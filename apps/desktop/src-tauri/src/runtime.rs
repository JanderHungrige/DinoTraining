//! The bundled runtime (doc 126): `uv`, the backend source and its lock ship in the app;
//! Python and every package are installed into the user's data folder from the official
//! sources, exactly as `uv.lock` pins them.
//!
//! This module holds no Tauri types, like `sidecar`: paths come in, processes go out.

use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use serde::{Deserialize, Serialize};

/// The resource folder `scripts/stage_runtime.py` writes and `tauri.release.conf.json`
/// bundles. The two are a pair and must agree.
pub const RESOURCE_DIR: &str = "runtime";
/// The Python the lock was made for (doc 125: `requires-python = ">=3.12,<3.13"`).
pub const PYTHON: &str = "3.12";

#[derive(Debug, thiserror::Error)]
pub enum RuntimeError {
    #[error("could not run uv: {0}")]
    Spawn(#[from] std::io::Error),
    #[error("installing the packages failed ({status}): {last_line}")]
    Failed { status: String, last_line: String },
}

/// What was installed, so an update or a variant switch can tell what it has.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Installed {
    pub variant: String,
    /// Seconds since the Unix epoch.
    pub installed_at: u64,
}

#[derive(Debug, Clone)]
pub struct Runtime {
    /// `<resources>/runtime`, read-only.
    pub bundled: PathBuf,
    /// `<app data>/runtime`, writable.
    pub root: PathBuf,
}

/// No console window on Windows for a helper process. `uv`, `nvidia-smi` and the venv's
/// `python.exe` are console programs; started from a GUI app each would flash (or, for
/// the backend, keep open) a black window.
pub fn hide_console(command: &mut Command) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }
    #[cfg(not(windows))]
    let _ = command;
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

    pub fn env_dir(&self) -> PathBuf {
        self.root.join("env")
    }

    pub fn env_python(&self) -> PathBuf {
        if cfg!(windows) {
            self.env_dir().join("Scripts").join("python.exe")
        } else {
            self.env_dir().join("bin").join("python")
        }
    }

    fn installed_lock(&self) -> PathBuf {
        self.root.join("installed.lock")
    }

    fn installed_file(&self) -> PathBuf {
        self.root.join("installed.json")
    }

    /// Installed, and from the lock this app version carries. An update with a new lock
    /// is not ready until it is synced (doc 129).
    pub fn is_ready(&self) -> bool {
        let bundled = std::fs::read(self.backend_dir().join("uv.lock")).ok();
        let installed = std::fs::read(self.installed_lock()).ok();
        self.env_python().is_file() && bundled.is_some() && bundled == installed
    }

    pub fn installed(&self) -> Option<Installed> {
        let text = std::fs::read_to_string(self.installed_file()).ok()?;
        serde_json::from_str(&text).ok()
    }

    /// A `uv` command that sees nothing of the user's own Python or uv setup.
    pub fn uv_command(&self) -> Command {
        let mut command = Command::new(self.uv());
        command
            .current_dir(self.backend_dir())
            .env("UV_PYTHON_INSTALL_DIR", self.root.join("python"))
            .env("UV_CACHE_DIR", self.root.join("cache"))
            .env("UV_PROJECT_ENVIRONMENT", self.env_dir())
            .env("UV_PYTHON_PREFERENCE", "only-managed")
            .env("UV_NO_CONFIG", "1")
            .env_remove("VIRTUAL_ENV")
            .env_remove("PYTHONPATH");
        hide_console(&mut command);
        command
    }

    /// Install (or re-sync) the environment for `variant` (`cpu`, `cu126`, `cu130`),
    /// streaming uv's output line by line. Records what was installed on success only, so
    /// an interrupted sync is never taken for a finished one.
    pub fn sync(&self, variant: &str, mut on_line: impl FnMut(&str)) -> Result<(), RuntimeError> {
        std::fs::create_dir_all(&self.root)?;
        let mut child = self
            .uv_command()
            .args(["sync", "--frozen", "--extra", variant, "--python", PYTHON])
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn()?;
        let mut last_line = String::new();
        if let Some(stderr) = child.stderr.take() {
            for line in BufReader::new(stderr).lines().map_while(Result::ok) {
                on_line(&line);
                if !line.trim().is_empty() {
                    last_line = line;
                }
            }
        }
        let status = child.wait()?;
        if !status.success() {
            return Err(RuntimeError::Failed { status: status.to_string(), last_line });
        }
        std::fs::copy(self.backend_dir().join("uv.lock"), self.installed_lock())?;
        let installed = Installed {
            variant: variant.to_string(),
            installed_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|elapsed| elapsed.as_secs())
                .unwrap_or_default(),
        };
        std::fs::write(
            self.installed_file(),
            serde_json::to_string_pretty(&installed).unwrap_or_default(),
        )?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("dino-runtime-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn bundle(dir: &Path, lock: &str) -> Runtime {
        let backend = dir.join("resources").join(RESOURCE_DIR).join("backend");
        std::fs::create_dir_all(backend.join("app")).unwrap();
        std::fs::write(backend.join("app").join("main.py"), "").unwrap();
        std::fs::write(backend.join("uv.lock"), lock).unwrap();
        Runtime { bundled: backend.parent().unwrap().to_path_buf(), root: dir.join("data") }
    }

    #[test]
    fn a_checkout_has_no_bundled_runtime() {
        let dir = temp("checkout");
        assert!(Runtime::find(Some(&dir)).is_none());
        assert!(Runtime::find(None).is_none());
    }

    #[test]
    fn ready_only_with_a_python_and_the_same_lock() {
        let dir = temp("ready");
        let runtime = bundle(&dir, "lock v1");
        assert!(!runtime.is_ready(), "nothing installed yet");
        std::fs::create_dir_all(runtime.env_python().parent().unwrap()).unwrap();
        std::fs::write(runtime.env_python(), "").unwrap();
        assert!(!runtime.is_ready(), "installed from no known lock");
        std::fs::write(runtime.root.join("installed.lock"), "lock v1").unwrap();
        assert!(runtime.is_ready());
        // An app update brings a new lock: not ready until it is synced (doc 129).
        std::fs::write(runtime.backend_dir().join("uv.lock"), "lock v2").unwrap();
        assert!(!runtime.is_ready());
    }

    #[test]
    fn uv_sees_nothing_of_the_users_own_python() {
        let dir = temp("isolation");
        let runtime = bundle(&dir, "lock");
        let command = runtime.uv_command();
        let envs: Vec<(String, Option<String>)> = command
            .get_envs()
            .map(|(k, v)| (k.to_string_lossy().into(), v.map(|v| v.to_string_lossy().into())))
            .collect();
        let get = |key: &str| envs.iter().find(|(k, _)| k == key).and_then(|(_, v)| v.clone());
        assert_eq!(get("UV_PYTHON_PREFERENCE").as_deref(), Some("only-managed"));
        assert_eq!(get("UV_NO_CONFIG").as_deref(), Some("1"));
        assert!(get("UV_PROJECT_ENVIRONMENT").unwrap().ends_with("env"));
        assert!(envs.iter().any(|(k, v)| k == "VIRTUAL_ENV" && v.is_none()), "removed");
    }
}
