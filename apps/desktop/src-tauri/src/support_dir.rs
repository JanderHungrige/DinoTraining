//! The app's own folder per platform (doc 132): the backend's `default_data_dir`
//! (app/core/paths.py), so `runtime/` sits beside `data/` and `models/`.

use std::ffi::OsString;
use std::path::PathBuf;

pub fn app_support_root() -> Option<PathBuf> {
    support_root(std::env::consts::OS, |key| std::env::var_os(key))
}

/// Per platform, from the environment:
/// - macOS: `~/Library/Application Support/DinoTraining`;
/// - Windows: `%LOCALAPPDATA%\DinoTraining`. Not `%APPDATA%`, the roaming profile a
///   company network copies at every logon: no place for gigabytes of PyTorch;
/// - Linux: `$XDG_DATA_HOME/DinoTraining`, or `~/.local/share/DinoTraining`.
pub fn support_root(os: &str, var: impl Fn(&str) -> Option<OsString>) -> Option<PathBuf> {
    let home = || var("HOME").or_else(|| var("USERPROFILE")).map(PathBuf::from);
    let base = match os {
        "macos" => home()?.join("Library").join("Application Support"),
        "windows" => var("LOCALAPPDATA")
            .map(PathBuf::from)
            .or_else(|| home().map(|home| home.join("AppData").join("Local")))?,
        _ => var("XDG_DATA_HOME")
            .filter(|value| !value.is_empty())
            .map(PathBuf::from)
            .or_else(|| home().map(|home| home.join(".local").join("share")))?,
    };
    Some(base.join("DinoTraining"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn vars(pairs: &'static [(&'static str, &'static str)]) -> impl Fn(&str) -> Option<OsString> {
        move |key| pairs.iter().find(|(k, _)| *k == key).map(|(_, v)| (*v).into())
    }

    #[test]
    fn windows_keeps_the_runtime_local_beside_the_data_not_roaming() {
        let root = support_root(
            "windows",
            vars(&[
                ("APPDATA", r"C:\Users\jan\AppData\Roaming"),
                ("LOCALAPPDATA", r"C:\Users\jan\AppData\Local"),
            ]),
        );
        let local = PathBuf::from(r"C:\Users\jan\AppData\Local");
        assert_eq!(root, Some(local.join("DinoTraining")));
    }

    #[test]
    fn linux_honours_xdg_data_home_like_the_backend() {
        let with = support_root("linux", vars(&[("HOME", "/home/jan"), ("XDG_DATA_HOME", "/xdg")]));
        assert_eq!(with, Some(PathBuf::from("/xdg/DinoTraining")));
        let empty = support_root("linux", vars(&[("HOME", "/home/jan"), ("XDG_DATA_HOME", "")]));
        assert_eq!(empty, Some(PathBuf::from("/home/jan/.local/share/DinoTraining")));
    }

    #[test]
    fn macos_uses_application_support() {
        let root = support_root("macos", vars(&[("HOME", "/Users/jan")]));
        let expected = PathBuf::from("/Users/jan/Library/Application Support/DinoTraining");
        assert_eq!(root, Some(expected));
    }
}
