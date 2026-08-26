#!/usr/bin/env bash
#
# Start DinoTraining for development.
#
#   ./scripts/dev.sh              full desktop app (Tauri window + Vite + backend)
#   ./scripts/dev.sh web          browser-only (Vite + backend, no Rust build)
#   ./scripts/dev.sh backend      backend alone
#
# The `web` mode is the fast loop: no Rust compile, and the same React app runs in a
# normal browser at http://localhost:1420. Reach for `desktop` when you are changing
# the shell itself or testing sidecar startup.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/apps/frontend"
DESKTOP_DIR="$REPO_ROOT/apps/desktop"
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"

log()  { printf '\033[0;36m[dev]\033[0m %s\n' "$*"; }
fail() { printf '\033[0;31m[dev]\033[0m %s\n' "$*" >&2; exit 1; }

preflight() {
  [ -x "$VENV_PYTHON" ] || fail "No backend venv. Run: python3.12 -m venv backend/.venv && source backend/.venv/bin/activate && pip install -e 'backend[dev]'"
  [ -d "$FRONTEND_DIR/node_modules" ] || fail "Frontend deps missing. Run: npm install --prefix apps/frontend --legacy-peer-deps"
  [ -f "$REPO_ROOT/.env" ] || log "WARNING: no .env at the repo root — copy .env.example and fill it in."
}

# Checked only for the desktop path, because `web` and `backend` never touch Tauri.
#
# It is separate from `preflight` because it was *missing* from it, and the failure was
# ugly: the script printed "Launching Tauri", handed `npx` a package that was not
# installed, and npx answered "could not determine executable to run" — which names
# neither Tauri nor the directory. `apps/desktop` keeps its own package.json holding only
# `@tauri-apps/cli`, and the README's setup never mentioned it.
desktop_preflight() {
  [ -d "$DESKTOP_DIR/node_modules" ] || fail "Tauri CLI missing. Run: npm install --prefix apps/desktop"
  command -v cargo >/dev/null || fail "cargo not found — install Rust 1.85+ (brew install rust)."
  command -v rustc >/dev/null || fail "rustc not found — install Rust 1.85+ (brew install rust)."

  # `rustc` existing is not the same as `rustc` working, and Tauri does not survive the
  # difference. tauri-cli 2.11.4 reads the host triple like this:
  #
  #   Command::new("rustc").args(["-vV"]).output()
  #     .expect("\"rustc\" could not be found, did you install Rust?")
  #   ...find(|l| l.starts_with("host:")).unwrap()          <- interface/rust.rs:1166
  #
  # A rustup shim with no default toolchain passes the `.expect` — the binary exists and
  # runs — then writes its error to *stderr* and leaves stdout empty, so the `find` returns
  # None and the CLI aborts with `called `Option::unwrap()` on a `None` value` and a line
  # number in someone else's crate. Nothing in that names rustup, a toolchain, or the fix.
  #
  # Captured into a variable rather than tested as `rustc -vV | grep -q`: `grep -q` exits
  # on the first match and closes the pipe, `rustc` dies of SIGPIPE with status 141, and
  # `set -o pipefail` above then fails the pipeline *because the match succeeded*. Caught
  # by running this check against a working toolchain, which is the case a preflight is
  # least likely to be tried against and the only one that must never fail.
  local rustc_out rustc_err
  rustc_out="$(rustc -vV 2>/dev/null | grep "^host:" || true)"
  if [ -z "$rustc_out" ]; then
    # **Show what rustc actually said.** The first version of this check guessed the cause
    # ("no default toolchain") and was wrong the first time it fired: the real one was a
    # Homebrew rust linked against a libLLVM that Homebrew had since upgraded, so rustc
    # aborted in the dynamic loader. Both causes look identical from the outside — empty
    # stdout — and only stderr tells them apart. So print stderr rather than a theory.
    rustc_err="$(rustc -vV 2>&1 >/dev/null || true)"
    fail "\`rustc -vV\` printed no host triple, so Tauri cannot start — it panics on an
       unwrap in its own CLI instead of saying so. What rustc reported:

  ${rustc_err:-(no output at all)}

       A 'Symbol not found' / dyld abort means the Rust install is linked against a
       library that moved — usually Homebrew rust after an llvm upgrade:
           brew reinstall rust        # or: brew uninstall rust && rustup default stable
       A 'no default toolchain' message means rustup has none selected:
           rustup default stable
       Having both Homebrew rust and rustup installed is the usual way into this; keep one.
       Check what is actually running with:  command -v rustc && rustc -vV"
  fi
}

start_backend() {
  log "Backend → http://127.0.0.1:8756/api/v1"
  cd "$BACKEND_DIR"
  PYTHONUNBUFFERED=1 "$VENV_PYTHON" -m app
}

start_web() {
  preflight
  # Kill the backend when this script exits, however it exits — an orphaned sidecar
  # holds port 8756 and makes the next run fail with a confusing "address in use".
  start_backend &
  local backend_pid=$!
  trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM

  log "Frontend → http://localhost:1420"
  cd "$FRONTEND_DIR"
  npm run dev
}

start_desktop() {
  preflight
  desktop_preflight
  log "Launching Tauri (it spawns the backend itself; first build takes a few minutes)"
  cd "$DESKTOP_DIR"
  npx tauri dev
}

case "${1:-desktop}" in
  desktop) start_desktop ;;
  web)     start_web ;;
  backend) preflight && start_backend ;;
  *)       fail "Unknown mode '${1}'. Use: desktop | web | backend" ;;
esac
