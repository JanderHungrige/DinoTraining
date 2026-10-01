; Doc 132: what Tauri's uninstaller does not reach. Tauri removes its own files by name and
; its "Delete the application data" checkbox clears the bundle identifier's folders only.
; DinoTraining keeps everything in %LOCALAPPDATA%\DinoTraining (the backend's folder; the
; app is installed there too):
;   runtime\   Python, PyTorch and uv's cache (1-6 GB), installed by the app itself
;   data\, models\, .env   the user's datasets, trained models, weights and settings
;
; Not while updating: an update reinstalls the app and keeps everything.

!macro NSIS_HOOK_POSTUNINSTALL
  ${If} $UpdateMode <> 1
    SetShellVarContext current
    ; The app can install these again; they are never the user's work.
    RMDir /r "$LOCALAPPDATA\DinoTraining\runtime"
    ; Builds before doc 132 kept the runtime in the roaming profile.
    RMDir /r "$APPDATA\DinoTraining\runtime"
    RMDir "$APPDATA\DinoTraining"
    ; The user's work goes only when they ticked "Delete the application data".
    ${If} $DeleteAppDataCheckboxState = 1
      RMDir /r "$LOCALAPPDATA\DinoTraining"
    ${EndIf}
    RMDir "$LOCALAPPDATA\DinoTraining"
  ${EndIf}
!macroend
