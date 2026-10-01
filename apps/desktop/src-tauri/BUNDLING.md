# Building an installer

The runtime is **not** in `tauri.conf.json`, and that is deliberate: a `bundle.resources`
entry makes Tauri's build script fail when the path is absent, so putting it in the main
config would break `cargo check` and `npm run tauri dev` for anyone who has not staged it.
Development does not need it — `SidecarConfig::resolve()` falls back to `python -m app`
from the backend venv.

Release builds merge it in (doc 126):

```bash
# 1. Stage the runtime: uv for the target (checksum-verified) and the backend source with
#    its lock, into src-tauri/runtime/.
python scripts/stage_runtime.py aarch64-apple-darwin   # or x86_64-pc-windows-msvc, x86_64-unknown-linux-gnu

# 2. Build the installer.
cd apps/desktop
npm run tauri build -- --config src-tauri/tauri.release.conf.json
```

Python and PyTorch are not in the installer. On first start the app runs
`uv sync --frozen` into the user's data folder (`…/DinoTraining/runtime/`), fetching
CPython and every package from the official sources exactly as `backend/uv.lock` pins
them. `DINO_RUNTIME_DIR` moves that folder, e.g. for a test install.
