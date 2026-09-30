<#
Build the CUDA 12.8 image and optionally export the files people install.

  powershell -ExecutionPolicy Bypass -File docker\build.ps1
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "C:\path\to\folder"
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -ModelImage trascrittore:latest

HF_TOKEN is read from .env and passed to BuildKit as a secret.
#>
param(
    [string]$ModelImage = '',
    [string]$Export = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot '.env'
$tokenLine = Get-Content -LiteralPath $envFile -ErrorAction SilentlyContinue |
    Where-Object { $_ -match '^\s*HF_TOKEN\s*=' } | Select-Object -First 1
if (-not $tokenLine) { throw "HF_TOKEN not found in $envFile." }
$env:HF_TOKEN = ($tokenLine -replace '^\s*HF_TOKEN\s*=\s*', '').Trim().Trim('"').Trim("'")
if (-not $env:HF_TOKEN) { throw "HF_TOKEN in $envFile is empty." }

try {
    $tag = 'trascrittore:cu128'
    $modelStage = if ($ModelImage) { 'copied' } else { 'downloaded' }
    if ($ModelImage) {
        & docker image inspect $ModelImage *> $null
        if ($LASTEXITCODE -ne 0) { throw "Model source $ModelImage is missing." }
    }
    Write-Host "Building $tag..."
    & docker build --build-arg "MODEL_STAGE=$modelStage" --build-arg "MODEL_IMAGE=$(if ($ModelImage) { $ModelImage } else { 'trascrittore:latest' })" `
        --secret id=hf_token,env=HF_TOKEN -t $tag $repoRoot
    if ($LASTEXITCODE -ne 0) { throw "docker build failed for $tag." }

    if ($Export) {
        New-Item -ItemType Directory -Force -Path $Export | Out-Null
        $tarPath = Join-Path $Export 'trascrittore-cu128.tar'
        $temporaryTar = "$tarPath.partial"
        try {
            & docker save -o $temporaryTar $tag
            if ($LASTEXITCODE -ne 0) { throw "docker save failed for $tag." }
            Move-Item -LiteralPath $temporaryTar -Destination $tarPath -Force
        }
        finally {
            if (Test-Path -LiteralPath $temporaryTar) { Remove-Item -LiteralPath $temporaryTar -Force }
        }
        $sizeGb = [math]::Round((Get-Item -LiteralPath $tarPath).Length / 1GB, 2)
        Write-Host "Exported trascrittore-cu128.tar ($sizeGb GB)."

        # Remove obsolete release files when updating an existing folder.
        foreach ($name in @('trascrittore-cu126.tar', 'trascrittore.tar', 'installa.ps1')) {
            $obsolete = Join-Path $Export $name
            if (Test-Path -LiteralPath $obsolete -PathType Leaf) { Remove-Item -LiteralPath $obsolete -Force }
        }
        New-Item -ItemType Directory -Force -Path (Join-Path $Export 'voci') | Out-Null
        foreach ($name in @('Trascrivi.bat', 'Verifica.bat', 'Installa.bat', 'trascrittore.ps1',
                            'skill-trascrittore.md', 'LEGGIMI.md', 'LICENZE.md')) {
            Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $Export -Force
        }
        Write-Host "Cartella pronta: $Export"
    }
}
finally {
    Remove-Item Env:HF_TOKEN -ErrorAction SilentlyContinue
}
