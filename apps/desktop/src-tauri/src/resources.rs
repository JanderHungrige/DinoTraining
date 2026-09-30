//! Where the bundled resources are (docs 126, 130).
//!
//! Tauri's `resource_dir` refuses on macOS when the app was started through a symbolic
//! link: Homebrew's `opt/dinotraining` path, or the link "Add to Applications" makes. The
//! refusal guards against relaunching through a planted link; reading resources from
//! the *resolved* path reads them from the real bundle, which is the safe direction.
//! Found live: without this, a Homebrew start found no runtime.

use std::path::{Path, PathBuf};

use tauri::Manager;

/// Tauri's answer, or the same answer from the resolved executable.
pub fn resource_dir(app: &tauri::AppHandle) -> Option<PathBuf> {
    app.path().resource_dir().ok().or_else(|| {
        let exe = std::fs::canonicalize(std::env::current_exe().ok()?).ok()?;
        let dir = macos_resources(&exe).filter(|_| cfg!(target_os = "macos"))?;
        log::info!("Started through a link; resources from {}", dir.display());
        Some(dir)
    })
}

/// `…/X.app/Contents/MacOS/x` → `…/X.app/Contents/Resources`.
pub fn macos_resources(exe: &Path) -> Option<PathBuf> {
    let contents = exe.parent()?.parent()?;
    (contents.file_name()? == "Contents").then(|| contents.join("Resources"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_resources_sit_beside_the_macos_folder() {
        let exe = Path::new("/opt/homebrew/Cellar/dinotraining/0.2.0/DinoTraining.app/Contents/MacOS/dinotraining");
        assert_eq!(
            macos_resources(exe),
            Some(PathBuf::from("/opt/homebrew/Cellar/dinotraining/0.2.0/DinoTraining.app/Contents/Resources"))
        );
    }

    #[test]
    fn a_binary_outside_a_bundle_has_none() {
        assert_eq!(macos_resources(Path::new("/usr/bin/dinotraining")), None);
        assert_eq!(macos_resources(Path::new("dinotraining")), None);
    }
}
