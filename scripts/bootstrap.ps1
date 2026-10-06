param([ValidateSet('install','start','doctor')][string]$Mode = 'start', [switch]$Smoke, [switch]$Quick)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONUTF8 = '1'
# Rehydrate persistent per-user Cloud settings into this process when a shell was
# opened before those variables were saved. This keeps START.bat reliable.
foreach ($cloudName in @('ULTRON_CLOUD_URL','ULTRON_DEVICE_TOKEN','ULTRON_CLOUD_DEVICE_ID')) {
    if (-not (Get-Item -Path ("Env:" + $cloudName) -ErrorAction SilentlyContinue)) {
        $userValue = [Environment]::GetEnvironmentVariable($cloudName, 'User')
        if ($userValue) { Set-Item -Path ("Env:" + $cloudName) -Value $userValue }
    }
}
$backendPath = Join-Path $projectRoot 'ultron\backend'
if ($env:PYTHONPATH) { $env:PYTHONPATH = $backendPath + ';' + $env:PYTHONPATH }
else { $env:PYTHONPATH = $backendPath }
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $projectRoot 'cache\playwright'
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
try {
    if ($Mode -eq 'install' -and -not (Test-Path -LiteralPath $pythonExe)) {
        $candidates = @()
        if ($env:MARK_PYTHON) { $candidates += $env:MARK_PYTHON }
        $candidates += (Join-Path $projectRoot 'runtime\python\python.exe')
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { $candidates += $cmd.Source }
        $candidates += @(Get-ChildItem -Path "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object FullName)
        $candidates += @(Get-ChildItem -Path "$env:ProgramFiles\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object FullName)
        # The desktop's bundled CPython is also a valid local interpreter, when present.
        $candidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
        $basePython = $null
        foreach ($candidate in $candidates) {
            if (-not (Test-Path -LiteralPath $candidate)) { continue }
            & $candidate -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,12) else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { $basePython = $candidate; break }
        }
        if (-not $basePython) {
            New-Item -ItemType Directory -Force (Join-Path $projectRoot 'cache') | Out-Null
            $installer = Join-Path $projectRoot 'cache\python-3.12.10-amd64.exe'
            Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer -TimeoutSec 180
            $signature = Get-AuthenticodeSignature -LiteralPath $installer
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw 'Python installer signature validation failed.' }
            $target = Join-Path $projectRoot 'runtime\python'
            $installProcess = Start-Process -FilePath $installer -ArgumentList @('/quiet','InstallAllUsers=0',"TargetDir=`"$target`"",'Include_launcher=0','PrependPath=0','AssociateFiles=0','Shortcuts=0','Include_test=0','Include_pip=1') -WindowStyle Hidden -Wait -PassThru
            if ($installProcess.ExitCode -ne 0) { throw "Python setup failed: $($installProcess.ExitCode)" }
            $basePython = Join-Path $target 'python.exe'
        }
        & $basePython -m venv (Join-Path $projectRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Venv olusturulamadi.' }
    }
    if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Python ortami yok. Once INSTALL.bat calistirin.' }
    $env:PATH = (Split-Path -Parent $pythonExe) + ';' + $env:PATH
    & $pythonExe --version
    if ($LASTEXITCODE -ne 0) { throw 'Python calismiyor.' }

    # The native cockpit loads ultron/frontend/dist, not the TypeScript source.
    # Rebuild automatically only when source/config is newer than the existing
    # bundle so git pull + START.bat is enough to activate UI upgrades.
    if ($Mode -eq 'start' -or $Mode -eq 'install') {
        $frontendDir = Join-Path $projectRoot 'ultron\frontend'
        $distIndex = Join-Path $frontendDir 'dist\index.html'
        $needsFrontendBuild = -not (Test-Path -LiteralPath $distIndex)
        if (-not $needsFrontendBuild) {
            $distTime = (Get-Item -LiteralPath $distIndex).LastWriteTimeUtc
            $frontendInputs = @(
                (Join-Path $frontendDir 'src'),
                (Join-Path $frontendDir 'index.html'),
                (Join-Path $frontendDir 'package.json'),
                (Join-Path $frontendDir 'package-lock.json'),
                (Join-Path $frontendDir 'vite.config.ts'),
                (Join-Path $frontendDir 'tsconfig.json')
            )
            foreach ($inputPath in $frontendInputs) {
                if (-not (Test-Path -LiteralPath $inputPath)) { continue }
                $item = Get-Item -LiteralPath $inputPath
                if ($item.PSIsContainer) {
                    $newer = Get-ChildItem -LiteralPath $inputPath -Recurse -File -ErrorAction SilentlyContinue |
                        Where-Object { $_.LastWriteTimeUtc -gt $distTime } |
                        Select-Object -First 1
                    if ($newer) { $needsFrontendBuild = $true; break }
                } elseif ($item.LastWriteTimeUtc -gt $distTime) {
                    $needsFrontendBuild = $true; break
                }
            }
        }
        if ($needsFrontendBuild) {
            $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
            if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
            if (-not $npm) { throw 'Frontend guncellendi ancak npm bulunamadi. Node.js/npm kurulumu gerekli.' }
            Write-Host 'ULTRON Center Stage arayuzu derleniyor...' -ForegroundColor Cyan
            Push-Location -LiteralPath $frontendDir
            try {
                if (-not (Test-Path -LiteralPath (Join-Path $frontendDir 'node_modules'))) {
                    & $npm.Source ci
                    if ($LASTEXITCODE -ne 0) { throw "Frontend npm ci basarisiz: $LASTEXITCODE" }
                }
                & $npm.Source run build
                if ($LASTEXITCODE -ne 0) { throw "Frontend build basarisiz: $LASTEXITCODE" }
            } finally {
                Pop-Location
            }
        }
    }
    if ($Mode -eq 'install') { & $pythonExe -m integration.installer }
    elseif ($Mode -eq 'doctor') {
        if ($Quick) { & $pythonExe -m integration.doctor --quick }
        else { & $pythonExe -m integration.doctor }
    }
    else {
        # Voice/Gemini Live builds its prompt from local memory. Pull the shared
        # Cloud memories into that store before launching so phone, typed desktop
        # and spoken desktop all know the same persistent facts. Best-effort only:
        # the sync module always exits 0 when Cloud is unavailable.
        & $pythonExe -m integration.cloud_memory_sync
        if ($Smoke) { & $pythonExe main.py --smoke }
        else { & $pythonExe main.py }
    }
    exit $LASTEXITCODE
} catch {
    Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
