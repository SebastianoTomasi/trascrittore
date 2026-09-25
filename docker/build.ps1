<#
Build the transcriber image, and optionally export the files the people who use it download.

  powershell -ExecutionPolicy Bypass -File docker\build.ps1
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "C:\path\to\export\folder"

The Hugging Face token is read from .env and handed to BuildKit as a secret,
so it never lands in an image layer, the build history or this console.
#>
param(
    [string]$Tag = "trascrittore:latest",
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
# A container still using it, such as a transcription in progress, blocks the removal.
$currentId = docker images -q --no-trunc $Tag
$previousStillThere = $previousId -and ((docker images -a -q --no-trunc) -contains $previousId)
if ($previousStillThere -and $previousId -ne $currentId) {
    if (docker ps -a -q --filter "ancestor=$previousId") {
        Write-Warning "The previous image is still used by a container. When it ends, remove it with: docker rmi $previousId"
    }
    else {
        docker rmi $previousId | Out-Null
    }
}

if ($Export) {
    # Lay out what the people who use the transcriber download: image, scripts, guide, model licenses,
    # agent skill and an empty voice library. The skill ships only here, next to the image it describes.
    # No settings file: Installa.bat creates trascrittore.ini once, and no update replaces it.
    New-Item -ItemType Directory -Force (Join-Path $Export "voci") | Out-Null
    $tarPath = Join-Path $Export "trascrittore.tar"
    docker save -o $tarPath $Tag
    if ($LASTEXITCODE -ne 0) { throw "docker save failed." }
    foreach ($name in "Trascrivi.bat", "Verifica.bat", "Installa.bat", "trascrittore.ps1", "skill-trascrittore.md", "LEGGIMI.md", "LICENZE.md") {
        Copy-Item (Join-Path $PSScriptRoot $name) $Export -Force
    }
    $sizeGb = [math]::Round((Get-Item $tarPath).Length / 1GB, 2)
    Write-Host "Export folder ready in $Export (image $sizeGb GB)."
}
