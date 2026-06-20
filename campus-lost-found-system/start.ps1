$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
$port = 5000
$url = "http://127.0.0.1:$port"
$outLog = Join-Path $PSScriptRoot "backend.log"
$errLog = Join-Path $PSScriptRoot "backend.err.log"

function Test-FlaskPort {
    $result = cmd /c "netstat -ano | findstr "":$port"" | findstr ""LISTENING"""
    return -not [string]::IsNullOrWhiteSpace($result)
}

function Show-StartupError {
    Write-Host "Flask service failed to start. Recent backend.err.log:" -ForegroundColor Red
    if (Test-Path $errLog) {
        Get-Content -Path $errLog -Tail 80
    } else {
        Write-Host "backend.err.log was not created."
    }
}

if (Test-FlaskPort) {
    Write-Host "Port $port is already LISTENING. Opening $url ..."
    cmd /c start "" "$url"
    exit 0
}

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $pythonFile = $pythonCommand.Source
    $pythonArgs = @("-3", "app.py")
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        Write-Host "Python was not found. Please install Python or add it to PATH." -ForegroundColor Red
        exit 1
    }
    $pythonFile = $pythonCommand.Source
    $pythonArgs = @("app.py")
}

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting Flask on port $port with $pythonFile $($pythonArgs -join ' ')" | Out-File -FilePath $outLog -Encoding utf8
"" | Out-File -FilePath $errLog -Encoding utf8

Start-Process `
    -FilePath $pythonFile `
    -ArgumentList $pythonArgs `
    -WorkingDirectory $PSScriptRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog

Start-Sleep -Seconds 3

if (Test-FlaskPort) {
    Write-Host "Flask service started successfully. Opening $url ..."
    cmd /c start "" "$url"
    exit 0
}

Show-StartupError
exit 1
