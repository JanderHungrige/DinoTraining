//! Microsoft's Visual C++ runtime on Windows (doc 141).
//!
//! PyTorch's Windows wheels need `msvcp140.dll` 14.40 or newer and do not ship it: against
//! an older one, `c10.dll` fails to initialise (WinError 1114) and the backend dies on
//! `import torch`. The setup checks the version and installs Microsoft's redistributable
//! before PyTorch. Elsewhere, nothing here does anything.

use std::fmt;

use crate::setup::SetupFailure;

/// The oldest runtime PyTorch 2.13's DLLs initialise against.
pub const MINIMUM: (u32, u32) = (14, 40);
/// Microsoft's permanent link to the current x64 redistributable.
pub const DOWNLOAD_URL: &str = "https://aka.ms/vs/17/release/vc_redist.x64.exe";
#[cfg_attr(not(windows), allow(dead_code))]
const SCRIPT: &str = include_str!("vc_runtime.ps1");
#[cfg_attr(not(windows), allow(dead_code))]
const REG_KEY: &str = r"HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64";

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct Version(pub u32, pub u32, pub u32);

impl fmt::Display for Version {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}.{}.{}", self.0, self.1, self.2)
    }
}

/// The version from `reg query <key> /v Version`: a line `Version  REG_SZ  v14.28.29334.00`.
pub fn parse_reg(output: &str) -> Option<Version> {
    let line = output.lines().find(|line| line.contains("REG_SZ") && line.trim_start().starts_with("Version"))?;
    let value = line.split_whitespace().last()?.trim_start_matches(['v', 'V']);
    let mut parts = value.split('.').map(|part| part.parse::<u32>().ok());
    Some(Version(parts.next()??, parts.next()??, parts.next().flatten().unwrap_or(0)))
}

/// Missing or unreadable counts as too old: installing over a newer one is harmless.
pub fn too_old(version: Option<Version>) -> bool {
    version.map_or(true, |version| (version.0, version.1) < MINIMUM)
}

/// What the installer script's exit code means (see `vc_runtime.ps1`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Installed,
    Declined,
    Unsigned,
    DownloadFailed,
    Failed(i32),
}

pub fn outcome(code: i32) -> Outcome {
    match code {
        0 | 3010 | 1638 => Outcome::Installed,
        1223 | 1602 => Outcome::Declined,
        90 => Outcome::Unsigned,
        91 => Outcome::DownloadFailed,
        other => Outcome::Failed(other),
    }
}

fn failure(found: Option<Version>, reason: &str, code: Option<i32>) -> SetupFailure {
    SetupFailure::VcRuntime { found: found.map(|version| version.to_string()), reason: reason.into(), code }
}

/// The installed runtime's version, from the registry; `None` elsewhere or when absent.
pub fn installed() -> Option<Version> {
    #[cfg(windows)]
    {
        let mut command = std::process::Command::new("reg");
        command.args(["query", REG_KEY, "/v", "Version", "/reg:64"]);
        crate::uv_sync::hide_console(&mut command);
        let output = command.output().ok()?;
        parse_reg(&String::from_utf8_lossy(&output.stdout))
    }
    #[cfg(not(windows))]
    None
}

/// Windows only: is the runtime missing or too old for PyTorch?
pub fn needed() -> bool {
    cfg!(windows) && too_old(installed())
}

/// Install the runtime when it is needed; blocking (Windows' permission prompt waits).
pub fn ensure() -> Result<(), SetupFailure> {
    if !needed() {
        return Ok(());
    }
    let found = installed();
    log::info!(
        "The Visual C++ runtime is {}; installing Microsoft's redistributable",
        found.map_or_else(|| "missing".to_string(), |version| version.to_string())
    );
    let code = run_script()?;
    match outcome(code) {
        Outcome::Installed if too_old(installed()) => {
            log::error!("The runtime installer succeeded ({code}) but the version is still too old");
            Err(failure(installed(), "still_old", Some(code)))
        }
        Outcome::Installed => {
            log::info!("The Visual C++ runtime is now {:?}", installed());
            Ok(())
        }
        Outcome::Declined => Err(failure(found, "declined", None)),
        Outcome::Unsigned => Err(failure(found, "unsigned", None)),
        Outcome::DownloadFailed => Err(failure(found, "download", None)),
        Outcome::Failed(code) => Err(failure(found, "installer", Some(code))),
    }
}

#[cfg(windows)]
fn run_script() -> Result<i32, SetupFailure> {
    let script = std::env::temp_dir().join("dinotraining-vc-runtime.ps1");
    std::fs::write(&script, SCRIPT).map_err(could_not_run)?;
    let mut command = std::process::Command::new("powershell");
    command.args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"]).arg(&script);
    command.arg("-Url").arg(DOWNLOAD_URL);
    crate::uv_sync::hide_console(&mut command);
    let output = command.output().map_err(could_not_run)?;
    let _ = std::fs::remove_file(&script);
    let said = String::from_utf8_lossy(&output.stdout);
    log::info!("Runtime installer: {}", said.trim());
    Ok(output.status.code().unwrap_or(-1))
}

#[cfg(not(windows))]
fn run_script() -> Result<i32, SetupFailure> {
    Ok(0)
}

#[cfg(windows)]
fn could_not_run(error: std::io::Error) -> SetupFailure {
    log::error!("The runtime installer could not run: {error}");
    failure(installed(), "installer", None)
}

/// For a backend that died on `import torch`: the runtime is the likely cause when the
/// log shows `c10.dll` failing to load or initialise.
pub fn backend_hint(log_tail: &str) -> Option<String> {
    let torch_dll = log_tail.contains("c10.dll");
    let load_error = log_tail.contains("WinError 1114") || log_tail.contains("WinError 126");
    (torch_dll && load_error).then(|| {
        format!(
            "\n\nThis usually means Microsoft's Visual C++ runtime is missing or older than \
             {}.{}. Install it from {DOWNLOAD_URL} and start V-Rex again.",
            MINIMUM.0, MINIMUM.1
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const JAN: &str = "\r\nHKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64\r\n    Version    REG_SZ    v14.28.29334.00\r\n\r\n";

    #[test]
    fn reads_the_version_from_reg_query() {
        assert_eq!(parse_reg(JAN), Some(Version(14, 28, 29334)));
        assert_eq!(parse_reg("    Version    REG_SZ    v14.44.35211.00"), Some(Version(14, 44, 35211)));
        assert_eq!(parse_reg("ERROR: The system was unable to find the specified registry key or value."), None);
        assert_eq!(parse_reg(""), None);
    }

    #[test]
    fn jans_runtime_is_too_old_and_missing_counts_as_too_old() {
        assert!(too_old(parse_reg(JAN)));
        assert!(too_old(None));
        assert!(too_old(Some(Version(14, 39, 99999))));
        assert!(!too_old(Some(Version(14, 40, 33810))));
        assert!(!too_old(Some(Version(14, 44, 35211))));
        assert!(!too_old(Some(Version(15, 0, 0))));
    }

    #[test]
    fn the_installer_exit_codes() {
        for code in [0, 3010, 1638] {
            assert_eq!(outcome(code), Outcome::Installed);
        }
        assert_eq!(outcome(1223), Outcome::Declined);
        assert_eq!(outcome(1602), Outcome::Declined);
        assert_eq!(outcome(90), Outcome::Unsigned);
        assert_eq!(outcome(91), Outcome::DownloadFailed);
        assert_eq!(outcome(1603), Outcome::Failed(1603));
    }

    #[test]
    fn the_backend_hint_only_for_torch_failing_to_load() {
        let jan = r#"OSError: [WinError 1114] Eine DLL-Initialisierungsroutine ist fehlgeschlagen. Error loading "C:\Users\werth\AppData\Local\DinoTraining\runtime\envs\1790853871801\Lib\site-packages\torch\lib\c10.dll" or one of its dependencies."#;
        let hint = backend_hint(jan).expect("Jan's traceback gets the hint");
        assert!(hint.contains(DOWNLOAD_URL) && hint.contains("14.40"));
        assert!(backend_hint(&jan.replace("1114", "126")).is_some());
        assert!(backend_hint("ModuleNotFoundError: No module named 'fastapi'").is_none());
        assert!(backend_hint("OSError: [WinError 1114] Error loading \"cudnn64_9.dll\"").is_none());
    }

    /// On a real Windows (CI's runner has Visual Studio): the registry is read, and new.
    #[cfg(windows)]
    #[test]
    fn the_runner_has_a_current_runtime() {
        let version = installed().expect("reg query found the runtime");
        assert!(!too_old(Some(version)), "{version}");
        assert!(!needed());
    }

    #[test]
    fn nothing_is_needed_off_windows() {
        if !cfg!(windows) {
            assert!(!needed());
            assert_eq!(ensure(), Ok(()));
        }
    }
}
