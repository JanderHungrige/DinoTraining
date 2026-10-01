//! Lifecycle for the FastAPI + PyTorch sidecar.
//!
//! The sidecar is `python -m app` in both cases: in development from the repo's backend
//! venv, in a packaged build from the uv-managed environment of the bundled runtime
//! (doc 126, [`crate::runtime`]). [`Launch`] is the only thing that differs.

use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use serde::Serialize;

use crate::runtime::{Env, Runtime};

/// How long to wait for the backend to answer before giving up.
/// Importing torch on a cold filesystem cache genuinely takes many seconds.
const READY_TIMEOUT: Duration = Duration::from_secs(60);
const POLL_INTERVAL: Duration = Duration::from_millis(250);

const DEFAULT_HOST: &str = "127.0.0.1";
const DEFAULT_PORT: u16 = 8756;

#[derive(Debug, thiserror::Error)]
pub enum SidecarError {
    #[error("the app's bundled runtime is missing: reinstall DinoTraining")]
    RuntimeMissing,
    #[error("could not locate the backend at {0}")]
    BackendMissing(PathBuf),
    #[error("could not find a Python interpreter — expected a venv at {0}")]
    PythonMissing(PathBuf),
    #[error("failed to spawn the backend process: {0}")]
    Spawn(#[from] std::io::Error),
    #[error("backend did not become healthy within {after:?}.{output}")]
    Timeout { after: Duration, output: String },
    /// `output` quotes `backend.log`'s last lines (doc 139), or says where to look.
    #[error("backend exited during startup ({status}).{output}")]
    BackendExited { status: std::process::ExitStatus, output: String },
    #[error(
        "port {0} is already in use. Another DinoTraining backend is probably still \
         running — stop it (lsof -ti:{0} | xargs kill) and relaunch."
    )]
    PortInUse(u16),
}

/// How the sidecar is started.
///
/// One way since doc 126: `python -m app`. What differs between a checkout and a packaged
/// app is only *which* Python and *which* backend folder — the repository's venv, or the
/// uv-managed environment in the user's data folder running the bundled backend source.
#[derive(Debug, Clone)]
pub enum Launch {
    Module { python: PathBuf, backend_dir: PathBuf },
}

/// Where the sidecar lives and how to reach it.
#[derive(Debug, Clone)]
pub struct SidecarConfig {
    pub launch: Launch,
    pub host: String,
    pub port: u16,
    /// Doc 139: where `backend.log` goes. `None` (a development run) inherits this
    /// process's terminal instead.
    pub log_dir: Option<PathBuf>,
}

impl SidecarConfig {
    pub fn health_url(&self) -> String {
        format!("http://{}:{}/api/v1/health", self.host, self.port)
    }

    /// Resolve how to start the sidecar.
    ///
    /// **The bundled runtime wins when it exists.** A packaged app must never fall through
    /// to a developer's venv that happens to be on the same machine — it would run a
    /// different build of the backend than the one shipped, and behave correctly enough
    /// that nobody would notice until the versions diverged.
    ///
    /// Whether the bundled runtime is *installed* is the caller's question
    /// ([`Runtime::is_ready`]); this only says where it will be.
    pub fn resolve(resource_dir: Option<&Path>) -> Result<Self, SidecarError> {
        match Runtime::find(resource_dir) {
            Some(runtime) => runtime
                .current()
                .map(|env| Self::bundled(&runtime, &env))
                .ok_or(SidecarError::PythonMissing(runtime.root)),
            // A release build never runs a developer's venv: on the build machine it would
            // run another backend than the one shipped, and work well enough that nobody
            // noticed (found live, doc 130: a start through a symlink did exactly that).
            None if cfg!(debug_assertions) => Self::for_development(),
            None => Err(SidecarError::RuntimeMissing),
        }
    }

    /// The packaged app: the uv-managed environment running the bundled backend source.
    pub fn bundled(runtime: &Runtime, env: &Env) -> Self {
        Self {
            launch: Launch::Module {
                python: env.python(),
                backend_dir: runtime.backend_dir(),
            },
            host: env_or(DEFAULT_HOST, "DINO_API_HOST"),
            port: env_port(),
            log_dir: None,
        }
    }

    /// Resolve paths for a development run, relative to this crate's source location.
    pub fn for_development() -> Result<Self, SidecarError> {
        let repo_root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(3)
            .ok_or_else(|| SidecarError::BackendMissing(PathBuf::from(env!("CARGO_MANIFEST_DIR"))))?
            .to_path_buf();

        let backend_dir = repo_root.join("backend");
        if !backend_dir.join("app").join("main.py").is_file() {
            return Err(SidecarError::BackendMissing(backend_dir));
        }

        let python = resolve_python(&backend_dir)?;

        Ok(Self {
            launch: Launch::Module { python, backend_dir },
            host: env_or(DEFAULT_HOST, "DINO_API_HOST"),
            port: env_port(),
            log_dir: None,
        })
    }
}

fn env_port() -> u16 {
    std::env::var("DINO_API_PORT")
        .ok()
        .and_then(|value| value.parse().ok())
        .unwrap_or(DEFAULT_PORT)
}

fn env_or(fallback: &str, key: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| fallback.to_string())
}

/// Prefer the project venv — a system Python almost certainly lacks torch.
fn resolve_python(backend_dir: &Path) -> Result<PathBuf, SidecarError> {
    let venv = backend_dir.join(".venv");
    let candidates = if cfg!(windows) {
        vec![venv.join("Scripts").join("python.exe")]
    } else {
        vec![venv.join("bin").join("python3"), venv.join("bin").join("python")]
    };

    candidates
        .into_iter()
        .find(|candidate| candidate.is_file())
        .ok_or(SidecarError::PythonMissing(venv))
}

/// Fail fast if something already owns the port.
///
/// Without this the new sidecar dies on bind, the old one keeps answering
/// `/api/v1/health`, and the shell cheerfully reports "ready" while pointed at a
/// process it does not own and cannot shut down.
pub fn ensure_port_free(config: &SidecarConfig) -> Result<(), SidecarError> {
    match std::net::TcpListener::bind((config.host.as_str(), config.port)) {
        Ok(listener) => {
            drop(listener);
            Ok(())
        }
        Err(_) => Err(SidecarError::PortInUse(config.port)),
    }
}

/// Wait up to [`PORT_WAIT`] for the port to free.
///
/// A backend stopped a moment ago (doc 128's switch) can leave the port unbindable for a
/// few seconds on Linux and Windows. A backend that is really still running fails after
/// the wait with the same message as before.
pub async fn wait_port_free(config: &SidecarConfig) -> Result<(), SidecarError> {
    let deadline = std::time::Instant::now() + PORT_WAIT;
    loop {
        match ensure_port_free(config) {
            Ok(()) => return Ok(()),
            Err(error) if std::time::Instant::now() >= deadline => return Err(error),
            Err(_) => tokio::time::sleep(POLL_INTERVAL).await,
        }
    }
}

const PORT_WAIT: Duration = Duration::from_secs(5);

/// Start the backend process. Does not wait for it to become healthy.
pub fn spawn(config: &SidecarConfig) -> Result<Child, SidecarError> {
    let Launch::Module { python, backend_dir } = &config.launch;
    log::info!("Spawning backend: {} -m app", python.display());
    let mut command = Command::new(python);
    command.arg("-m").arg("app").current_dir(backend_dir);
    crate::uv_sync::hide_console(&mut command);
    // An operation MPS lacks runs on the CPU instead of failing (doc 126). A value the
    // user set themselves is left alone.
    if cfg!(target_os = "macos") && std::env::var_os("PYTORCH_ENABLE_MPS_FALLBACK").is_none() {
        command.env("PYTORCH_ENABLE_MPS_FALLBACK", "1");
    }

    // Never inherit in a packaged app: a Windows GUI app has no standard streams to give,
    // and the backend's traceback went nowhere (doc 139).
    let (stdout, stderr) = match &config.log_dir {
        Some(dir) => {
            let (file, path) = crate::backend_log::create(dir)?;
            log::info!("Backend output: {}", path.display());
            (Stdio::from(file.try_clone()?), Stdio::from(file))
        }
        None => (Stdio::inherit(), Stdio::inherit()),
    };
    let child = command
        .env("DINO_API_HOST", &config.host)
        .env("DINO_API_PORT", config.port.to_string())
        // Unbuffered, so the Python log reaches the file as it happens rather than
        // in one lump when the process dies — which is exactly when you need it.
        .env("PYTHONUNBUFFERED", "1")
        .env("PYTHONIOENCODING", "utf-8")
        .stdout(stdout)
        .stderr(stderr)
        .spawn()?;

    Ok(child)
}

/// Poll `/api/v1/health` until it answers, the child dies, or the timeout elapses.
///
/// Takes the child so a crashed backend is reported as a crash. Polling the port
/// alone cannot distinguish "not listening yet" from "died on startup" — and the
/// difference is the entire diagnostic.
pub async fn wait_until_healthy(
    config: &SidecarConfig,
    child: &mut Child,
) -> Result<(), SidecarError> {
    let client = reqwest::Client::new();
    let url = config.health_url();
    let deadline = std::time::Instant::now() + READY_TIMEOUT;

    while std::time::Instant::now() < deadline {
        if let Some(status) = child.try_wait()? {
            let output = crate::backend_log::quote(config.log_dir.as_deref());
            return Err(SidecarError::BackendExited { status, output });
        }

        match client.get(&url).timeout(Duration::from_secs(2)).send().await {
            Ok(response) if response.status().is_success() => {
                log::info!("Backend healthy at {url}");
                return Ok(());
            }
            // A connection refused here is the normal "not listening yet" case.
            Ok(_) | Err(_) => tokio::time::sleep(POLL_INTERVAL).await,
        }
    }

    Err(SidecarError::Timeout {
        after: READY_TIMEOUT,
        output: crate::backend_log::quote(config.log_dir.as_deref()),
    })
}

/// Owns the child process so it can be killed when the window closes.
#[derive(Default)]
pub struct SidecarHandle {
    child: Mutex<Option<Child>>,
}

impl SidecarHandle {
    pub fn store(&self, child: Child) {
        if let Ok(mut slot) = self.child.lock() {
            *slot = Some(child);
        }
    }

    /// Kill the backend. Safe to call more than once.
    ///
    /// Without this the Python process outlives the window and keeps port 8756 —
    /// the next launch then fails with a confusing "address in use".
    pub fn shutdown(&self) {
        let Ok(mut slot) = self.child.lock() else {
            return;
        };
        if let Some(mut child) = slot.take() {
            log::info!("Stopping backend (pid {})", child.id());
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

/// Reported to the UI so a failed startup is visible in the window, not just the log.
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "state", rename_all = "snake_case")]
pub enum BackendState {
    Starting,
    Ready { url: String },
    Failed { message: String },
}
