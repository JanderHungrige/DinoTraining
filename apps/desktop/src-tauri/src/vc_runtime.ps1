# Doc 141: install Microsoft's Visual C++ runtime, which PyTorch's Windows wheels need
# (msvcp140.dll 14.40 or newer) but do not ship.
#
# Exit codes, read by vc_runtime.rs:
#   0, 3010, 1638  installed (3010: a restart is suggested; 1638: a newer one was there)
#   1223           the user declined Windows' permission prompt
#   90             the download is not signed by Microsoft; it was not run
#   91             the download failed
#   other          the installer's own error code
param([string]$Url = 'https://aka.ms/vs/17/release/vc_redist.x64.exe')

$ErrorActionPreference = 'Stop'
# Windows PowerShell 5.1 redraws its progress bar per chunk and slows downloads tenfold.
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$file = Join-Path $env:TEMP 'dinotraining-vc_redist.x64.exe'
try {
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $file
} catch {
    Write-Output "download failed: $($_.Exception.Message)"
    exit 91
}

$signature = Get-AuthenticodeSignature -FilePath $file
$subject = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { '' }
if ($signature.Status -ne 'Valid' -or $subject -notmatch 'O=Microsoft Corporation') {
    Write-Output "signature refused: $($signature.Status) $subject"
    Remove-Item -Force $file -ErrorAction SilentlyContinue
    exit 90
}

try {
    $process = Start-Process -FilePath $file -ArgumentList '/install', '/passive', '/norestart' `
        -Verb RunAs -Wait -PassThru
} catch {
    # Start-Process throws when the permission prompt is declined.
    Write-Output "not started: $($_.Exception.Message)"
    exit 1223
}
Remove-Item -Force $file -ErrorAction SilentlyContinue
Write-Output "installer exit code: $($process.ExitCode)"
exit $process.ExitCode
