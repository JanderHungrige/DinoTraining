//! uv's install output turned into progress a person can follow (doc 127).
//!
//! Pure: lines in, state out. Weighted by megabytes, because one torch wheel is most of
//! the download and a count of packages would sit at 90 % while it arrives.

use std::collections::HashMap;

use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    /// Doc 141: Microsoft's Visual C++ runtime, before anything else (Windows only).
    Runtime,
    Python,
    Packages,
    Installing,
    Done,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Progress {
    pub phase: Phase,
    pub done_mb: f64,
    pub total_mb: f64,
    /// The last thing that finished downloading, for "torch done" under the bar.
    pub current: Option<String>,
}

#[derive(Debug)]
pub struct Tracker {
    sizes: HashMap<String, f64>,
    progress: Progress,
}

impl Default for Tracker {
    fn default() -> Self {
        Self {
            sizes: HashMap::new(),
            progress: Progress { phase: Phase::Python, done_mb: 0.0, total_mb: 0.0, current: None },
        }
    }
}

impl Tracker {
    /// Read one line of uv's output. Returns the new progress when the line changed it,
    /// so the caller emits only what moves the bar.
    pub fn read(&mut self, line: &str) -> Option<Progress> {
        let line = line.trim();
        if let Some(rest) = line.strip_prefix("Downloading ") {
            let (name, size) = split_size(rest)?;
            let name = display_name(name);
            if name.starts_with("cpython") {
                self.progress.phase = Phase::Python;
            } else if self.progress.phase == Phase::Python {
                self.progress.phase = Phase::Packages;
            }
            self.progress.total_mb += size;
            self.sizes.insert(name, size);
        } else if let Some(rest) = line.strip_prefix("Downloaded ") {
            let name = display_name(rest);
            let size = self.sizes.remove(&name)?;
            self.progress.done_mb += size;
            self.progress.current = Some(name);
        } else if line.starts_with("Prepared ") {
            self.progress.phase = Phase::Installing;
            self.progress.done_mb = self.progress.total_mb;
        } else if line.starts_with("Installed ") {
            self.progress.phase = Phase::Done;
        } else {
            return None;
        }
        Some(self.progress.clone())
    }
}

/// `torch (106.1MiB)` → (`torch`, 106.1). Sizes in MiB, rounded as uv prints them.
fn split_size(text: &str) -> Option<(&str, f64)> {
    let open = text.rfind(" (")?;
    let inner = text[open + 2..].strip_suffix(')')?;
    let (number, factor) = if let Some(n) = inner.strip_suffix("GiB") {
        (n, 1024.0)
    } else if let Some(n) = inner.strip_suffix("MiB") {
        (n, 1.0)
    } else {
        (inner.strip_suffix("KiB")?, 1.0 / 1024.0)
    };
    Some((&text[..open], number.parse::<f64>().ok()? * factor))
}

/// `cpython-3.12.14-macos-aarch64-none (download)` → `cpython-3.12.14-macos-aarch64-none`.
fn display_name(name: &str) -> String {
    name.trim().trim_end_matches(" (download)").to_string()
}

/// uv's last words, read as "no connection" when they say so (doc 127).
pub fn looks_offline(line: &str) -> bool {
    let line = line.to_lowercase();
    [
        "dns error",
        "failed to lookup address",
        "error sending request",
        "connection refused",
        "network is unreachable",
        "no such host",
        "timed out",
    ]
    .iter()
    .any(|marker| line.contains(marker))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Doc 126's real run, shortened.
    const RUN: &[&str] = &[
        "Downloading cpython-3.12.14-macos-aarch64-none (download) (23.9MiB)",
        " Downloaded cpython-3.12.14-macos-aarch64-none (download)",
        "Using CPython 3.12.14",
        "Creating virtual environment at: /x/env",
        "Downloading sympy (6.0MiB)",
        "Downloading torch (106.1MiB)",
        "Downloading tiny (512KiB)",
        " Downloaded sympy",
        " Downloaded tiny",
        " Downloaded torch",
        "Prepared 68 packages in 25.64s",
        "Installed 68 packages in 417ms",
        " + torch==2.13.0",
    ];

    fn replay(lines: &[&str]) -> (Tracker, Vec<Progress>) {
        let mut tracker = Tracker::default();
        let events = lines.iter().filter_map(|line| tracker.read(line)).collect();
        (tracker, events)
    }

    #[test]
    fn python_first_then_packages_by_megabyte() {
        let (_, events) = replay(&RUN[..2]);
        assert_eq!(events[0].phase, Phase::Python);
        assert!((events[1].done_mb - 23.9).abs() < 1e-9);
        assert_eq!(events[1].current.as_deref(), Some("cpython-3.12.14-macos-aarch64-none"));

        let (_, events) = replay(&RUN[..9]);
        let last = events.last().unwrap();
        assert_eq!(last.phase, Phase::Packages);
        assert!((last.total_mb - (23.9 + 6.0 + 106.1 + 0.5)).abs() < 1e-9);
        assert!((last.done_mb - (23.9 + 6.0 + 0.5)).abs() < 1e-9);
        assert_eq!(last.current.as_deref(), Some("tiny"));
    }

    #[test]
    fn prepared_fills_the_bar_and_installed_finishes() {
        let (_, events) = replay(RUN);
        let installing = events.iter().find(|p| p.phase == Phase::Installing).unwrap();
        assert_eq!(installing.done_mb, installing.total_mb);
        assert_eq!(events.last().unwrap().phase, Phase::Done);
    }

    #[test]
    fn lines_that_change_nothing_emit_nothing() {
        let mut tracker = Tracker::default();
        assert!(tracker.read("Using CPython 3.12.14").is_none());
        assert!(tracker.read(" + torch==2.13.0").is_none());
        // A "Downloaded" for something never announced (uv skips small files) is ignored.
        assert!(tracker.read(" Downloaded idna").is_none());
    }

    #[test]
    fn gigabytes_count_as_megabytes() {
        let mut tracker = Tracker::default();
        let progress = tracker.read("Downloading torch (2.4GiB)").unwrap();
        assert!((progress.total_mb - 2.4 * 1024.0).abs() < 1e-9);
    }

    #[test]
    fn connection_failures_read_as_offline() {
        assert!(looks_offline("  Caused by: dns error: failed to lookup address information"));
        assert!(looks_offline("error: Request failed after 3 retries: error sending request"));
        assert!(!looks_offline("error: No space left on device (os error 28)"));
    }
}
