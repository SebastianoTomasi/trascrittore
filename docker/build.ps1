<#
Build the CUDA 12.8 image and optionally export the files people install.

  powershell -ExecutionPolicy Bypass -File docker\build.ps1
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "C:\path\to\folder"
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -ModelImage trascrittore:latest

Model downloads read HF_TOKEN from .env and pass it to BuildKit as a secret.
#>
param(
    [string]$ModelImage = '',
    [string]$Export = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot '.env'
$previousToken = $env:HF_TOKEN

try {
    $tag = 'trascrittore:cu128'
    $modelStage = if ($ModelImage) { 'copied' } else { 'downloaded' }
    $buildArguments = @('build', '--build-arg', "MODEL_STAGE=$modelStage", '-t', $tag)
    if ($ModelImage) {
        & docker image inspect $ModelImage *> $null
        if ($LASTEXITCODE -ne 0) { throw "Model source $ModelImage is missing." }
        $buildArguments += @('--build-arg', "MODEL_IMAGE=$ModelImage")
    }
    else {
        $tokenLine = Get-Content -LiteralPath $envFile -ErrorAction SilentlyContinue |
            Where-Object { $_ -match '^\s*HF_TOKEN\s*=' } | Select-Object -First 1
        if (-not $tokenLine) { throw "HF_TOKEN not found in $envFile." }
        $env:HF_TOKEN = ($tokenLine -replace '^\s*HF_TOKEN\s*=\s*', '').Trim().Trim('"').Trim("'")
        if (-not $env:HF_TOKEN) { throw "HF_TOKEN in $envFile is empty." }
        $buildArguments += @('--secret', 'id=hf_token,env=HF_TOKEN')
    }
    $buildArguments += $repoRoot
    Write-Host "Building $tag..."
    & docker @buildArguments
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

        New-Item -ItemType Directory -Force -Path (Join-Path $Export 'voci') | Out-Null
        foreach ($name in @('Trascrivi.bat', 'Verifica.bat', 'Installa.bat', 'trascrittore.ps1',
                            'skill-trascrittore.md', 'skill-fix-transcript.md', 'LEGGIMI.md', 'LICENZE.md')) {
            Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $Export -Force
        }
        Write-Host "Cartella pronta: $Export"
    }
}
finally {
    $env:HF_TOKEN = $previousToken
}
