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
