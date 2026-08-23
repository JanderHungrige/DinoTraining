# Building an installer

The sidecar is **not** in `tauri.conf.json`, and that is deliberate: `externalBin` makes
Tauri's build script fail when the binary is absent, so putting it in the main config would
break `cargo check` and `npm run tauri dev` for anyone who has not built a 640 MB sidecar
first. Development does not need one — `SidecarConfig::resolve()` falls back to
`python -m app` from the backend venv.

Release builds merge it in:

```bash
# 1. Freeze the sidecar from a *production* venv (not the dev one — see doc 56).
cd backend
python -m venv .build && .build/bin/pip install . pyinstaller
.build/bin/python packaging/build_sidecar.py

# 2. Put it where the bundler looks.
cp -R dist/dinotraining-sidecar-<triple> ../apps/desktop/src-tauri/binaries/

# 3. Build the installer.
cd ../apps/desktop
npm run tauri build -- --config src-tauri/tauri.release.conf.json
```

Per platform: PyInstaller does not cross-compile and the torch wheel differs by platform,
so step 1 runs on each of macOS, Windows and Linux.

## GPU builds

The shipped sidecar is **CPU-only** (doc 56 — a CUDA torch wheel is 2.5 GB on Windows). A
CUDA sidecar is built the same way, from a venv installed against PyTorch's CUDA index, and
published as a separate release asset. The app downloads it into
`<DINO_DATA_DIR>/runtimes/cuda/` and prefers it automatically — see doc 57 and
`downloaded_gpu_sidecar()` in `src/sidecar.rs`.
