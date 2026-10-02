//! "Add to Applications" for the Homebrew install (doc 130).
//!
//! A formula may not write outside its prefix, so the app offers it itself: a symbolic
//! link in `~/Applications` to Homebrew's version-independent `opt` path, which
//! survives `brew upgrade`. Only offered when the app runs from a Cellar.

use std::path::{Component, Path, PathBuf};

const FORMULA: &str = "v-rex";
const APP: &str = "V-Rex.app";

/// `<prefix>/Cellar/v-rex/<v>/V-Rex.app/…` → `<prefix>/opt/v-rex/V-Rex.app`.
pub fn homebrew_app(exe: &Path) -> Option<PathBuf> {
    let parts: Vec<Component<'_>> = exe.components().collect();
    let cellar = parts.windows(2).position(|pair| {
        pair[0].as_os_str() == "Cellar" && pair[1].as_os_str() == FORMULA
    })?;
    let prefix: PathBuf = parts[..cellar].iter().collect();
    Some(prefix.join("opt").join(FORMULA).join(APP))
}

/// The executable with symbolic links resolved. The `v-rex` command starts the app
/// through Homebrew's `opt/v-rex` link, and only the resolved path shows the
/// Cellar (found live, doc 130).
fn running_from() -> Option<PathBuf> {
    std::fs::canonicalize(std::env::current_exe().ok()?).ok()
}

fn applications_link() -> Option<PathBuf> {
    let home = std::env::var_os("HOME")?;
    Some(PathBuf::from(home).join("Applications").join(APP))
}

/// The link to offer, when the app runs from Homebrew and none exists yet.
fn offer() -> Option<(PathBuf, PathBuf)> {
    if !cfg!(target_os = "macos") {
        return None;
    }
    let source = homebrew_app(&running_from()?)?;
    let link = applications_link()?;
    // symlink_metadata: a dangling link is still "already there", and not replaced.
    link.symlink_metadata().is_err().then_some((source, link))
}

/// The folder the app would be added to, or `None` when there is nothing to offer.
#[tauri::command]
pub fn applications_offer() -> Option<String> {
    let (source, link) = offer()?;
    log::info!("Offering to link {} to {}", link.display(), source.display());
    Some(link.display().to_string())
}

#[tauri::command]
pub fn add_to_applications() -> Result<String, String> {
    let (source, link) = offer().ok_or("Nothing to add: not a Homebrew install, or already added.")?;
    if let Some(folder) = link.parent() {
        std::fs::create_dir_all(folder).map_err(|error| error.to_string())?;
    }
    #[cfg(unix)]
    std::os::unix::fs::symlink(&source, &link).map_err(|error| error.to_string())?;
    log::info!("Linked {} to {}", link.display(), source.display());
    Ok(link.display().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_cellar_path_points_at_the_opt_path() {
        let exe = Path::new(
            "/opt/homebrew/Cellar/v-rex/0.2.0/V-Rex.app/Contents/MacOS/dinotraining",
        );
        assert_eq!(
            homebrew_app(exe),
            Some(PathBuf::from("/opt/homebrew/opt/v-rex/V-Rex.app"))
        );
    }

    #[test]
    fn a_custom_homebrew_prefix_works_too() {
        let exe = Path::new("/Users/jan/brew/Cellar/v-rex/1.0.0/V-Rex.app/Contents/MacOS/x");
        assert_eq!(
            homebrew_app(exe),
            Some(PathBuf::from("/Users/jan/brew/opt/v-rex/V-Rex.app"))
        );
    }

    #[cfg(unix)]
    #[test]
    fn a_start_through_the_opt_link_is_resolved_to_the_cellar() {
        let root = std::env::temp_dir().join(format!("dino-mac-apps-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let macos = root.join("Cellar/v-rex/0.2.0/V-Rex.app/Contents/MacOS");
        std::fs::create_dir_all(&macos).unwrap();
        std::fs::write(macos.join("dinotraining"), "").unwrap();
        std::fs::create_dir_all(root.join("opt")).unwrap();
        std::os::unix::fs::symlink("../Cellar/v-rex/0.2.0", root.join("opt/v-rex")).unwrap();

        let through_opt = root.join("opt/v-rex/V-Rex.app/Contents/MacOS/dinotraining");
        assert_eq!(homebrew_app(&through_opt), None, "the unresolved path hides the Cellar");
        let resolved = std::fs::canonicalize(&through_opt).unwrap();
        let expected = std::fs::canonicalize(&root).unwrap().join("opt/v-rex/V-Rex.app");
        assert_eq!(homebrew_app(&resolved), Some(expected));
    }

    #[test]
    fn anywhere_else_there_is_nothing_to_offer() {
        for exe in [
            "/Users/jan/Applications/V-Rex.app/Contents/MacOS/dinotraining",
            "/opt/homebrew/Cellar/other/1.0/V-Rex.app/Contents/MacOS/dinotraining",
            "/Applications/Cellar.app/Contents/MacOS/dinotraining",
        ] {
            assert_eq!(homebrew_app(Path::new(exe)), None, "{exe}");
        }
    }
}
