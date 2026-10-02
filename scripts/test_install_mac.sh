#!/usr/bin/env bash
# Tests for scripts/install-mac.sh (doc 130). macOS on Apple silicon only; no network:
# every case installs a local archive through DINO_ARCHIVE.
#
#   bash scripts/test_install_mac.sh

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
INSTALL="$HERE/install-mac.sh"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/v-rex-install-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
FAILED=0

check() { # check <description> <command...>
  local what="$1"; shift
  if "$@"; then printf 'ok    %s\n' "$what"; else printf 'FAIL  %s\n' "$what"; FAILED=1; fi
}

# An archive holding a V-Rex.app whose binary prints its build.
make_archive() { # make_archive <dir> <build>
  local dir="$1" build="$2"
  mkdir -p "$dir/src/V-Rex.app/Contents/MacOS"
  printf '#!/bin/sh\necho %s\n' "$build" > "$dir/src/V-Rex.app/Contents/MacOS/dinotraining"
  chmod +x "$dir/src/V-Rex.app/Contents/MacOS/dinotraining"
  tar -czf "$dir/app.tar.gz" -C "$dir/src" V-Rex.app
  shasum -a 256 "$dir/app.tar.gz" > "$dir/app.tar.gz.sha256"
}

run_install() { # run_install <archive> <target>
  DINO_ARCHIVE="$1" DINO_INSTALL_DIR="$2" bash "$INSTALL" > "$WORK/out.txt" 2>&1
}

make_archive "$WORK/v1" one
make_archive "$WORK/v2" two
TARGET="$WORK/Applications"

check "installs into a folder it creates" run_install "$WORK/v1/app.tar.gz" "$TARGET"
check "the installed app runs" test "$("$TARGET/V-Rex.app/Contents/MacOS/dinotraining")" = one
check "no quarantine mark on the installed app" \
  sh -c "! xattr '$TARGET/V-Rex.app' | grep -q com.apple.quarantine"

check "installing again replaces the app" run_install "$WORK/v2/app.tar.gz" "$TARGET"
check "the new build is the one installed" test "$("$TARGET/V-Rex.app/Contents/MacOS/dinotraining")" = two

# A tampered archive: the checksum no longer matches.
cp "$WORK/v1/app.tar.gz" "$WORK/bad.tar.gz"
cp "$WORK/v2/app.tar.gz.sha256" "$WORK/bad.tar.gz.sha256"
check "a checksum mismatch refuses" sh -c "! DINO_ARCHIVE='$WORK/bad.tar.gz' DINO_INSTALL_DIR='$TARGET' bash '$INSTALL' > '$WORK/out.txt' 2>&1"
check "…and says why" grep -q "checksum does not match" "$WORK/out.txt"
check "…and leaves the installed app alone" test "$("$TARGET/V-Rex.app/Contents/MacOS/dinotraining")" = two

# An archive without the app.
mkdir -p "$WORK/empty/src/Other"
tar -czf "$WORK/empty/app.tar.gz" -C "$WORK/empty/src" Other
shasum -a 256 "$WORK/empty/app.tar.gz" > "$WORK/empty/app.tar.gz.sha256"
check "an archive without the app refuses" sh -c "! DINO_ARCHIVE='$WORK/empty/app.tar.gz' DINO_INSTALL_DIR='$TARGET' bash '$INSTALL' > '$WORK/out.txt' 2>&1"
check "…and the installed app survives" test -x "$TARGET/V-Rex.app/Contents/MacOS/dinotraining"

exit "$FAILED"
