//! Where this copy came from (doc 156): the Microsoft Store, the installer, or a dev build.
//!
//! The Store edition runs with a package identity. Windows redirects what it writes under
//! `AppData` into the package's own folder, which only the package sees under the original
//! path. Explorer runs outside the package, so a folder shown to the user is translated to
//! where Windows really put it.

use std::path::{Path, PathBuf};

use tauri_plugin_opener::OpenerExt;

/// The package family name when started with a package identity (MSIX), else `None`.
#[cfg(windows)]
pub fn package_family() -> Option<String> {
    #[link(name = "kernel32")]
    extern "system" {
        fn GetCurrentPackageFamilyName(length: *mut u32, name: *mut u16) -> i32;
    }
    const ERROR_INSUFFICIENT_BUFFER: i32 = 122;
    let mut length: u32 = 0;
    // Without a package this answers APPMODEL_ERROR_NO_PACKAGE (15700).
    // SAFETY: a null buffer with length 0 only asks for the needed length.
    let code = unsafe { GetCurrentPackageFamilyName(&mut length, std::ptr::null_mut()) };
    if code != ERROR_INSUFFICIENT_BUFFER || length == 0 {
        return None;
    }
    let mut name = vec![0u16; length as usize];
    // SAFETY: the buffer holds `length` UTF-16 units, as the first call asked for.
    let code = unsafe { GetCurrentPackageFamilyName(&mut length, name.as_mut_ptr()) };
    if code != 0 {
        log::warn!("GetCurrentPackageFamilyName failed with {code}");
        return None;
    }
    let end = name.iter().position(|&unit| unit == 0).unwrap_or(name.len());
    Some(String::from_utf16_lossy(&name[..end]))
}

#[cfg(not(windows))]
pub fn package_family() -> Option<String> {
    None
}

/// `store` under a package identity, `dev` for a debug build, else `installer`.
pub fn edition_of(family: Option<&str>, debug: bool) -> &'static str {
    match (family, debug) {
        (Some(_), _) => "store",
        (None, true) => "dev",
        (None, false) => "installer",
    }
}

#[tauri::command]
pub fn app_edition() -> &'static str {
    edition_of(package_family().as_deref(), cfg!(debug_assertions))
}

/// Where Windows puts `path` for the package `family`, if `path` lies under the user's
/// `AppData` (`local` = `%LOCALAPPDATA%`, `roaming` = `%APPDATA%`).
pub(crate) fn packaged_path(path: &Path, family: &str, local: Option<&Path>, roaming: Option<&Path>) -> Option<PathBuf> {
    let local = local?;
    let package = local.join("Packages").join(family).join("LocalCache");
    if path.starts_with(local.join("Packages")) {
        return None;
    }
    [(Some(local), "Local"), (roaming, "Roaming")].into_iter().find_map(|(base, part)| {
        let rest = path.strip_prefix(base?).ok()?;
        Some(package.join(part).join(rest))
    })
}

/// `path` as a process outside the package finds it: the redirected copy when it exists.
pub fn shown_path(path: &Path) -> PathBuf {
    let Some(family) = package_family() else {
        return path.to_path_buf();
    };
    let local = std::env::var_os("LOCALAPPDATA").map(PathBuf::from);
    let roaming = std::env::var_os("APPDATA").map(PathBuf::from);
    packaged_path(path, &family, local.as_deref(), roaming.as_deref())
        .filter(|redirected| redirected.exists())
        .unwrap_or_else(|| path.to_path_buf())
}

/// Show `path` selected in Explorer / Finder / the file manager (doc 59), where it really is.
#[tauri::command]
pub fn reveal_path(app: tauri::AppHandle, path: String) -> Result<String, String> {
    let shown = shown_path(Path::new(&path));
    app.opener()
        .reveal_item_in_dir(&shown)
        .map_err(|error| format!("Could not show {}: {error}", shown.display()))?;
    Ok(shown.display().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    const FAMILY: &str = "JeanQuestEnterprise.V-Rex_f2f23w3rhp35p";

    fn local() -> PathBuf {
        PathBuf::from("/Users/jan/AppData/Local")
    }

    fn roaming() -> PathBuf {
        PathBuf::from("/Users/jan/AppData/Roaming")
    }

    #[test]
    fn the_edition_follows_the_package_identity_first() {
        assert_eq!(edition_of(Some(FAMILY), false), "store");
        assert_eq!(edition_of(Some(FAMILY), true), "store");
        assert_eq!(edition_of(None, true), "dev");
        assert_eq!(edition_of(None, false), "installer");
    }

    #[test]
    fn local_and_roaming_paths_map_into_the_package_folder() {
        let data = local().join("DinoTraining/datasets/cars");
        assert_eq!(
            packaged_path(&data, FAMILY, Some(&local()), Some(&roaming())),
            Some(local().join("Packages").join(FAMILY).join("LocalCache/Local/DinoTraining/datasets/cars"))
        );
        let settings = roaming().join("com.dinotraining.app");
        assert_eq!(
            packaged_path(&settings, FAMILY, Some(&local()), Some(&roaming())),
            Some(local().join("Packages").join(FAMILY).join("LocalCache/Roaming/com.dinotraining.app"))
        );
    }

    #[test]
    fn paths_outside_appdata_or_already_in_the_package_stay() {
        let mine = PathBuf::from("/Users/jan/Pictures/cars");
        assert_eq!(packaged_path(&mine, FAMILY, Some(&local()), Some(&roaming())), None);
        let inside = local().join("Packages").join(FAMILY).join("LocalCache/Local/DinoTraining");
        assert_eq!(packaged_path(&inside, FAMILY, Some(&local()), Some(&roaming())), None);
        assert_eq!(packaged_path(&local().join("DinoTraining"), FAMILY, None, None), None);
    }

    #[test]
    fn without_a_package_the_shown_path_is_the_path() {
        let path = local().join("DinoTraining");
        if package_family().is_none() {
            assert_eq!(shown_path(&path), path);
        }
    }
}
