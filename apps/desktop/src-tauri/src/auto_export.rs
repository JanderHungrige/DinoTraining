//! Doc 144: on quitting, the backend exports every changed dataset before it is stopped.
//!
//! The shell holds the exit once, asks `POST /exports/run` with a deadline, waits a little
//! longer than that, then stops the backend and exits. Whether to export on closing is the
//! backend's setting; with it off the run answers at once. A second quit while waiting
//! exits at once.

use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

/// What the backend may spend on exports before it is asked to stop.
pub const DEADLINE_SECONDS: u64 = 20;
/// How long the shell waits for the answer: the deadline plus a dataset already writing.
pub const WAIT: Duration = Duration::from_secs(DEADLINE_SECONDS + 5);

/// Set once the exit is held for exports, so the next quit is not held again.
#[derive(Default)]
pub struct Closing(AtomicBool);

impl Closing {
    /// True the first time only: hold this exit.
    pub fn begin(&self) -> bool {
        !self.0.swap(true, Ordering::SeqCst)
    }
}

pub fn request_body() -> serde_json::Value {
    serde_json::json!({ "reason": "close", "wait": true, "deadline_seconds": DEADLINE_SECONDS })
}

/// One log line from the answer: what went, what did not.
pub fn summary(answer: &serde_json::Value) -> String {
    let outcome = answer["outcome"].as_str().unwrap_or("unknown");
    let count = |key: &str| answer["report"][key].as_array().map_or(0, Vec::len);
    if outcome != "done" {
        return format!("Exports on closing: {outcome}");
    }
    format!(
        "Exports on closing: {} exported, {} failed, {} unfinished, {} without a target",
        count("exported"),
        count("failed"),
        count("unfinished"),
        count("no_target")
    )
}

/// Ask the backend to export what changed; errors are logged by the caller, never fatal.
pub async fn run_before_exit(base_url: &str) -> Result<String, String> {
    let client = reqwest::Client::builder().timeout(WAIT).build().map_err(|error| error.to_string())?;
    let response = client
        .post(format!("{base_url}/api/v1/exports/run"))
        .json(&request_body())
        .send()
        .await
        .map_err(|error| error.to_string())?;
    let answer: serde_json::Value = response.json().await.map_err(|error| error.to_string())?;
    Ok(summary(&answer))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_exit_is_held_once() {
        let closing = Closing::default();
        assert!(closing.begin());
        assert!(!closing.begin());
    }

    #[test]
    fn the_request_and_its_summary() {
        let body = request_body();
        assert_eq!(body["reason"], "close");
        assert_eq!(body["wait"], true);
        assert_eq!(body["deadline_seconds"], DEADLINE_SECONDS);
        assert!(WAIT > Duration::from_secs(DEADLINE_SECONDS));
        let done = serde_json::json!({
            "outcome": "done",
            "report": { "exported": [{}, {}], "failed": [], "unfinished": [{}], "no_target": [] }
        });
        assert_eq!(summary(&done), "Exports on closing: 2 exported, 0 failed, 1 unfinished, 0 without a target");
        assert_eq!(summary(&serde_json::json!({ "outcome": "off" })), "Exports on closing: off");
    }
}
