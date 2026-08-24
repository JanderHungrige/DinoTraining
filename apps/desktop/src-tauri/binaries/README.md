# Bundled sidecar

Tauri's `externalBin` looks here for `dinotraining-sidecar-<target-triple>` — for example
`dinotraining-sidecar-aarch64-apple-darwin`. Build it with:

```bash
cd backend
python -m venv .build && .build/bin/pip install . pyinstaller
.build/bin/python packaging/build_sidecar.py
cp -R dist/dinotraining-sidecar-<triple> ../apps/desktop/src-tauri/binaries/
```

**Nothing here is committed.** The sidecar is ~640 MB per platform (doc 56), PyInstaller
does not cross-compile, and the torch wheel differs per platform — so it is built on each
platform by the release job rather than checked in.

The name here carries the target triple; the file *installed* beside the app does not —
Tauri strips it when bundling. `frozen_sidecar()` in `sidecar.rs` looks for the stripped
name, and confusing the two is the usual first failure.
