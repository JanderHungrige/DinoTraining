//! "A new version is available" (doc 158): asked once at start, for the editions that do
//! not update themselves.
//!
//! The Store updates its edition (doc 156), and a dev build is whatever is checked out, so
//! only the installer edition asks. The answer comes from the download site's
//! `latest.json` (doc 133), with GitHub's latest release as the fallback. Offline, slow or
//! malformed answers are logged and stay silent: a check that fails must never be in the
//! user's way. `DINO_UPDATE_CHECK=0` turns it off.

use std::time::Duration;

use serde::Serialize;

const LATEST_JSON: &str = "https://dino.w3rth.de/latest.json";
const GITHUB_LATEST: &str = "https://api.github.com/repos/JanderHungrige/DinoTraining/releases/latest";
/// Where the user gets it: the site gives each platform its own way.
pub const DOWNLOAD_PAGE: &str = "https://dino.w3rth.de";
const TIMEOUT: Duration = Duration::from_secs(8);

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Update {
    pub current: String,
    pub latest: String,
    /// The release notes.
    pub notes: String,
    pub download: String,
}

/// `x.y.z` (a leading `v`, and anything after a `-` or `+`, ignored) as numbers.
pub(crate) fn parse_version(text: &str) -> Option<(u64, u64, u64)> {
    let core = text.trim().trim_start_matches('v');
    let core = core.split(['-', '+']).next()?;
    let mut parts = core.split('.').map(|part| part.parse::<u64>().ok());
    let version = (parts.next()??, parts.next()??, parts.next()??);
    parts.next().is_none().then_some(version)
}

/// The update for `current`, if `latest` is newer.
pub(crate) fn newer(current: &str, latest: &str, notes: &str) -> Option<Update> {
    (parse_version(latest)? > parse_version(current)?).then(|| Update {
        current: current.to_string(),
        latest: latest.trim().trim_start_matches('v').to_string(),
        notes: notes.to_string(),
        download: DOWNLOAD_PAGE.to_string(),
    })
}

/// Version and notes from `latest.json` (`version`, `html_url`) or a GitHub release
/// (`tag_name`, `html_url`).
pub(crate) fn read_answer(body: &serde_json::Value) -> Option<(String, String)> {
    let version = body
        .get("version")
        .and_then(|value| value.as_str())
        .or_else(|| body.get("tag_name").and_then(|value| value.as_str()))?;
    let notes = body.get("html_url").and_then(|value| value.as_str()).unwrap_or(DOWNLOAD_PAGE);
    Some((version.to_string(), notes.to_string()))
}

async fn ask(client: &reqwest::Client, url: &str) -> Result<(String, String), String> {
    let response = client.get(url).send().await.map_err(|error| error.to_string())?;
    let response = response.error_for_status().map_err(|error| error.to_string())?;
    let body: serde_json::Value = response.json().await.map_err(|error| error.to_string())?;
    read_answer(&body).ok_or_else(|| format!("no version in the answer from {url}"))
}

pub(crate) fn turned_off(value: Option<String>) -> bool {
    matches!(value.as_deref().map(str::trim), Some("0" | "false" | "off" | "no"))
}

#[tauri::command]
pub async fn check_for_update(app: tauri::AppHandle) -> Option<Update> {
    let edition = crate::edition::app_edition();
    if edition != "installer" || turned_off(std::env::var("DINO_UPDATE_CHECK").ok()) {
        log::info!("Update check skipped ({edition} edition or DINO_UPDATE_CHECK=0)");
        return None;
    }
    let current = app.package_info().version.to_string();
    let client = reqwest::Client::builder()
        .timeout(TIMEOUT)
        .user_agent(format!("DinoTraining/{current}"))
        .build()
        .map_err(|error| log::warn!("Update check: no HTTP client: {error}"))
        .ok()?;
    let mut answer = Err(String::new());
    for url in [LATEST_JSON, GITHUB_LATEST] {
        answer = ask(&client, url).await;
        match &answer {
            Ok(_) => break,
            Err(error) => log::warn!("Update check via {url} failed: {error}"),
        }
    }
    let (latest, notes) = answer.ok()?;
    let update = newer(&current, &latest, &notes);
    log::info!("Update check: running {current}, latest {latest}");
    update
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn versions_compare_as_numbers_not_text() {
        assert_eq!(parse_version("0.1.10"), Some((0, 1, 10)));
        assert_eq!(parse_version("v1.2.3"), Some((1, 2, 3)));
        assert_eq!(parse_version("1.2.3-beta.1"), Some((1, 2, 3)));
        assert_eq!(parse_version("1.2"), None);
        assert_eq!(parse_version("1.2.3.4"), None);
        assert_eq!(parse_version("latest"), None);
        assert!(newer("0.1.9", "0.1.10", "n").is_some(), "10 > 9, although '1' < '9'");
    }

    #[test]
    fn only_a_newer_release_is_an_update() {
        let update = newer("0.1.2", "v0.1.3", "https://notes").unwrap();
        assert_eq!(update.latest, "0.1.3");
        assert_eq!(update.current, "0.1.2");
        assert_eq!(update.notes, "https://notes");
        assert_eq!(update.download, DOWNLOAD_PAGE);
        assert_eq!(newer("0.1.2", "0.1.2", ""), None);
        assert_eq!(newer("0.2.0", "0.1.9", ""), None, "a dev build ahead of the release");
        assert_eq!(newer("0.1.2", "garbage", ""), None);
    }

    #[test]
    fn both_sources_are_read() {
        let site = serde_json::json!({ "version": "0.1.3", "html_url": "https://gh/v0.1.3" });
        assert_eq!(read_answer(&site), Some(("0.1.3".into(), "https://gh/v0.1.3".into())));
        let github = serde_json::json!({ "tag_name": "v0.1.3", "html_url": "https://gh/v0.1.3" });
        assert_eq!(read_answer(&github), Some(("v0.1.3".into(), "https://gh/v0.1.3".into())));
        // The site before the first release writes `"version": null`.
        assert_eq!(read_answer(&serde_json::json!({ "version": null })), None);
    }

    #[test]
    fn the_check_can_be_turned_off() {
        assert!(turned_off(Some("0".into())));
        assert!(turned_off(Some(" off ".into())));
        assert!(!turned_off(Some("1".into())));
        assert!(!turned_off(None));
    }
}
