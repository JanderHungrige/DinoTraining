//! First-run setup (doc 127): which machine this is, which PyTorch it gets, and whether
//! the install can start at all.
//!
//! The choice is a pure function of what was detected, so every row of doc 127's table is
//! a unit test and no test needs an NVIDIA card.

use std::net::{TcpStream, ToSocketAddrs};
use std::path::Path;
use std::process::Command;
use std::time::Duration;

use serde::Serialize;

use crate::runtime::hide_console;

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Gpu {
    pub name: String,
    pub driver: String,
}

/// Why a machine gets less than the best, or nothing. The UI words it (doc 111).
#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Note {
    IntelMac,
    UnsupportedPlatform { os: String, arch: String },
    DriverTooOld { driver: String, needed: u32 },
}

/// A variant the user may pick, with what it costs.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Choice {
    pub variant: &'static str,
    pub download_gb: f64,
    pub disk_gb: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Machine {
    pub os: String,
    pub arch: String,
    pub apple_silicon: bool,
    pub gpu: Option<Gpu>,
    /// Recommended first; empty when the machine is refused.
    pub choices: Vec<Choice>,
    pub note: Option<Note>,
}

/// Measured in doc 126 for `cpu` (Python 73 MB, environment 869 MB, cache 821 MB); CUDA
/// adds NVIDIA's libraries, about 2.5 GB more downloaded and twice that installed.
const CPU: Choice = Choice { variant: "cpu", download_gb: 1.0, disk_gb: 3.0 };
const CU130: Choice = Choice { variant: "cu130", download_gb: 3.5, disk_gb: 10.0 };
const CU126: Choice = Choice { variant: "cu126", download_gb: 3.5, disk_gb: 10.0 };
/// The drivers the two CUDA builds need (NVIDIA's CUDA release notes).
const CU130_DRIVER: u32 = 580;
const CU126_DRIVER: u32 = 560;

/// Doc 127's table.
pub fn choose(os: &str, arch: &str, gpu: Option<Gpu>) -> Machine {
    let mut machine = Machine {
        os: os.to_string(),
        arch: arch.to_string(),
        apple_silicon: os == "macos" && arch == "aarch64",
        gpu: None,
        choices: Vec::new(),
        note: None,
    };
    match (os, arch) {
        ("macos", "aarch64") => machine.choices = vec![CPU],
        ("macos", _) => machine.note = Some(Note::IntelMac),
        ("windows" | "linux", "x86_64") => {
            let major = gpu.as_ref().and_then(|gpu| driver_major(&gpu.driver));
            machine.choices = match major {
                Some(major) if major >= CU130_DRIVER => vec![CU130, CPU],
                Some(major) if major >= CU126_DRIVER => vec![CU126, CPU],
                _ => vec![CPU],
            };
            if let (Some(gpu), Some(major)) = (&gpu, major) {
                if major < CU126_DRIVER {
                    machine.note = Some(Note::DriverTooOld {
                        driver: gpu.driver.clone(),
                        needed: CU126_DRIVER,
                    });
                }
            }
            machine.gpu = gpu;
        }
        _ => {
            machine.note = Some(Note::UnsupportedPlatform { os: os.into(), arch: arch.into() })
        }
    }
    machine
}

fn driver_major(driver: &str) -> Option<u32> {
    driver.trim().split('.').next()?.parse().ok()
}

/// `nvidia-smi`'s first line: `NVIDIA GeForce RTX 4070, 581.15`.
pub fn parse_nvidia_smi(output: &str) -> Option<Gpu> {
    let line = output.lines().find(|line| !line.trim().is_empty())?;
    let (name, driver) = line.rsplit_once(',')?;
    driver_major(driver)?;
    Some(Gpu { name: name.trim().to_string(), driver: driver.trim().to_string() })
}

/// The machine this runs on. `nvidia-smi` ships with every NVIDIA driver; without it
/// there is no card PyTorch could use.
pub fn detect() -> Machine {
    let gpu = if cfg!(target_os = "macos") {
        None
    } else {
        let mut command = Command::new("nvidia-smi");
        command.args(["--query-gpu=name,driver_version", "--format=csv,noheader"]);
        hide_console(&mut command);
        command
            .output()
            .ok()
            .filter(|output| output.status.success())
            .and_then(|output| parse_nvidia_smi(&String::from_utf8_lossy(&output.stdout)))
    };
    choose(std::env::consts::OS, std::env::consts::ARCH, gpu)
}

/// Why an install cannot start or did not finish. The UI words each kind (doc 111).
#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum SetupFailure {
    Unsupported,
    Disk { needed_gb: f64, free_gb: f64, path: String },
    Offline,
    Failed { message: String },
}

/// Free space where the runtime goes. The folder may not exist yet; its nearest
/// existing parent is on the same disk.
pub fn check_disk(root: &Path, choice: &Choice) -> Result<(), SetupFailure> {
    let existing = root.ancestors().find(|path| path.exists()).unwrap_or(root);
    let Ok(free) = fs4::available_space(existing) else {
        // Unknown is not "full": let uv try and report a real failure.
        log::warn!("Could not read the free space at {}", existing.display());
        return Ok(());
    };
    let free_gb = free as f64 / 1024f64.powi(3);
    if free_gb < choice.disk_gb {
        return Err(SetupFailure::Disk {
            needed_gb: choice.disk_gb,
            free_gb: (free_gb * 10.0).floor() / 10.0,
            path: existing.display().to_string(),
        });
    }
    Ok(())
}

/// The servers the install needs: PyPI for the packages, GitHub for Python itself. A TCP
/// connection is enough to tell "offline" from "a server said no".
pub fn check_online() -> Result<(), SetupFailure> {
    for host in ["pypi.org:443", "github.com:443"] {
        let reachable = host
            .to_socket_addrs()
            .ok()
            .and_then(|mut addresses| addresses.next())
            .is_some_and(|address| {
                TcpStream::connect_timeout(&address, Duration::from_secs(10)).is_ok()
            });
        if !reachable {
            log::warn!("{host} is not reachable");
            return Err(SetupFailure::Offline);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn nvidia(driver: &str) -> Option<Gpu> {
        Some(Gpu { name: "NVIDIA GeForce RTX 4070".into(), driver: driver.into() })
    }

    fn variants(machine: &Machine) -> Vec<&str> {
        machine.choices.iter().map(|choice| choice.variant).collect()
    }

    #[test]
    fn apple_silicon_gets_the_mac_wheels_with_mps() {
        let machine = choose("macos", "aarch64", None);
        assert_eq!(variants(&machine), ["cpu"]);
        assert!(machine.apple_silicon && machine.note.is_none());
    }

    #[test]
    fn an_intel_mac_is_refused_before_anything_downloads() {
        let machine = choose("macos", "x86_64", None);
        assert!(machine.choices.is_empty());
        assert_eq!(machine.note, Some(Note::IntelMac));
    }

    #[test]
    fn the_driver_decides_the_cuda_build() {
        assert_eq!(variants(&choose("windows", "x86_64", nvidia("581.15"))), ["cu130", "cpu"]);
        assert_eq!(variants(&choose("linux", "x86_64", nvidia("580.65.06"))), ["cu130", "cpu"]);
        assert_eq!(variants(&choose("linux", "x86_64", nvidia("565.57.01"))), ["cu126", "cpu"]);
        assert_eq!(variants(&choose("windows", "x86_64", None)), ["cpu"]);
    }

    #[test]
    fn an_old_driver_gets_the_cpu_and_the_reason() {
        let machine = choose("windows", "x86_64", nvidia("535.98"));
        assert_eq!(variants(&machine), ["cpu"]);
        assert_eq!(
            machine.note,
            Some(Note::DriverTooOld { driver: "535.98".into(), needed: 560 })
        );
        assert!(machine.gpu.is_some(), "the card is still named");
    }

    #[test]
    fn platforms_outside_the_lock_are_refused() {
        let machine = choose("linux", "aarch64", None);
        assert!(machine.choices.is_empty());
        assert!(matches!(machine.note, Some(Note::UnsupportedPlatform { .. })));
    }

    #[test]
    fn nvidia_smi_output_is_read() {
        let gpu = parse_nvidia_smi("NVIDIA GeForce RTX 5090, 581.15\nNVIDIA T4, 581.15\n");
        assert_eq!(gpu, Some(Gpu { name: "NVIDIA GeForce RTX 5090".into(), driver: "581.15".into() }));
        assert_eq!(parse_nvidia_smi(""), None);
        assert_eq!(parse_nvidia_smi("No devices were found"), None);
    }

    #[test]
    fn too_little_disk_says_how_much() {
        let huge = Choice { variant: "cpu", download_gb: 1.0, disk_gb: 1.0e9 };
        let missing = std::env::temp_dir().join("dino-setup-does-not-exist").join("runtime");
        match check_disk(&missing, &huge) {
            Err(SetupFailure::Disk { needed_gb, free_gb, .. }) => {
                assert_eq!(needed_gb, 1.0e9);
                assert!(free_gb > 0.0);
            }
            other => panic!("expected a disk failure, got {other:?}"),
        }
    }
}
