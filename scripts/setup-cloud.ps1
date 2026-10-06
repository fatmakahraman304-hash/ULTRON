param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$url = 'https://ultron-yubh.onrender.com'

Write-Host 'ULTRON Cloud kurulumu' -ForegroundColor Cyan
Write-Host 'Render ortamindaki ULTRON_DEVICE_TOKEN degerini girin. Yazarken ekranda gorunmez.'
$secure = Read-Host 'ULTRON_DEVICE_TOKEN' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ([string]::IsNullOrWhiteSpace($token)) { throw 'Token bos olamaz.' }

    [Environment]::SetEnvironmentVariable('ULTRON_CLOUD_URL', $url, 'User')
    [Environment]::SetEnvironmentVariable('ULTRON_DEVICE_TOKEN', $token, 'User')
    [Environment]::SetEnvironmentVariable('ULTRON_CLOUD_DEVICE_ID', 'desktop-ultron', 'User')

    $env:ULTRON_CLOUD_URL = $url
    $env:ULTRON_DEVICE_TOKEN = $token
    $env:ULTRON_CLOUD_DEVICE_ID = 'desktop-ultron'

    $python = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Python ortami bulunamadi. Once INSTALL.bat calistirin.' }

    & $python -m integration.cloud_memory_sync
    if ($LASTEXITCODE -ne 0) { throw 'Cloud dogrulamasi basarisiz oldu.' }

    Write-Host 'ULTRON Cloud ayarlari kalici olarak kaydedildi.' -ForegroundColor Green
    Write-Host 'Artik START.bat normal sekilde kullanilabilir.' -ForegroundColor Green
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}
