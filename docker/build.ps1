<#
Build the meeting transcriber image, and optionally export it for colleagues.

  powershell -ExecutionPolicy Bypass -File docker\build.ps1
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "C:\path\to\shared\folder"

The Hugging Face token is read from .env and handed to BuildKit as a secret,
so it never lands in an image layer, the build history or this console.
#>
param(
    [string]$Tag = "meeting-transcriber:pilot",
    [string]$Export = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot ".env"

$tokenLine = Get-Content $envFile -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*HF_TOKEN\s*=' } | Select-Object -First 1
if (-not $tokenLine) {
    throw "HF_TOKEN not found in $envFile."
}
$env:HF_TOKEN = ($tokenLine -replace '^\s*HF_TOKEN\s*=\s*', '').Trim().Trim('"').Trim("'")
if (-not $env:HF_TOKEN) {
    throw "HF_TOKEN in $envFile is empty."
}

$previousId = docker images -q --no-trunc $Tag
try {
    docker build --secret id=hf_token,env=HF_TOKEN -t $Tag $repoRoot
    if ($LASTEXITCODE -ne 0) { throw "docker build failed." }
}
finally {
    Remove-Item Env:HF_TOKEN -ErrorAction SilentlyContinue
}

# The previous build can lose its tag but keep its own layers on disk until removed.
# Docker sometimes removes it by itself, so check it still exists before removing it.
$currentId = docker images -q --no-trunc $Tag
$previousStillThere = $previousId -and ((docker images -a -q --no-trunc) -contains $previousId)
if ($previousStillThere -and $previousId -ne $currentId) {
    docker rmi $previousId | Out-Null
}

if ($Export) {
    # Lay out the shared folder colleagues use: image, scripts, guide, settings and voice library.
    New-Item -ItemType Directory -Force (Join-Path $Export "voci") | Out-Null
    $tarPath = Join-Path $Export "meeting-transcriber.tar"
    docker save -o $tarPath $Tag
    if ($LASTEXITCODE -ne 0) { throw "docker save failed." }
    foreach ($name in "Trascrivi.bat", "Installa.bat", "LEGGIMI.md") {
        Copy-Item (Join-Path $PSScriptRoot $name) $Export -Force
    }
    # meeting.ini in the shared folder may hold tuned thresholds: never overwrite it.
    $sharedConfig = Join-Path $Export "meeting.ini"
    if (-not (Test-Path $sharedConfig)) {
        Copy-Item (Join-Path $PSScriptRoot "meeting.ini") $sharedConfig
    }
    $sizeGb = [math]::Round((Get-Item $tarPath).Length / 1GB, 2)
    Write-Host "Shared folder ready in $Export (image $sizeGb GB)."
}
