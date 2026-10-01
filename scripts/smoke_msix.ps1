# Doc 153: the Store edition installed and started the way a user starts it.
#
#   pwsh scripts/smoke_msix.ps1 -Msix <test-signed .msix> -Cert <.cer>
#
# Trusts the test certificate, installs the package, starts it through its package
# identity (shell:AppsFolder, so it inherits no standard handles and no environment: the
# gap doc 139 found), lets the first-run setup install the CPU variant unattended, checks
# /health and PyTorch in the redirected runtime, starts it a second time without setup,
# then removes the package and checks that Windows removed its redirected data with it.
param(
    [Parameter(Mandatory = $true)] [string] $Msix,
    [Parameter(Mandatory = $true)] [string] $Cert,
    [int] $FirstStartSeconds = 1500,
    [int] $SecondStartSeconds = 180
)
$ErrorActionPreference = 'Stop'
$Health = 'http://127.0.0.1:8756/api/v1/health'

function Wait-Healthy([int] $Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    $started = Get-Date
    while ((Get-Date) -lt $deadline) {
        try {
            $answer = Invoke-RestMethod -Uri $Health -TimeoutSec 5
            return [math]::Round(((Get-Date) - $started).TotalSeconds), $answer
        } catch { Start-Sleep -Seconds 5 }
    }
    throw "/health did not answer within $Seconds s"
}

function Stop-App {
    Get-Process | Where-Object { $_.Name -in @('DinoTraining', 'python', 'uv') } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 5
}

Import-Certificate -FilePath $Cert -CertStoreLocation Cert:\LocalMachine\TrustedPeople | Out-Null
Add-AppxPackage -Path $Msix
$package = Get-AppxPackage | Where-Object { $_.Name -like 'DinoTraining*' -or $_.Name -like '*DinoTraining*' } | Select-Object -First 1
if (-not $package) { throw 'the package is not installed' }
$family = $package.PackageFamilyName
Write-Host "Installed $($package.PackageFullName) at $($package.InstallLocation)"

# The unattended variant through a file: a packaged start inherits no environment.
# Written outside the package; the app's redirected AppData reads through to it.
$support = Join-Path $env:LOCALAPPDATA 'DinoTraining'
New-Item -ItemType Directory -Force -Path $support | Out-Null
Set-Content -Path (Join-Path $support 'setup-auto') -Value 'cpu' -NoNewline

Start-Process "shell:AppsFolder\$family!DinoTraining"
$first, $answer = Wait-Healthy $FirstStartSeconds
Write-Host "First start healthy after $first s: $($answer | ConvertTo-Json -Compress)"

# Where Windows really put the runtime (doc 152): the package's redirected LocalAppData.
$redirected = Join-Path $env:LOCALAPPDATA "Packages\$family\LocalCache\Local\DinoTraining"
$python = Get-ChildItem (Join-Path $redirected 'runtime\envs') -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\Scripts\\python\.exe$' } | Select-Object -First 1
if ($python) {
    & $python.FullName -c "import torch; print('torch', torch.__version__)"
    if ($LASTEXITCODE -ne 0) { throw 'PyTorch does not import in the redirected runtime' }
    $where = "redirected: $redirected"
} else {
    $plain = Join-Path $support 'runtime'
    Write-Host "No runtime under $redirected; the real folder holds: $(Test-Path $plain)"
    $where = "not redirected: $plain"
}

Stop-App
Start-Process "shell:AppsFolder\$family!DinoTraining"
$second, $_ = Wait-Healthy $SecondStartSeconds
Write-Host "Second start healthy after $second s"
Stop-App

Remove-AppxPackage -Package $package.PackageFullName
Start-Sleep -Seconds 5
$left = Test-Path (Join-Path $env:LOCALAPPDATA "Packages\$family")
Remove-Item (Join-Path $support 'setup-auto') -ErrorAction SilentlyContinue

@(
    "### MSIX smoke test (doc 153)",
    "- first start (setup, unattended): $first s; second start: $second s",
    "- runtime $where",
    "- after removing the package, its data folder is $(if ($left) { 'still there' } else { 'gone' })"
) | Add-Content -Path $env:GITHUB_STEP_SUMMARY -ErrorAction SilentlyContinue
if ($left) { throw "Windows left the package's data folder after removal" }
Write-Host 'MSIX smoke test passed'
