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

; Doc 146: before anything is removed, and only when the user's work would go with it
; ("Delete the application data" ticked): say that exports stay, and offer to stop.
; Not while updating, not unattended (/S, /P): doc 131's smoke test removes silently.
!macro NSIS_HOOK_PREUNINSTALL
  ${If} $UpdateMode <> 1
  ${AndIf} $PassiveMode <> 1
  ${AndIf} $DeleteAppDataCheckboxState = 1
  ${AndIfNot} ${Silent}
    MessageBox MB_OKCANCEL|MB_ICONINFORMATION "This removes everything inside DinoTraining: its datasets, annotations and trained models. Exported annotations and models stay where you saved them. To keep the rest, choose Cancel and export it first (Models & Datasets: Export everything now).$\r$\n$\r$\nDamit wird alles entfernt, was in DinoTraining liegt: Datensätze, Annotationen und trainierte Modelle. Exportierte Annotationen und Modelle bleiben, wo du sie gespeichert hast. Um den Rest zu behalten, wähle Abbrechen und exportiere zuerst (Modelle & Datensätze: Jetzt alles exportieren)." /SD IDOK IDOK dino_uninstall_confirmed
    Abort
    dino_uninstall_confirmed:
  ${EndIf}
!macroend
