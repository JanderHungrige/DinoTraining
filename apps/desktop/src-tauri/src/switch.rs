//! CPU ⇄ GPU from the Admin tab (doc 128): the first start's `uv sync` with another
//! extra into a new environment while the backend keeps running (doc 129), then a quick
//! swap, and a way back when the new one does not start.

use serde::Serialize;
use tauri::Manager;

use crate::runtime::{Env, Runtime};
use crate::setup::{Machine, SetupFailure};
use crate::setup_flow::{activate, install, runtime, SetupState};
use crate::sidecar::SidecarHandle;

/// For the GPU panel: what is installed, and what this machine could take.
#[derive(Debug, Serialize)]
pub struct RuntimeStatus {
    pub variant: Option<String>,
    pub machine: Machine,
}

/// `None` outside the packaged app: a checkout manages its own environment.
#[tauri::command]
pub fn runtime_status(
    app: tauri::AppHandle,
    state: tauri::State<'_, SetupState>,
) -> Option<RuntimeStatus> {
    let runtime = runtime(&app)?;
    Some(RuntimeStatus {
        variant: runtime.installed().map(|installed| installed.variant),
        machine: state.machine(),
    })
}

#[tauri::command]
pub async fn switch_variant(
    app: tauri::AppHandle,
    state: tauri::State<'_, SetupState>,
    variant: String,
) -> Result<(), SetupFailure> {
    let runtime = runtime(&app).ok_or(SetupFailure::Unsupported)?;
    let choice = state
        .machine()
        .choices
        .into_iter()
        .find(|choice| choice.variant == variant)
        .ok_or(SetupFailure::Unsupported)?;
    state.begin()?;
    // The download: the backend keeps running on the current environment meanwhile, and
    // a failure here has changed nothing.
    let built = install(&app, runtime.clone(), choice.variant, &choice).await;
    state.end();
    swap(&app, &runtime, &built?, choice.variant).await
}

/// Stop, point at `new`, start. When it does not start, point back and start the old
/// one: seconds, nothing downloaded.
async fn swap(
    app: &tauri::AppHandle,
    runtime: &Runtime,
    new: &Env,
    variant: &str,
) -> Result<(), SetupFailure> {
    let previous = runtime.current();
    log::info!("Switching PyTorch to {variant}");
    app.state::<SidecarHandle>().shutdown();
    activate(runtime, new)?;
    let Err(message) = crate::start_backend(app.clone()).await else {
        log::info!("Switched to {variant}");
        let runtime = runtime.clone();
        tauri::async_runtime::spawn_blocking(move || runtime.remove_others());
        return Ok(());
    };
    let reason = SetupFailure::Failed { message };
    let Some(previous) = previous else { return Err(reason) };
    log::warn!("The {variant} environment did not start ({reason:?}); going back");
    app.state::<SidecarHandle>().shutdown();
    activate(runtime, &previous)?;
    crate::start_backend(app.clone())
        .await
        .map_err(|message| SetupFailure::Failed { message })?;
    let to = previous.installed().map_or_else(|| "cpu".to_string(), |installed| installed.variant);
    Err(SetupFailure::RolledBack { to, reason: Box::new(reason) })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_rollback_reports_where_it_went_and_why() {
        let failure = SetupFailure::RolledBack {
            to: "cpu".into(),
            reason: Box::new(SetupFailure::Offline),
        };
        let json = serde_json::to_value(&failure).unwrap();
        assert_eq!(json["kind"], "rolled_back");
        assert_eq!(json["to"], "cpu");
        assert_eq!(json["reason"]["kind"], "offline");
    }
}
