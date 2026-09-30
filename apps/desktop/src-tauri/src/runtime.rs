//! The bundled runtime (doc 126): `uv`, the backend source and its lock ship in the app;
//! Python and every package are installed into the user's data folder from the official
//! sources, exactly as `uv.lock` pins them.
//!
//! Environments live side by side (doc 129): every sync builds a new folder under
//! `envs/`, and `current` names the one the backend runs in. The running environment is
//! never touched, so an update or a switch that fails leaves a working app behind.
//!
//! Running uv lives in [`crate::uv_sync`]. This module holds no Tauri types, like `sidecar`: paths come in, processes go out.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

/// The resource folder `scripts/stage_runtime.py` writes and `tauri.release.conf.json`
/// bundles. The two are a pair and must agree.
pub const RESOURCE_DIR: &str = "runtime";

/// What was installed, so an update or a variant switch can tell what it has.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Installed {
    pub variant: String,
    /// Seconds since the Unix epoch.
    pub installed_at: u64,
}

/// One environment folder under `envs/`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Env {
    pub id: String,
    pub dir: PathBuf,
}

impl Env {
    pub fn python(&self) -> PathBuf {
        if cfg!(windows) {
            self.dir.join("Scripts").join("python.exe")
        } else {
            self.dir.join("bin").join("python")
        }
    }

    pub(crate) fn lock_copy(&self) -> PathBuf {
        self.dir.join("installed.lock")
    }

    pub fn installed(&self) -> Option<Installed> {
        let text = std::fs::read_to_string(self.dir.join("installed.json")).ok()?;
        serde_json::from_str(&text).ok()
    }

    /// Has a Python: it can start, even if its lock is older than the app's (doc 129).
    pub fn usable(&self) -> bool {
        self.python().is_file()
    }
}

#[derive(Debug, Clone)]
pub struct Runtime {
    /// `<resources>/runtime`, read-only.
    pub bundled: PathBuf,
    /// `<app data>/runtime`, writable.
    pub root: PathBuf,
}

/// Where the app keeps its own files when nothing overrides it. Mirrors the Python side's
/// data folder choice (`data/` lives beside `runtime/`).
pub fn app_support_root() -> Option<PathBuf> {
    let home = std::env::var_os("HOME").or_else(|| std::env::var_os("USERPROFILE"))?;
    let home = PathBuf::from(home);
    Some(if cfg!(target_os = "macos") {
        home.join("Library").join("Application Support").join("DinoTraining")
    } else if cfg!(windows) {
        std::env::var_os("APPDATA").map(PathBuf::from).unwrap_or(home).join("DinoTraining")
    } else {
        home.join(".local").join("share").join("DinoTraining")
    })
}

pub(crate) fn since_epoch() -> std::time::Duration {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default()
}

impl Runtime {
    /// The bundled runtime, when this is a packaged build. A checkout has none.
    pub fn find(resource_dir: Option<&Path>) -> Option<Self> {
        let bundled = resource_dir?.join(RESOURCE_DIR);
        if !bundled.join("backend").join("app").join("main.py").is_file() {
            return None;
        }
        let root = std::env::var_os("DINO_RUNTIME_DIR")
            .map(PathBuf::from)
            .or_else(|| app_support_root().map(|root| root.join("runtime")))?;
        Some(Self { bundled, root })
    }

    pub fn backend_dir(&self) -> PathBuf {
        self.bundled.join("backend")
    }

    pub fn uv(&self) -> PathBuf {
        self.bundled.join(if cfg!(windows) { "uv.exe" } else { "uv" })
    }

    pub(crate) fn envs_dir(&self) -> PathBuf {
        self.root.join("envs")
    }

    fn pointer(&self) -> PathBuf {
        self.root.join("current")
    }

    pub(crate) fn env(&self, id: &str) -> Env {
        Env { id: id.to_string(), dir: self.envs_dir().join(id) }
    }

    /// The environment the backend runs in, when there is one.
    pub fn current(&self) -> Option<Env> {
        let id = std::fs::read_to_string(self.pointer()).ok()?;
        let env = self.env(id.trim());
        env.dir.is_dir().then_some(env)
    }

    /// Installed, and from the lock this app version carries. An update with a new lock
    /// is not ready until it is synced (doc 129).
    pub fn is_ready(&self) -> bool {
        let Some(env) = self.current() else { return false };
        let bundled = std::fs::read(self.backend_dir().join("uv.lock")).ok();
        let installed = std::fs::read(env.lock_copy()).ok();
        env.usable() && bundled.is_some() && bundled == installed
    }

    pub fn installed(&self) -> Option<Installed> {
        self.current()?.installed()
    }

    /// Make `env` the one the backend runs in: one rename, so never half-written.
    pub fn activate(&self, env: &Env) -> std::io::Result<()> {
        std::fs::create_dir_all(&self.root)?;
        let temporary = self.root.join("current.tmp");
        std::fs::write(&temporary, &env.id)?;
        std::fs::rename(&temporary, self.pointer())
    }

    /// Remove every environment but the current one: the one replaced, and leftovers of
    /// an interrupted sync. Best effort: a folder still in use stays for next time.
    pub fn remove_others(&self) {
        let Some(current) = self.current() else { return };
        let Ok(entries) = std::fs::read_dir(self.envs_dir()) else { return };
        for entry in entries.flatten() {
            if entry.file_name().to_string_lossy() == current.id {
                continue;
            }
            match std::fs::remove_dir_all(entry.path()) {
                Ok(()) => log::info!("Removed the old environment {}", entry.path().display()),
                Err(error) => log::warn!("Could not remove {}: {error}", entry.path().display()),
            }
        }
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;

    pub(crate) fn temp(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("dino-runtime-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    pub(crate) fn bundle(dir: &Path, lock: &str) -> Runtime {
        let backend = dir.join("resources").join(RESOURCE_DIR).join("backend");
        std::fs::create_dir_all(backend.join("app")).unwrap();
        std::fs::write(backend.join("app").join("main.py"), "").unwrap();
        std::fs::write(backend.join("uv.lock"), lock).unwrap();
        Runtime { bundled: backend.parent().unwrap().to_path_buf(), root: dir.join("data") }
    }

    /// What a successful sync leaves: a Python and the lock it was synced from.
    fn fake_env(runtime: &Runtime, id: &str, lock: &str) -> Env {
        let env = runtime.env(id);
        std::fs::create_dir_all(env.python().parent().unwrap()).unwrap();
        std::fs::write(env.python(), "").unwrap();
        std::fs::write(env.lock_copy(), lock).unwrap();
        env
    }

    #[test]
    fn a_checkout_has_no_bundled_runtime() {
        let dir = temp("checkout");
        assert!(Runtime::find(Some(&dir)).is_none());
        assert!(Runtime::find(None).is_none());
    }

    #[test]
    fn ready_only_with_a_current_env_from_the_same_lock() {
        let dir = temp("ready");
        let runtime = bundle(&dir, "lock v1");
        assert!(!runtime.is_ready(), "nothing installed yet");
        let env = fake_env(&runtime, "1", "lock v1");
        assert!(!runtime.is_ready(), "built but not activated");
        runtime.activate(&env).unwrap();
        assert!(runtime.is_ready());
        // An app update brings a new lock: not ready until it is synced (doc 129)...
        std::fs::write(runtime.backend_dir().join("uv.lock"), "lock v2").unwrap();
        assert!(!runtime.is_ready());
        // ...but the old environment can still start.
        assert!(runtime.current().unwrap().usable());
    }

    #[test]
    fn activating_switches_and_removing_others_keeps_only_the_current() {
        let dir = temp("switch");
        let runtime = bundle(&dir, "lock");
        let old = fake_env(&runtime, "1", "lock");
        runtime.activate(&old).unwrap();
        let new = fake_env(&runtime, "2", "lock");
        let leftover = runtime.env("3"); // an interrupted sync: no Python, no lock
        std::fs::create_dir_all(&leftover.dir).unwrap();

        assert_eq!(runtime.current(), Some(old.clone()), "a new build does not switch by itself");
        runtime.activate(&new).unwrap();
        assert_eq!(runtime.current(), Some(new.clone()));
        runtime.remove_others();
        assert!(new.dir.is_dir());
        assert!(!old.dir.exists() && !leftover.dir.exists());
    }

    #[test]
    fn a_pointer_to_a_missing_folder_is_no_environment() {
        let dir = temp("dangling");
        let runtime = bundle(&dir, "lock");
        runtime.activate(&runtime.env("gone")).unwrap();
        assert!(runtime.current().is_none());
        assert!(!runtime.is_ready());
    }

    #[test]
    fn a_new_env_never_reuses_an_existing_folder() {
        let dir = temp("fresh");
        let runtime = bundle(&dir, "lock");
        let first = runtime.new_env();
        std::fs::create_dir_all(&first.dir).unwrap();
        assert_ne!(runtime.new_env().dir, first.dir);
    }
}
