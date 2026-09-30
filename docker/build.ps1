<#
Build one or both pinned CUDA images, optionally exporting their separate TARs.

  powershell -ExecutionPolicy Bypass -File docker\build.ps1
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Variant both -Export "C:\path\to\folder"
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Variant both -ModelImage trascrittore:latest

HF_TOKEN is read from .env and passed to BuildKit as a secret.
#>
param(
    [ValidateSet('cu126', 'cu128', 'both')]
    [string]$Variant = 'cu128',
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

$variants = if ($Variant -eq 'both') { @('cu128', 'cu126') } else { @($Variant) }
try {
    if ($Export) { New-Item -ItemType Directory -Force -Path $Export | Out-Null }
    foreach ($cuda in $variants) {
        $tag = "trascrittore:$cuda"
        $sourceImage = if ($cuda -eq 'cu126') { 'trascrittore:cu128' } elseif ($ModelImage) { $ModelImage } else { 'trascrittore:cu128' }
        $modelStage = if ($cuda -eq 'cu126' -or $ModelImage) { 'copied' } else { 'downloaded' }
        if ($modelStage -eq 'copied') {
            & docker image inspect $sourceImage *> $null
            if ($LASTEXITCODE -ne 0) { throw "Model source $sourceImage is missing. Build cu128 first." }
        }
        Write-Host "Building $tag..."
        & docker build --build-arg "CUDA_VARIANT=$cuda" --build-arg "MODEL_STAGE=$modelStage" `
            --build-arg "MODEL_IMAGE=$sourceImage" --secret id=hf_token,env=HF_TOKEN -t $tag $repoRoot
        if ($LASTEXITCODE -ne 0) { throw "docker build failed for $cuda." }
        if ($Export) {
            $tarPath = Join-Path $Export "trascrittore-$cuda.tar"
            $temporaryTar = "$tarPath.partial"
            try {
                & docker save -o $temporaryTar $tag
                if ($LASTEXITCODE -ne 0) { throw "docker save failed for $cuda." }
                Move-Item -LiteralPath $temporaryTar -Destination $tarPath -Force
            }
            finally {
                if (Test-Path -LiteralPath $temporaryTar) { Remove-Item -LiteralPath $temporaryTar -Force }
            }
            $sizeGb = [math]::Round((Get-Item -LiteralPath $tarPath).Length / 1GB, 2)
            Write-Host "Exported trascrittore-$cuda.tar ($sizeGb GB)."
        }
    }
    if ($Export) {
        # A previous single-image release must not be mistaken for a current archive.
        $oldArchive = Join-Path $Export 'trascrittore.tar'
        if (Test-Path -LiteralPath $oldArchive) { Remove-Item -LiteralPath $oldArchive -Force }
        $oldInstallerHelper = Join-Path $Export 'installa.ps1'
        if (Test-Path -LiteralPath $oldInstallerHelper -PathType Leaf) {
            Remove-Item -LiteralPath $oldInstallerHelper -Force
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
