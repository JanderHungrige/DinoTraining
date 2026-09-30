//! The setup screen's two commands (doc 127): what this machine needs, and install it.
//!
//! The screen *asks* (`setup_status`) rather than waiting for an event, because an event
//! emitted before the webview listens is simply lost, and a window stuck on "Starting"
//! would be exactly the doc 126 behaviour this replaces.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use serde::Serialize;
use tauri::{Emitter, Manager};

use crate::progress::{looks_offline, Tracker};
use crate::runtime::Runtime;
use crate::setup::{self, Machine, SetupFailure};

/// Emitted while `uv sync` runs: [`crate::progress::Progress`].
pub const PROGRESS_EVENT: &str = "setup-progress";

#[derive(Default)]
pub struct SetupState {
    machine: Mutex<Option<Machine>>,
    installing: AtomicBool,
}

impl SetupState {
    /// One install or switch at a time: two `uv sync` into one environment would corrupt it.
    pub(crate) fn begin(&self) -> Result<(), SetupFailure> {
        if self.installing.swap(true, Ordering::SeqCst) {
            return Err(SetupFailure::Failed { message: "An install is already running.".into() });
        }
        Ok(())
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
}

pub fn runtime(app: &tauri::AppHandle) -> Option<Runtime> {
    Runtime::find(app.path().resource_dir().ok().as_deref())
}

pub fn needs_setup(app: &tauri::AppHandle) -> bool {
    runtime(app).is_some_and(|runtime| !runtime.is_ready())
}

#[tauri::command]
pub fn setup_status(app: tauri::AppHandle, state: tauri::State<'_, SetupState>) -> SetupStatus {
    if !needs_setup(&app) {
        return SetupStatus { needed: false, machine: None, auto: None };
    }
    let machine = state.machine();
    let auto = std::env::var("DINO_SETUP_AUTO")
        .ok()
        .filter(|wanted| machine.choices.iter().any(|choice| choice.variant == wanted));
    SetupStatus { needed: true, machine: Some(machine), auto }
}

/// The setup screen's steps, into the app log: what a user sends when the first start
/// goes wrong, and what doc 131's smoke test reads. Only known step names are logged.
#[tauri::command]
pub fn setup_report(step: String) {
    const STEPS: [&str; 6] = ["shown", "installing", "starting", "ready", "opened", "failed"];
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
    let result = install(&app, runtime, choice.variant, &choice).await;
    state.end();
    result?;
    crate::start_backend(app.clone())
        .await
        .map_err(|message| SetupFailure::Failed { message })?;
    log::info!("Setup finished: the environment is installed and the backend answers");
    Ok(())
}

/// Disk, connection, then `uv sync` with progress events (doc 127).
pub(crate) async fn install(
    app: &tauri::AppHandle,
    runtime: Runtime,
    variant: &'static str,
    choice: &setup::Choice,
) -> Result<(), SetupFailure> {
    setup::check_disk(&runtime.root, choice)?;
    tauri::async_runtime::spawn_blocking(setup::check_online)
        .await
        .map_err(|error| SetupFailure::Failed { message: error.to_string() })??;
    sync(app, runtime, variant).await
}

/// `uv sync` alone, with progress events. The rollback of doc 128 uses it without the
/// checks: the previous variant comes from uv's cache and needs no connection.
pub(crate) async fn sync(
    app: &tauri::AppHandle,
    runtime: Runtime,
    variant: &'static str,
) -> Result<(), SetupFailure> {
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
        (Ok(()), _) => Ok(()),
        (Err(_), true) => Err(SetupFailure::Offline),
        (Err(error), false) => {
            log::error!("Install failed: {error}");
            Err(SetupFailure::Failed { message: error.to_string() })
        }
    }
}
