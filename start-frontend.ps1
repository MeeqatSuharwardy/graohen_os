# Windows PowerShell script to start frontend

Write-Host "Starting FlashDash Frontend..." -ForegroundColor Green

# Check if .env exists
if (-Not (Test-Path "frontend\packages\desktop\.env")) {
    Write-Host "Creating frontend .env file..." -ForegroundColor Yellow
    New-Item -Path "frontend\packages\desktop\.env" -ItemType File -Force | Out-Null
    Add-Content -Path "frontend\packages\desktop\.env" -Value "VITE_API_BASE_URL=http://localhost:8000"
}

# Check if dependencies are installed
if (-Not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location frontend
    pnpm install
    Set-Location ..
}

# Start Electron app
Write-Host "Starting Electron app..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

pnpm run dev
