; Doc 132: what Tauri's uninstaller does not reach. Tauri removes its own files by name and
; its "Delete the application data" checkbox clears the bundle identifier's folders only.
; DinoTraining keeps everything in %LOCALAPPDATA%\DinoTraining (the backend's folder; the
; app is installed there too):
;   runtime\   Python, PyTorch and uv's cache (1-6 GB), installed by the app itself
;   data\, models\, .env   the user's datasets, trained models, weights and settings
;
; Not while updating: an update reinstalls the app and keeps everything.

; Removing a tree NSIS cannot remove alone. Found by doc 131's CI on the first two runs:
; - RMDir /r stops at paths beyond MAX_PATH (260 characters), and uv's cache and
;   PyTorch's site-packages go far deeper: 5 files stayed in cache\ and envs\.
;   `rd` with the \\?\ prefix has no such limit;
; - read-only files: attrib clears them first (best effort, short paths).
; nsExec runs both without a console window. RMDir /r afterwards catches the rest.
!macro DINO_REMOVE_TREE DIR
  ${If} ${FileExists} "${DIR}\*.*"
    DetailPrint "Removing ${DIR}"
    nsExec::Exec 'attrib -R "${DIR}\*" /S /D'
    Pop $0
    nsExec::Exec '"$SYSDIR\cmd.exe" /c rd /s /q "\\?\${DIR}"'
    Pop $0
    RMDir /r "${DIR}"
  ${EndIf}
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  ${If} $UpdateMode <> 1
    SetShellVarContext current
    ; The app can install these again; they are never the user's work.
    !insertmacro DINO_REMOVE_TREE "$LOCALAPPDATA\DinoTraining\runtime"
    ; Builds before doc 132 kept the runtime in the roaming profile.
    !insertmacro DINO_REMOVE_TREE "$APPDATA\DinoTraining\runtime"
    RMDir "$APPDATA\DinoTraining"
    ; The user's work goes only when they ticked "Delete the application data".
    ${If} $DeleteAppDataCheckboxState = 1
      !insertmacro DINO_REMOVE_TREE "$LOCALAPPDATA\DinoTraining"
    ${EndIf}
    RMDir "$LOCALAPPDATA\DinoTraining"
  ${EndIf}
!macroend
