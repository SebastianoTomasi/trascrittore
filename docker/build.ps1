<#
Build the CUDA 12.8 image and optionally export the files people install.

  powershell -ExecutionPolicy Bypass -File docker\build.ps1
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -Export "C:\path\to\folder"
  powershell -ExecutionPolicy Bypass -File docker\build.ps1 -ModelImage trascrittore:latest

Dependencies and models go into an image of their own, trascrittore-base:<key>. The key
changes only with Dockerfile, pyproject.toml, uv.lock or docker/prefetch_models.py, so a
code change reuses that image even after BuildKit has cleaned up its cache.
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
    # Line endings are normalized so a checkout that rewrites them keeps the key.
    $baseText = (@('Dockerfile', 'pyproject.toml', 'uv.lock', 'docker\prefetch_models.py') | ForEach-Object {
        [System.IO.File]::ReadAllText((Join-Path $repoRoot $_)) -replace "`r`n", "`n"
    }) -join "`0"
    $baseHash = [System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($baseText))
    $baseTag = 'trascrittore-base:' + (-join ($baseHash[0..5] | ForEach-Object { $_.ToString('x2') }))

    # image ls stays silent for a missing image; Windows PowerShell stops on a redirected error message.
    if (& docker image ls -q $baseTag) {
        Write-Host "Reusing $baseTag."
    }
    else {
        $baseArguments = @('build', '-t', $baseTag)
        if ($ModelImage) {
            if (-not (& docker image ls -q $ModelImage)) { throw "Model source $ModelImage is missing." }
            $baseArguments += @('--target', 'copied', '--build-arg', "MODEL_IMAGE=$ModelImage")
        }
        else {
            $tokenLine = Get-Content -LiteralPath $envFile -ErrorAction SilentlyContinue |
                Where-Object { $_ -match '^\s*HF_TOKEN\s*=' } | Select-Object -First 1
            if (-not $tokenLine) { throw "HF_TOKEN not found in $envFile." }
            $env:HF_TOKEN = ($tokenLine -replace '^\s*HF_TOKEN\s*=\s*', '').Trim().Trim('"').Trim("'")
            if (-not $env:HF_TOKEN) { throw "HF_TOKEN in $envFile is empty." }
            $baseArguments += @('--target', 'downloaded', '--secret', 'id=hf_token,env=HF_TOKEN')
        }
        Write-Host "Building $baseTag (dependencies and models)..."
        & docker @baseArguments $repoRoot
        if ($LASTEXITCODE -ne 0) { throw "docker build failed for $baseTag." }
    }

    Write-Host "Building $tag..."
    & docker build --build-arg "BASE=$baseTag" -t $tag $repoRoot
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
        foreach ($name in @('Trascrivi.bat', 'Installa.bat', 'trascrittore.ps1',
                            'skill-trascrittore.md', 'skill-fix-transcript.md', 'LEGGIMI.md', 'LICENZE.md')) {
            Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $Export -Force
        }
        Write-Host "Cartella pronta: $Export"
    }
}
finally {
    $env:HF_TOKEN = $previousToken
}
