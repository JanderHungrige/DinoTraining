//! The backend's output, in a file beside the app's own log (doc 139).
//!
//! The packaged app used to let the backend inherit its standard streams. A Windows GUI
//! app has none, so a failing start said "see the log above for the Python traceback"
//! about a log that did not exist (Jan's Windows PC, 0.1.0). Now the backend always
//! writes to `backend.log`, the previous run's stays as `backend.previous.log`, and a
//! failed start quotes the file's last lines in its error.

use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};

pub const FILE: &str = "backend.log";
const PREVIOUS: &str = "backend.previous.log";
/// Enough for a Python traceback; bounded so a chatty log cannot bloat the error.
const TAIL_BYTES: u64 = 16 * 1024;

/// A fresh `backend.log` in `dir`, keeping the last run's beside it.
pub fn create(dir: &Path) -> std::io::Result<(File, PathBuf)> {
    std::fs::create_dir_all(dir)?;
    let path = dir.join(FILE);
    if path.exists() {
        // Best effort: a locked previous log must not stop the backend from starting.
        let _ = std::fs::rename(&path, dir.join(PREVIOUS));
    }
    Ok((File::create(&path)?, path))
}

/// The last `lines` non-empty lines of `path`, or "" when it cannot be read.
pub fn tail(path: &Path, lines: usize) -> String {
    let Ok(mut file) = File::open(path) else { return String::new() };
    let length = file.metadata().map(|meta| meta.len()).unwrap_or(0);
    let start = length.saturating_sub(TAIL_BYTES);
    if file.seek(SeekFrom::Start(start)).is_err() {
        return String::new();
    }
    let mut bytes = Vec::new();
    if file.read_to_end(&mut bytes).is_err() {
        return String::new();
    }
    let text = String::from_utf8_lossy(&bytes);
    let kept: Vec<&str> = text.lines().filter(|line| !line.trim().is_empty()).collect();
    kept[kept.len().saturating_sub(lines)..].join("\n")
}

/// The backend's last words for an error message: the log's tail when there is a log
/// folder, else where to look instead.
pub fn quote(dir: Option<&Path>) -> String {
    let Some(dir) = dir else {
        return " See the terminal for the Python traceback.".to_string();
    };
    let path = dir.join(FILE);
    match tail(&path, 15) {
        lines if lines.is_empty() => format!(" It wrote nothing to {}.", path.display()),
        lines => format!("\n\nIts last output ({}):\n{lines}", path.display()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("dino-backend-log-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        dir
    }

    #[test]
    fn a_new_run_keeps_the_previous_log() {
        let dir = temp("rotate");
        let (_, first) = create(&dir).unwrap();
        std::fs::write(&first, "run one\n").unwrap();
        let (_, second) = create(&dir).unwrap();
        assert_eq!(second, dir.join(FILE));
        assert_eq!(std::fs::read_to_string(dir.join(PREVIOUS)).unwrap(), "run one\n");
        assert_eq!(std::fs::read_to_string(second).unwrap(), "");
    }

    #[test]
    fn the_tail_is_the_last_lines_without_blanks() {
        let dir = temp("tail");
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join(FILE);
        std::fs::write(&path, "a\n\nb\nTraceback (most recent call last):\n\nValueError: boom\n").unwrap();
        assert_eq!(tail(&path, 2), "Traceback (most recent call last):\nValueError: boom");
        assert_eq!(tail(&path, 50).lines().count(), 4);
    }

    #[test]
    fn a_huge_log_is_read_from_its_end_only() {
        let dir = temp("huge");
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join(FILE);
        let mut text = "noise\n".repeat(100_000);
        text.push_str("ValueError: the real reason\n");
        std::fs::write(&path, text).unwrap();
        assert!(tail(&path, 1).ends_with("ValueError: the real reason"));
    }

    #[test]
    fn the_error_quotes_the_traceback_or_says_where_to_look() {
        let dir = temp("quote");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join(FILE), "ValueError: Unable to configure formatter 'default'\n").unwrap();
        let quoted = quote(Some(&dir));
        assert!(quoted.contains("Unable to configure formatter"), "{quoted}");
        assert!(quoted.contains(FILE));
        std::fs::write(dir.join(FILE), "").unwrap();
        assert!(quote(Some(&dir)).contains("wrote nothing"));
        assert!(quote(None).contains("terminal"));
    }

    #[test]
    fn a_missing_log_gives_nothing() {
        assert_eq!(tail(Path::new("/definitely/not/here/backend.log"), 5), "");
    }
}
