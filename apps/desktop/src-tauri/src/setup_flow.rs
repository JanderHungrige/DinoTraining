//! The setup screen's two commands (doc 127): what this machine needs, and install it.
//!
//! The screen *asks* (`setup_status`) rather than waiting for an event, because an event
//! emitted before the webview listens is simply lost, and a window stuck on "Starting"
//! would be exactly the doc 126 behaviour this replaces.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use serde::Serialize;
use tauri::{Emitter, Manager};

use crate::progress::{looks_offline, Phase, Progress, Tracker};
use crate::runtime::{Env, Runtime};
use crate::setup::{self, Machine, SetupFailure};

/// Emitted while `uv sync` runs: [`crate::progress::Progress`].
pub const PROGRESS_EVENT: &str = "setup-progress";

#[derive(Default)]
pub struct SetupState {
    machine: Mutex<Option<Machine>>,
    installing: AtomicBool,
    /// Doc 129: the user chose to start on the previous packages after a failed update.
    stale_ok: AtomicBool,
}

impl SetupState {
    /// One install or switch at a time: two `uv sync` into one environment would corrupt it.
    pub(crate) fn begin(&self) -> Result<(), SetupFailure> {
        if self.installing.swap(true, Ordering::SeqCst) {
            return Err(SetupFailure::Failed { message: "An install is already running.".into() });
        }
        Ok(())
    }

    pub(crate) fn allow_stale(&self) {
        self.stale_ok.store(true, Ordering::SeqCst);
    }

    pub(crate) fn end(&self) {
        self.installing.store(false, Ordering::SeqCst);
    }

    /// Detected once: `nvidia-smi` takes a moment and the answer does not change.
    pub(crate) fn machine(&self) -> Machine {
        let mut slot = self.machine.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
        slot.get_or_insert_with(setup::detect).clone()
    }
}

#[derive(Debug, Serialize)]
pub struct SetupStatus {
    /// A packaged app whose environment is missing or from an older lock.
    pub needed: bool,
    pub machine: Option<Machine>,
    /// `DINO_SETUP_AUTO=<variant>`: the screen installs it without waiting for a click.
    /// For unattended installs and doc 131's smoke test; a variant this machine cannot
    /// take is ignored, so the screen asks as usual.
    pub auto: Option<String>,
    /// Doc 129: an environment exists but is from an older lock. Its variant; the screen
    /// updates it without asking, and can fall back to it.
    pub update: Option<String>,
}

pub fn runtime(app: &tauri::AppHandle) -> Option<Runtime> {
    Runtime::find(crate::resources::resource_dir(app).as_deref())
}

/// A packaged app whose environment is missing or outdated, unless the user chose to
/// start on the outdated one (doc 129).
pub fn needs_setup(app: &tauri::AppHandle) -> bool {
    let Some(runtime) = runtime(app) else { return false };
    if runtime.is_ready() {
        // Doc 141: a ready environment whose PyTorch cannot load on this Windows.
        return crate::vc_runtime::needed();
    }
    let stale_ok = app.state::<SetupState>().stale_ok.load(Ordering::SeqCst);
    !(stale_ok && runtime.current().is_some_and(|env| env.usable()))
}

/// The variant of an existing environment from an older lock (doc 129).
fn outdated_variant(runtime: &Runtime) -> Option<String> {
    let env = runtime.current().filter(Env::usable)?;
    Some(env.installed().map_or_else(|| "cpu".to_string(), |installed| installed.variant))
}

#[tauri::command]
pub fn setup_status(app: tauri::AppHandle, state: tauri::State<'_, SetupState>) -> SetupStatus {
    if !needs_setup(&app) {
        return SetupStatus { needed: false, machine: None, auto: None, update: None };
    }
    let machine = state.machine();
    let update = runtime(&app).and_then(|runtime| outdated_variant(&runtime));
    let offered = |wanted: &String| machine.choices.iter().any(|choice| choice.variant == wanted);
    let auto = setup_auto(
        std::env::var("DINO_SETUP_AUTO").ok(),
        crate::support_dir::app_support_root().map(|root| root.join(SETUP_AUTO_FILE)),
    )
    .or_else(|| update.clone())
    .filter(offered);
    SetupStatus { needed: true, machine: Some(machine), auto, update }
}

/// Doc 153: the unattended variant, also from a file in the support folder. A Store (MSIX)
/// app started like the Start menu does inherits no environment, so its smoke test writes
/// the variant there instead of setting `DINO_SETUP_AUTO`.
pub const SETUP_AUTO_FILE: &str = "setup-auto";

pub(crate) fn setup_auto(env: Option<String>, file: Option<std::path::PathBuf>) -> Option<String> {
    env.filter(|value| !value.trim().is_empty())
        .or_else(|| file.and_then(|path| std::fs::read_to_string(path).ok()))
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

/// The setup screen's steps, into the app log: what a user sends when the first start
/// goes wrong, and what doc 131's smoke test reads. Only known step names are logged.
#[tauri::command]
pub fn setup_report(step: String) {
    const STEPS: [&str; 7] =
        ["shown", "installing", "starting", "resuming", "ready", "opened", "failed"];
    if STEPS.contains(&step.as_str()) {
        log::info!("Setup screen: {step}");
    }
}

/// Check, install, start the backend, and return once it answers `/health`.
///
/// The shell waits, not the screen: a webview in a hidden window has its timers paused
/// by WebKit, so a screen polling `/health` stalled on "starting" while the backend was
/// long up (found live, doc 127).
#[tauri::command]
pub async fn setup_install(
    app: tauri::AppHandle,
    state: tauri::State<'_, SetupState>,
    variant: String,
) -> Result<(), SetupFailure> {
    let runtime = runtime(&app).ok_or(SetupFailure::Unsupported)?;
    let machine = state.machine();
    let choice = machine
        .choices
        .iter()
        .find(|choice| choice.variant == variant)
        .cloned()
        .ok_or(SetupFailure::Unsupported)?;
    state.begin()?;
    let result = install(&app, runtime.clone(), choice.variant, &choice).await;
    state.end();
    let previous = runtime.current();
    activate(&runtime, &result?)?;
    if let Err(message) = crate::start_backend(app.clone()).await {
        // A new environment that does not start: point back at the old one, which the
        // screen offers to start (doc 129). Nothing is removed.
        if let Some(previous) = previous {
            activate(&runtime, &previous)?;
        }
        return Err(SetupFailure::Failed { message });
    }
    log::info!("Setup finished: the environment is installed and the backend answers");
    tauri::async_runtime::spawn_blocking(move || runtime.remove_others());
    Ok(())
}

pub(crate) fn activate(runtime: &Runtime, env: &Env) -> Result<(), SetupFailure> {
    runtime.activate(env).map_err(|error| SetupFailure::Failed { message: error.to_string() })
}

/// Doc 129: start on the previous packages after a failed update. The update is tried
/// again at the next start.
#[tauri::command]
pub async fn start_previous(
    app: tauri::AppHandle,
    state: tauri::State<'_, SetupState>,
) -> Result<(), SetupFailure> {
    log::warn!("Starting on the previous environment; the update is still pending");
    state.allow_stale();
    crate::start_backend(app.clone()).await.map_err(|message| SetupFailure::Failed { message })
}

/// Disk, connection, then `uv sync` into a new environment, with progress events (doc 127).
pub(crate) async fn install(
    app: &tauri::AppHandle,
    runtime: Runtime,
    variant: &'static str,
    choice: &setup::Choice,
) -> Result<Env, SetupFailure> {
    ensure_vc_runtime(app).await?;
    setup::check_disk(&runtime.root, choice)?;
    tauri::async_runtime::spawn_blocking(setup::check_online)
        .await
        .map_err(|error| SetupFailure::Failed { message: error.to_string() })??;
    sync(app, runtime, variant).await
}

/// Doc 141: Microsoft's Visual C++ runtime first, on Windows when it is too old for
/// PyTorch. The screen says so before Windows asks for permission.
async fn ensure_vc_runtime(app: &tauri::AppHandle) -> Result<(), SetupFailure> {
    if !crate::vc_runtime::needed() {
        return Ok(());
    }
    let progress = Progress { phase: Phase::Runtime, done_mb: 0.0, total_mb: 0.0, current: None };
    let _ = app.emit(PROGRESS_EVENT, progress);
    tauri::async_runtime::spawn_blocking(crate::vc_runtime::ensure)
        .await
        .map_err(|error| SetupFailure::Failed { message: error.to_string() })?
}

/// `uv sync` into a new environment beside the current one, with progress events.
async fn sync(
    app: &tauri::AppHandle,
    runtime: Runtime,
    variant: &'static str,
) -> Result<Env, SetupFailure> {
    log::info!("Installing the {variant} environment into {}", runtime.root.display());
    let emitter = app.clone();
    let outcome = tauri::async_runtime::spawn_blocking(move || {
        let mut tracker = Tracker::default();
        let mut offline = false;
        let result = runtime.sync(variant, |line| {
            log::info!("uv: {line}");
            offline |= looks_offline(line);
            if let Some(progress) = tracker.read(line) {
                let _ = emitter.emit(PROGRESS_EVENT, progress);
            }
        });
        (result, offline)
    })
    .await
    .map_err(|error| SetupFailure::Failed { message: error.to_string() })?;

    match outcome {
        (Ok(env), _) => Ok(env),
        (Err(_), true) => Err(SetupFailure::Offline),
        (Err(error), false) => {
            log::error!("Install failed: {error}");
            Err(SetupFailure::Failed { message: error.to_string() })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_unattended_variant_comes_from_the_environment_or_the_file() {
        let dir = std::env::temp_dir().join(format!("dino-setup-auto-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let file = dir.join(SETUP_AUTO_FILE);
        std::fs::write(&file, "cpu\n").unwrap();
        assert_eq!(setup_auto(Some("cu130".into()), Some(file.clone())), Some("cu130".into()));
        assert_eq!(setup_auto(None, Some(file.clone())), Some("cpu".into()));
        assert_eq!(setup_auto(Some("  ".into()), Some(file.clone())), Some("cpu".into()));
        assert_eq!(setup_auto(None, Some(dir.join("missing"))), None);
        assert_eq!(setup_auto(None, None), None);
        std::fs::remove_dir_all(&dir).unwrap();
    }
}
