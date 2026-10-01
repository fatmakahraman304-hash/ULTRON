param([ValidateSet('install','start','doctor')][string]$Mode = 'start', [switch]$Smoke, [switch]$Quick)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONUTF8 = '1'
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
    if ($Mode -eq 'install') { & $pythonExe -m integration.installer }
    elseif ($Mode -eq 'doctor') {
        if ($Quick) { & $pythonExe -m integration.doctor --quick }
        else { & $pythonExe -m integration.doctor }
    }
    else {
        if ($Smoke) { & $pythonExe main.py --smoke }
        else { & $pythonExe main.py }
    }
    exit $LASTEXITCODE
} catch {
    Write-Host "HATA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
