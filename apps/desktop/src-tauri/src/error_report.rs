//! "Open the log" and "Report an issue" beside an error (doc 140).
//!
//! The report is a **prefilled GitHub issue in the browser**: the user reads it and submits
//! it with their own account. Posting from the app would need a token inside a publicly
//! distributed binary, which is a secret given away. The home folder is replaced by `~`
//! in everything quoted, so a user name does not land in a public issue unnoticed.

use std::path::PathBuf;

use tauri::Manager;
use tauri_plugin_opener::OpenerExt;

use crate::backend_log;

const NEW_ISSUE: &str = "https://github.com/JanderHungrige/DinoTraining/issues/new";
/// GitHub refuses longer request lines; the log's quote shrinks to fit under this.
const MAX_URL: usize = 7_500;
const LOG_LINES: usize = 40;

fn log_path(app: &tauri::AppHandle) -> Option<PathBuf> {
    Some(app.path().app_log_dir().ok()?.join(backend_log::FILE))
}

/// Open `backend.log` in the system's default program for it (Notepad, TextEdit, …).
#[tauri::command]
pub fn open_backend_log(app: tauri::AppHandle) -> Result<String, String> {
    let path = log_path(&app).ok_or("No log folder")?;
    if !path.is_file() {
        return Err(format!("No log yet at {}", path.display()));
    }
    // Under the Store the log is in the package's folder (doc 156).
    let shown = crate::edition::shown_path(&path).display().to_string();
    app.opener()
        .open_path(&shown, None::<&str>)
        .map_err(|error| format!("Could not open {shown}: {error}"))?;
    Ok(shown)
}

/// Open a prefilled "new issue" page for `message`, with the log's last lines.
#[tauri::command]
pub fn report_issue(app: tauri::AppHandle, message: String) -> Result<(), String> {
    let log = log_path(&app).map(|path| backend_log::tail(&path, LOG_LINES)).unwrap_or_default();
    let home = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")).ok();
    let report = Report {
        message: &message,
        version: &app.package_info().version.to_string(),
        os: std::env::consts::OS,
        arch: std::env::consts::ARCH,
        log: &log,
        home: home.as_deref(),
    };
    let url = issue_url(&report);
    app.opener().open_url(url, None::<&str>).map_err(|error| error.to_string())
}

pub struct Report<'a> {
    pub message: &'a str,
    pub version: &'a str,
    pub os: &'a str,
    pub arch: &'a str,
    pub log: &'a str,
    pub home: Option<&'a str>,
}

/// The issue page's URL. Pure, so the redaction and the length limit are tested.
pub fn issue_url(report: &Report<'_>) -> String {
    let redact = |text: &str| match report.home.filter(|home| home.len() > 1) {
        Some(home) => text.replace(home, "~"),
        None => text.to_string(),
    };
    let message = redact(report.message);
    let first_line = message.lines().next().unwrap_or("").chars().take(80).collect::<String>();
    let title = format!("[{} {}] {}", report.os, report.version, first_line);
    let log = redact(report.log);
    let mut lines: Vec<&str> = log.lines().collect();
    loop {
        let body = body(&message, report, &lines.join("\n"));
        let url = reqwest::Url::parse_with_params(
            NEW_ISSUE,
            [("title", title.as_str()), ("body", body.as_str()), ("labels", "bug")],
        )
        .map(String::from)
        .unwrap_or_else(|_| NEW_ISSUE.to_string());
        // Drop the oldest log lines first: the end holds the traceback that matters.
        if url.len() <= MAX_URL || lines.is_empty() {
            return url;
        }
        lines.remove(0);
    }
}

fn body(message: &str, report: &Report<'_>, log: &str) -> String {
    let log = if log.is_empty() { "(no backend log)" } else { log };
    format!(
        "**What happened**\n\n<!-- What did you do just before? -->\n\n**The error**\n\n```\n{message}\n```\n\n\
         **DinoTraining** {} · {} {}\n\n**The backend log (last lines)**\n\n```\n{log}\n```\n",
        report.version, report.os, report.arch
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn report<'a>(message: &'a str, log: &'a str) -> Report<'a> {
        Report {
            message,
            version: "0.1.1",
            os: "windows",
            arch: "x86_64",
            log,
            home: Some(r"C:\Users\jan"),
        }
    }

    fn decoded(url: &str) -> String {
        let parsed = reqwest::Url::parse(url).unwrap();
        parsed.query_pairs().map(|(k, v)| format!("{k}={v}\n")).collect()
    }

    #[test]
    fn the_issue_carries_the_error_the_version_and_the_log() {
        let url = issue_url(&report("backend exited during startup (exit code: 1)", "ValueError: boom"));
        assert!(url.starts_with(NEW_ISSUE));
        let text = decoded(&url);
        assert!(text.contains("title=[windows 0.1.1] backend exited during startup (exit code: 1)"));
        assert!(text.contains("ValueError: boom"));
        assert!(text.contains("labels=bug"));
    }

    #[test]
    fn the_home_folder_never_reaches_the_issue() {
        let url = issue_url(&report(
            r"cannot open C:\Users\jan\AppData\Local\DinoTraining",
            r"File C:\Users\jan\x.py",
        ));
        let text = decoded(&url);
        assert!(!text.contains(r"C:\Users\jan"), "{text}");
        assert!(text.contains(r"~\AppData\Local\DinoTraining"));
    }

    #[test]
    fn a_long_log_is_cut_from_its_start_to_fit_githubs_limit() {
        let mut log = (0..2000).map(|i| format!("line {i} of a chatty log")).collect::<Vec<_>>();
        log.push("ValueError: the real reason".to_string());
        let url = issue_url(&report("failed", &log.join("\n")));
        assert!(url.len() <= MAX_URL, "{}", url.len());
        let text = decoded(&url);
        assert!(text.contains("ValueError: the real reason"));
        assert!(!text.contains("line 0 of"));
    }

    #[test]
    fn no_log_says_so() {
        assert!(decoded(&issue_url(&report("failed", ""))).contains("(no backend log)"));
    }
}

