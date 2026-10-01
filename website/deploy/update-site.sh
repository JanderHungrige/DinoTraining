#!/usr/bin/env bash
# Keep the DinoTraining download site current (doc 133). Runs from jan's crontab:
#
#   */10 * * * * $HOME/dinotraining-site/deploy/update-site.sh >> $HOME/dinotraining-site/update.log 2>&1
#
# 1. The site: website/ (+ the app's background video) at the newest commit of the first
#    branch that has it (main; dev until main carries website/). Rendered into
#    sites/<sha>/, then `current` is switched in one rename. nginx serves current/.
# 2. latest.json: GitHub's latest published release, reduced to what the page needs.
# 3. Its own deploy files (this script, compose.yml, nginx.conf) from the same commit;
#    the container is (re)started only when compose.yml or nginx.conf changed.
#
# Touches nothing outside SITE_ROOT and its own container. Needs: bash, curl, tar,
# python3, git, docker (jan is in the docker group).

set -euo pipefail

REPO="JanderHungrige/DinoTraining"
SITE_ROOT="${SITE_ROOT:-$HOME/dinotraining-site}"
BRANCHES="${SITE_BRANCHES:-main dev}"
NO_DOCKER="${SITE_NO_DOCKER:-}"
KEEP_SITES=3

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

mkdir -p "$SITE_ROOT/sites" "$SITE_ROOT/deploy"
# One run at a time (cron every 10 min, a slow download could overlap).
if command -v flock >/dev/null; then
  exec 9>"$SITE_ROOT/.lock"
  flock -n 9 || { log "another run is busy"; exit 0; }
fi

# --- 1. which commit -------------------------------------------------------------------
SHA=""
for branch in $BRANCHES; do
  candidate="$(git ls-remote "https://github.com/$REPO" "refs/heads/$branch" | cut -f1)"
  [ -n "$candidate" ] || continue
  if curl -fsI "https://raw.githubusercontent.com/$REPO/$candidate/website/index.html" >/dev/null; then
    SHA="$candidate"
    BRANCH="$branch"
    break
  fi
  log "$branch ($candidate) has no website/ yet"
done
[ -n "$SHA" ] || { log "no branch carries website/; nothing to do"; exit 1; }

# --- 2. the site at that commit --------------------------------------------------------
if [ "$(cat "$SITE_ROOT/deployed-sha" 2>/dev/null)" != "$SHA" ]; then
  log "deploying $BRANCH at $SHA"
  WORK="$(mktemp -d "$SITE_ROOT/sites/.new.XXXXXX")"
  trap 'rm -rf "$WORK"' EXIT
  curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$SHA" | tar -xz -C "$WORK"
  SRC="$(find "$WORK" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  NEW="$SITE_ROOT/sites/$SHA"
  rm -rf "$NEW"
  mkdir -p "$NEW/media"
  cp "$SRC"/website/*.html "$SRC"/website/*.css "$SRC"/website/*.js "$NEW/"
  cp "$SRC"/apps/frontend/public/background/particles-loop.mp4 \
     "$SRC"/apps/frontend/public/background/particles-poster.jpg "$NEW/media/"

  # Deploy files: note whether the container's configuration changed.
  RESTART=""
  for file in compose.yml nginx.conf; do
    if ! cmp -s "$SRC/website/deploy/$file" "$SITE_ROOT/deploy/$file"; then RESTART=1; fi
    cp "$SRC/website/deploy/$file" "$SITE_ROOT/deploy/$file"
  done
  cp "$SRC/website/deploy/update-site.sh" "$SITE_ROOT/deploy/update-site.sh.new"
  chmod +x "$SITE_ROOT/deploy/update-site.sh.new"

  # One rename switches what nginx serves; a visitor never sees half a site.
  python3 - "$SITE_ROOT" "$SHA" <<'PY'
import os, sys
root, sha = sys.argv[1], sys.argv[2]
tmp = os.path.join(root, "current.tmp")
if os.path.lexists(tmp):
    os.remove(tmp)
os.symlink(os.path.join("sites", sha), tmp)
os.replace(tmp, os.path.join(root, "current"))
PY
  echo "$SHA" > "$SITE_ROOT/deployed-sha"
  # The script replaces itself last: this run keeps reading the old file safely.
  mv -f "$SITE_ROOT/deploy/update-site.sh.new" "$SITE_ROOT/deploy/update-site.sh"

  # Older sites beyond the newest few.
  ls -1t "$SITE_ROOT/sites" | grep -v '^\.' | tail -n +$((KEEP_SITES + 1)) | while read -r old; do
    [ "$old" = "$SHA" ] || rm -rf "${SITE_ROOT:?}/sites/$old"
  done

  if [ -n "$RESTART" ] && [ -z "$NO_DOCKER" ]; then
    log "container configuration changed: (re)starting"
    SITE_ROOT="$SITE_ROOT" docker compose -p dinotraining-site -f "$SITE_ROOT/deploy/compose.yml" up -d --force-recreate
  fi
fi

# --- 3. latest.json --------------------------------------------------------------------
RELEASE="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null || echo '{}')"
# The release arrives on stdin: its notes may hold any character, so it is never pasted
# into code.
read -r -d '' LATEST_PY <<'PY' || true
import json, os, sys
target = sys.argv[1]
try:
    release = json.load(sys.stdin)
except ValueError:
    release = {}
if not isinstance(release, dict):
    release = {}
def asset(suffix):
    for item in release.get("assets", []):
        if item.get("name", "").endswith(suffix):
            return {"name": item["name"], "url": item["browser_download_url"], "size": item["size"]}
    return None
tag = release.get("tag_name") or ""
data = {
    "version": tag[1:] if tag.startswith("v") else (tag or None),
    "published_at": release.get("published_at"),
    "html_url": release.get("html_url") or "https://github.com/JanderHungrige/DinoTraining/releases",
    "assets": {
        "windows": asset("-setup.exe"),
        "linux": asset("_amd64.deb"),
        "mac": asset("_aarch64.app.tar.gz"),
    },
}
text = json.dumps(data, indent=2) + "\n"
old = open(target).read() if os.path.exists(target) else ""
if text != old:
    with open(target + ".tmp", "w") as out:
        out.write(text)
    os.replace(target + ".tmp", target)
    print("latest.json:", data["version"])
PY
printf '%s' "$RELEASE" | python3 -c "$LATEST_PY" "$SITE_ROOT/latest.json"
