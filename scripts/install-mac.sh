#!/usr/bin/env bash
# Install V-Rex on a Mac with Apple silicon (doc 130).
#
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/JanderHungrige/DinoTraining/main/scripts/install-mac.sh)"
#
# Why a script: the app is not signed with a paid Apple certificate. Gatekeeper only
# blocks files a *browser* downloaded (they carry a quarantine mark); curl sets none. So
# this installs without a warning and without admin rights, into ~/Applications.
#
# Environment:
#   DINO_VERSION      a release version (default: the latest release)
#   DINO_ARCHIVE      install this local .app.tar.gz instead (checked against <file>.sha256)
#   DINO_INSTALL_DIR  where the app goes (default: ~/Applications)

set -euo pipefail

REPO="JanderHungrige/DinoTraining"
INSTALL_DIR="${DINO_INSTALL_DIR:-$HOME/Applications}"
APP_NAME="V-Rex.app"

say() { printf '%s\n' "$*"; }
fail() { printf 'V-Rex install: %s\n' "$*" >&2; exit 1; }

# --- the machine ---------------------------------------------------------------------
[ "$(uname -s)" = "Darwin" ] || fail "this script is for macOS. Windows and Linux have installers on the releases page."
# hw.optional.arm64 is 1 on Apple silicon, even for a shell running under Rosetta.
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" != "1" ]; then
  fail "this Mac has an Intel processor. PyTorch, which V-Rex needs, is no longer made for Intel Macs."
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/v-rex-install.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# --- the archive ---------------------------------------------------------------------
if [ -n "${DINO_ARCHIVE:-}" ]; then
  ARCHIVE="$DINO_ARCHIVE"
  [ -f "$ARCHIVE" ] || fail "no archive at $ARCHIVE"
  [ -f "$ARCHIVE.sha256" ] || fail "no checksum at $ARCHIVE.sha256"
  EXPECTED="$(awk '{print $1}' "$ARCHIVE.sha256")"
else
  if [ -n "${DINO_VERSION:-}" ]; then
    VERSION="${DINO_VERSION#v}"
  else
    say "Looking up the latest release…"
    VERSION="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
      | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | head -n 1)"
    [ -n "$VERSION" ] || fail "could not find the latest release. Set DINO_VERSION, or see https://github.com/$REPO/releases"
  fi
  NAME="V-Rex_${VERSION}_aarch64.app.tar.gz"
  BASE="https://github.com/$REPO/releases/download/v$VERSION/$NAME"
  say "Downloading V-Rex $VERSION…"
  ARCHIVE="$WORK/$NAME"
  curl -fL --progress-bar -o "$ARCHIVE" "$BASE" || fail "download failed: $BASE"
  EXPECTED="$(curl -fsSL "$BASE.sha256" | awk '{print $1}')" || fail "could not fetch the checksum"
fi

ACTUAL="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
if [ "$ACTUAL" != "$EXPECTED" ]; then
  fail "the archive's checksum does not match ($ACTUAL, expected $EXPECTED). Nothing was installed."
fi

# --- unpack, then replace ------------------------------------------------------------
tar -xzf "$ARCHIVE" -C "$WORK"
[ -d "$WORK/$APP_NAME" ] || fail "the archive holds no $APP_NAME"

mkdir -p "$INSTALL_DIR"
# The old app is replaced only now that the new one is complete.
if [ -e "$INSTALL_DIR/$APP_NAME" ] || [ -L "$INSTALL_DIR/$APP_NAME" ]; then
  rm -rf "$INSTALL_DIR/$APP_NAME"
fi
mv "$WORK/$APP_NAME" "$INSTALL_DIR/$APP_NAME"

say "Installed: $INSTALL_DIR/$APP_NAME"
say "Start it from Finder or Spotlight, or with: open \"$INSTALL_DIR/$APP_NAME\""
say "The first start downloads Python and PyTorch once (about 1 GB)."
