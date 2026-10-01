//! Running `uv` for the bundled runtime (docs 126, 129): an isolated command, and the
//! sync that builds a new environment beside the current one.

use std::io::{BufRead, BufReader};
use std::process::{Command, Stdio};

use crate::runtime::{since_epoch, Env, Installed, Runtime};

/// The Python the lock was made for (doc 125: `requires-python = ">=3.12,<3.13"`).
pub const PYTHON: &str = "3.12";
/// Extras every installed app gets besides its PyTorch variant: `export` is doc 122's ONNX
/// export. Without it the export silently lacked `model.onnx` (found by doc 131's smoke
/// test, the first time an installed environment was checked).
pub const APP_EXTRAS: [&str; 1] = ["export"];

#[derive(Debug, thiserror::Error)]
pub enum RuntimeError {
    #[error("could not run uv: {0}")]
    Spawn(#[from] std::io::Error),
    #[error("installing the packages failed ({status}): {last_line}")]
    Failed { status: String, last_line: String },
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

impl Runtime {
    /// A `uv` command for `env` that sees nothing of the user's own Python or uv setup.
    pub fn uv_command(&self, env: &Env) -> Command {
        let mut command = Command::new(self.uv());
        command
            .current_dir(self.backend_dir())
            .env("UV_PYTHON_INSTALL_DIR", self.root.join("python"))
            .env("UV_CACHE_DIR", self.root.join("cache"))
            .env("UV_PROJECT_ENVIRONMENT", &env.dir)
            .env("UV_PYTHON_PREFERENCE", "only-managed")
            .env("UV_NO_CONFIG", "1")
            .env_remove("VIRTUAL_ENV")
            .env_remove("PYTHONPATH");
        hide_console(&mut command);
        command
    }

    /// A fresh folder for the next sync: never the current one, never an existing one.
    pub(crate) fn new_env(&self) -> Env {
        let mut id = since_epoch().as_millis().to_string();
        while self.envs_dir().join(&id).exists() {
            id.push('x');
        }
        self.env(&id)
    }

    /// Build a new environment for `variant` (`cpu`, `cu126`, `cu130`) beside the current
    /// one, streaming uv's output line by line. The lock copy and `installed.json` are
    /// written on success only, so an interrupted sync is never taken for a finished one.
    /// Does not switch to it: that is [`Runtime::activate`].
    pub fn sync(&self, variant: &str, mut on_line: impl FnMut(&str)) -> Result<Env, RuntimeError> {
        let env = self.new_env();
        std::fs::create_dir_all(self.envs_dir())?;
        let mut child = self
            .uv_command(&env)
            .args(sync_args(variant))
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
        std::fs::copy(self.backend_dir().join("uv.lock"), env.lock_copy())?;
        let installed = Installed {
            variant: variant.to_string(),
            extras: APP_EXTRAS.map(String::from).to_vec(),
            installed_at: since_epoch().as_secs(),
        };
        std::fs::write(
            env.dir.join("installed.json"),
            serde_json::to_string_pretty(&installed).unwrap_or_default(),
        )?;
        Ok(env)
    }

}

/// `uv sync --frozen --extra <variant> --extra export --python 3.12`.
pub fn sync_args(variant: &str) -> Vec<String> {
    let mut args = vec!["sync".to_string(), "--frozen".into(), "--extra".into(), variant.into()];
    for extra in APP_EXTRAS {
        args.extend(["--extra".to_string(), extra.to_string()]);
    }
    args.extend(["--python".to_string(), PYTHON.to_string()]);
    args
}

#[cfg(test)]
mod tests {
    use super::sync_args;

    #[test]
    fn the_app_installs_its_variant_and_the_onnx_export() {
        assert_eq!(
            sync_args("cu130").join(" "),
            "sync --frozen --extra cu130 --extra export --python 3.12"
        );
    }

    use crate::runtime::tests::{bundle, temp};

    #[test]
    fn uv_sees_nothing_of_the_users_own_python() {
        let dir = temp("isolation");
        let runtime = bundle(&dir, "lock");
        let command = runtime.uv_command(&runtime.env("7"));
        let envs: Vec<(String, Option<String>)> = command
            .get_envs()
            .map(|(k, v)| (k.to_string_lossy().into(), v.map(|v| v.to_string_lossy().into())))
            .collect();
        let get = |key: &str| envs.iter().find(|(k, _)| k == key).and_then(|(_, v)| v.clone());
        assert_eq!(get("UV_PYTHON_PREFERENCE").as_deref(), Some("only-managed"));
        assert_eq!(get("UV_NO_CONFIG").as_deref(), Some("1"));
        assert!(get("UV_PROJECT_ENVIRONMENT").unwrap().ends_with('7'));
        assert!(envs.iter().any(|(k, v)| k == "VIRTUAL_ENV" && v.is_none()), "removed");
    }
}
