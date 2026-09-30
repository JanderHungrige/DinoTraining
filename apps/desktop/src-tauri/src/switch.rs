//! CPU ⇄ GPU from the Admin tab (doc 128): the first start's `uv sync` with another
//! extra, around a stopped backend, and a way back when it fails.

use serde::Serialize;
use tauri::Manager;

use crate::runtime::Runtime;
use crate::setup::{self, Choice, Machine, SetupFailure};
use crate::setup_flow::{runtime, sync, SetupState};
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

const VARIANTS: [&str; 3] = ["cpu", "cu126", "cu130"];

/// Where to go back to when a switch fails: what was installed before, or the CPU when
/// that is unknown. Nothing when the failed switch *was* to that variant.
pub fn rollback_to(previous: Option<&str>, attempted: &str) -> Option<&'static str> {
    let target = previous.unwrap_or("cpu");
    VARIANTS.into_iter().find(|variant| *variant == target && *variant != attempted)
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
    let previous = runtime.installed().map(|installed| installed.variant);
    state.begin()?;
    let result = switch(&app, runtime, &choice, previous.as_deref()).await;
    state.end();
    result
}

async fn switch(
    app: &tauri::AppHandle,
    runtime: Runtime,
    choice: &Choice,
    previous: Option<&str>,
) -> Result<(), SetupFailure> {
    // Checked while the backend still runs: a refusal here costs the user nothing.
    setup::check_disk(&runtime.root, choice)?;
    tauri::async_runtime::spawn_blocking(setup::check_online)
        .await
        .map_err(|error| SetupFailure::Failed { message: error.to_string() })??;

    log::info!("Switching PyTorch from {previous:?} to {}", choice.variant);
    app.state::<SidecarHandle>().shutdown();
    let Err(failure) = sync_and_start(app, runtime.clone(), choice.variant).await else {
        log::info!("Switched to {}", choice.variant);
        return Ok(());
    };
    let Some(back) = rollback_to(previous, choice.variant) else {
        return Err(failure);
    };

    log::warn!("Switching to {} failed ({failure:?}); going back to {back}", choice.variant);
    app.state::<SidecarHandle>().shutdown();
    match sync_and_start(app, runtime, back).await {
        Ok(()) => Err(SetupFailure::RolledBack { to: back.to_string(), reason: Box::new(failure) }),
        Err(second) => {
            log::error!("Going back to {back} failed too: {second:?}");
            Err(failure)
        }
    }
}

async fn sync_and_start(
    app: &tauri::AppHandle,
    runtime: Runtime,
    variant: &'static str,
) -> Result<(), SetupFailure> {
    sync(app, runtime, variant).await?;
    crate::start_backend(app.clone())
        .await
        .map_err(|message| SetupFailure::Failed { message })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_failed_switch_goes_back_to_what_was_installed() {
        assert_eq!(rollback_to(Some("cpu"), "cu130"), Some("cpu"));
        assert_eq!(rollback_to(Some("cu126"), "cpu"), Some("cu126"));
    }

    #[test]
    fn unknown_before_means_back_to_the_cpu() {
        assert_eq!(rollback_to(None, "cu130"), Some("cpu"));
    }

    #[test]
    fn nothing_to_go_back_to_when_the_switch_was_to_the_same() {
        assert_eq!(rollback_to(Some("cpu"), "cpu"), None);
        assert_eq!(rollback_to(None, "cpu"), None);
    }

    #[test]
    fn an_unknown_previous_variant_is_not_invented() {
        assert_eq!(rollback_to(Some("rocm"), "cpu"), None);
    }

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
