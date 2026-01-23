# Windows PowerShell script to check backend status

Write-Host "Checking FlashDash Backend Status..." -ForegroundColor Cyan
Write-Host ""

# Check if port 8000 is in use
$portCheck = Test-NetConnection -ComputerName localhost -Port 8000 -WarningAction SilentlyContinue
if ($portCheck.TcpTestSucceeded) {
    Write-Host "✓ Port 8000 is in use" -ForegroundColor Green
} else {
    Write-Host "✗ Port 8000 is not in use - backend not running" -ForegroundColor Red
    Write-Host "  Start with: .\start-backend.ps1" -ForegroundColor Yellow
    exit 1
}

# Test health endpoint
Write-Host ""
Write-Host "Testing health endpoint..." -ForegroundColor Cyan
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
    if ($healthResponse.StatusCode -eq 200) {
        Write-Host "✓ Health endpoint OK (HTTP 200)" -ForegroundColor Green
        Write-Host "  Response: $($healthResponse.Content)" -ForegroundColor Gray
    } else {
        Write-Host "✗ Health endpoint failed (HTTP $($healthResponse.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Health endpoint failed: $_" -ForegroundColor Red
    exit 1
}

# Test devices endpoint
Write-Host ""
Write-Host "Testing devices endpoint..." -ForegroundColor Cyan
try {
    $devicesResponse = Invoke-WebRequest -Uri "http://localhost:8000/devices" -UseBasicParsing -ErrorAction Stop
    if ($devicesResponse.StatusCode -eq 200) {
        Write-Host "✓ Devices endpoint OK (HTTP 200)" -ForegroundColor Green
        $deviceCount = ($devicesResponse.Content | ConvertFrom-Json).Count
        Write-Host "  Found $deviceCount device(s)" -ForegroundColor Gray
    } else {
        Write-Host "✗ Devices endpoint failed (HTTP $($devicesResponse.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Devices endpoint failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Backend is running correctly!" -ForegroundColor Green
