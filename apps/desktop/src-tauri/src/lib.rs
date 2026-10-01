//! DinoTraining desktop shell.
//!
//! Responsibilities stop at the window and the sidecar process. No ML, no business
//! logic — that all lives behind `/api/v1` in the Python backend.

pub mod mac_apps;
pub mod progress;
pub mod resources;
pub mod runtime;
pub mod setup;
pub mod setup_flow;
pub mod sidecar;
pub mod switch;
pub mod uv_sync;

use tauri::{Emitter, Manager, RunEvent};

use crate::setup_flow::SetupState;
use crate::sidecar::{BackendState, SidecarConfig, SidecarHandle};

/// Emitted to the webview whenever the backend's state changes.
const BACKEND_EVENT: &str = "backend-state";

/// Lets the UI ask for the backend origin instead of hardcoding a port.
#[tauri::command]
fn backend_url(app: tauri::AppHandle) -> String {
    SidecarConfig::resolve(resource_dir(&app).as_deref())
        .map(|config| format!("http://{}:{}", config.host, config.port))
        .unwrap_or_else(|_| "http://127.0.0.1:8756".to_string())
}

pub fn run() {
    tauri::Builder::default()
        // Without a logger installed the `log::` macros below are silent no-ops —
        // which would make a failed sidecar startup invisible outside the UI event.
        // Its default targets are stdout and the app's log folder; the second is what a
        // user can send when the install or the backend fails outside a terminal.
        .plugin(
            tauri_plugin_log::Builder::new()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(SidecarHandle::default())
        .manage(SetupState::default())
        .invoke_handler(tauri::generate_handler![
            backend_url,
            setup_flow::setup_status,
            setup_flow::setup_install,
            setup_flow::setup_report,
            setup_flow::start_previous,
            switch::runtime_status,
            switch::switch_variant,
            mac_apps::applications_offer,
            mac_apps::add_to_applications
        ])
        .setup(|app| {
            let handle = app.handle().clone();
            install_signal_handlers(handle.clone());
            tauri::async_runtime::spawn(async move {
                // Its failure is already logged and emitted to the UI.
                let _ = start_backend(handle).await;
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build the DinoTraining window")
        .run(|app_handle, event| {
            // Covers both the last-window-closed path and an explicit quit.
            if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
                app_handle.state::<SidecarHandle>().shutdown();
            }
        });
}

/// Kill the sidecar on SIGTERM/SIGINT as well as on a normal quit.
///
/// Tauri's `RunEvent` handler covers closing the window, but not a signal — and a
/// `tauri dev` restart or a terminal Ctrl-C sends one. Without this the Python process
/// is orphaned holding port 8756, and the next launch fails on bind. Nothing can be
/// done about SIGKILL; `ensure_port_free` reports that case with instructions instead.
#[cfg(unix)]
fn install_signal_handlers(app: tauri::AppHandle) {
    tauri::async_runtime::spawn(async move {
        use tokio::signal::unix::{signal, SignalKind};

        let (Ok(mut term), Ok(mut interrupt)) = (
            signal(SignalKind::terminate()),
            signal(SignalKind::interrupt()),
        ) else {
            log::warn!("Could not install signal handlers; the backend may outlive the window");
            return;
        };

        tokio::select! {
            _ = term.recv() => {}
            _ = interrupt.recv() => {}
        }

        log::info!("Signal received — stopping the backend before exit");
        app.state::<SidecarHandle>().shutdown();
        std::process::exit(0);
    });
}

#[cfg(not(unix))]
fn install_signal_handlers(_app: tauri::AppHandle) {
    // Windows Ctrl-C handling arrives with the Wave 5 packaging work.
}

/// Where the bundled resources are, or None in a development run (see `resources`).
fn resource_dir(app: &tauri::AppHandle) -> Option<std::path::PathBuf> {
    resources::resource_dir(app)
}

/// Spawn the sidecar and report the outcome to the UI; returns the failure too, for the
/// setup screen, which waits on this rather than polling from the webview (doc 127).
///
/// A packaged app without its environment waits: the setup screen installs it and calls
/// this again.
pub(crate) async fn start_backend(app: tauri::AppHandle) -> Result<(), String> {
    if setup_flow::needs_setup(&app) {
        log::info!("The Python environment is not installed yet; waiting for the setup screen");
        return Ok(());
    }
    let _ = app.emit(BACKEND_EVENT, BackendState::Starting);

    let config = match SidecarConfig::resolve(resource_dir(&app).as_deref()) {
        Ok(config) => config,
        Err(error) => return Err(report_failure(&app, error.to_string())),
    };

    if let Err(error) = sidecar::wait_port_free(&config).await {
        return Err(report_failure(&app, error.to_string()));
    }

    let mut child = match sidecar::spawn(&config) {
        Ok(child) => child,
        Err(error) => return Err(report_failure(&app, error.to_string())),
    };

    let result = sidecar::wait_until_healthy(&config, &mut child).await;

    // Hand the child over either way: on failure it may still be alive and must
    // not be leaked past shutdown.
    app.state::<SidecarHandle>().store(child);

    match result {
        Ok(()) => {
            let url = format!("http://{}:{}", config.host, config.port);
            let _ = app.emit(BACKEND_EVENT, BackendState::Ready { url });
            Ok(())
        }
        Err(error) => Err(report_failure(&app, error.to_string())),
    }
}

/// Log and emit a startup failure; returns the message for callers that pass it on.
fn report_failure(app: &tauri::AppHandle, message: String) -> String {
    log::error!("Backend failed to start: {message}");
    let _ = app.emit(BACKEND_EVENT, BackendState::Failed { message: message.clone() });
    message
}
