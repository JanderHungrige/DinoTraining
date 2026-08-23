//! Lifecycle for the FastAPI + PyTorch sidecar.
//!
//! In development the sidecar is `python -m app` run from the repo's backend venv.
//! In a packaged build it is a **frozen binary** shipped beside the executable, and
//! [`Launch`] is the only thing that differs — everything above this module stays put,
//! which is what the original note promised (doc 56).

use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use serde::Serialize;

/// How long to wait for the backend to answer before giving up.
/// Importing torch on a cold filesystem cache genuinely takes many seconds.
const READY_TIMEOUT: Duration = Duration::from_secs(60);
const POLL_INTERVAL: Duration = Duration::from_millis(250);

const DEFAULT_HOST: &str = "127.0.0.1";
const DEFAULT_PORT: u16 = 8756;

#[derive(Debug, thiserror::Error)]
pub enum SidecarError {
    #[error("could not locate the backend at {0}")]
    BackendMissing(PathBuf),
    #[error("could not find a Python interpreter — expected a venv at {0}")]
    PythonMissing(PathBuf),
    #[error("failed to spawn the backend process: {0}")]
    Spawn(#[from] std::io::Error),
    #[error("backend did not become healthy within {0:?}")]
    Timeout(Duration),
    #[error("backend exited during startup ({0}) — see the log above for the Python traceback")]
    BackendExited(std::process::ExitStatus),
    #[error(
        "port {0} is already in use. Another DinoTraining backend is probably still \
         running — stop it (lsof -ti:{0} | xargs kill) and relaunch."
    )]
    PortInUse(u16),
}

/// How the sidecar is started.
///
/// Two variants and no third: either PyInstaller froze it into one binary, or this is a
/// checkout with a venv. A packaged build has no venv and a checkout has no frozen binary,
/// so the choice is made by looking rather than by a flag someone has to remember to set.
#[derive(Debug, Clone)]
pub enum Launch {
    /// A frozen binary next to the app executable, as Tauri's `externalBin` places it.
    Frozen(PathBuf),
    /// `python -m app` from the repository's backend venv.
    Module { python: PathBuf, backend_dir: PathBuf },
}

/// Where the sidecar lives and how to reach it.
#[derive(Debug, Clone)]
pub struct SidecarConfig {
    pub launch: Launch,
    pub host: String,
    pub port: u16,
}

impl SidecarConfig {
    pub fn health_url(&self) -> String {
        format!("http://{}:{}/api/v1/health", self.host, self.port)
    }

    /// Resolve how to start the sidecar.
    ///
    /// **The frozen binary wins when it exists.** A packaged app must never fall through to
    /// a developer's venv that happens to be on the same machine — it would run a different
    /// build of the backend than the one shipped, and behave correctly enough that nobody
    /// would notice until the versions diverged.
    pub fn resolve() -> Result<Self, SidecarError> {
        if let Some(frozen) = frozen_sidecar() {
            log::info!("Using the bundled sidecar: {}", frozen.display());
            return Ok(Self {
                launch: Launch::Frozen(frozen),
                host: env_or(DEFAULT_HOST, "DINO_API_HOST"),
                port: env_port(),
            });
        }
        Self::for_development()
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
        })
    }
}

fn env_port() -> u16 {
    std::env::var("DINO_API_PORT")
        .ok()
        .and_then(|value| value.parse().ok())
        .unwrap_or(DEFAULT_PORT)
}

/// The frozen sidecar beside this executable, if there is one.
///
/// Tauri strips the target triple from an `externalBin` name when it bundles, so the file
/// installed next to the app is plain `dinotraining-sidecar`. The build script names it
/// with the triple because that is what the *bundler* looks for — the two names are
/// deliberately different and confusing them is the usual first failure.
fn frozen_sidecar() -> Option<PathBuf> {
    let name = if cfg!(windows) { "dinotraining-sidecar.exe" } else { "dinotraining-sidecar" };
    let beside = std::env::current_exe().ok()?.parent()?.join(name);
    beside.is_file().then_some(beside)
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

/// Start the backend process. Does not wait for it to become healthy.
pub fn spawn(config: &SidecarConfig) -> Result<Child, SidecarError> {
    let mut command = match &config.launch {
        Launch::Frozen(binary) => {
            log::info!("Spawning bundled sidecar: {}", binary.display());
            Command::new(binary)
        }
        Launch::Module { python, backend_dir } => {
            log::info!("Spawning backend: {} -m app", python.display());
            let mut command = Command::new(python);
            command.arg("-m").arg("app").current_dir(backend_dir);
            command
        }
    };

    let child = command
        .env("DINO_API_HOST", &config.host)
        .env("DINO_API_PORT", config.port.to_string())
        // Unbuffered, so the Python log reaches our stderr as it happens rather than
        // in one lump when the process dies — which is exactly when you need it.
        .env("PYTHONUNBUFFERED", "1")
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
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
            return Err(SidecarError::BackendExited(status));
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

    Err(SidecarError::Timeout(READY_TIMEOUT))
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
