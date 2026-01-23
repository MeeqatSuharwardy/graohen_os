# Windows PowerShell script to start backend

Write-Host "Starting FlashDash Backend..." -ForegroundColor Green

# Navigate to backend directory
Set-Location backend\py-service

# Check if virtual environment exists
if (-Not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Check if activation succeeded
if ($LASTEXITCODE -ne 0) {
    Write-Host "Activation failed. Trying to set execution policy..." -ForegroundColor Yellow
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    & .\venv\Scripts\Activate.ps1
}

# Install/upgrade dependencies if needed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "Creating .env file from env.example..." -ForegroundColor Yellow
    Copy-Item env.example .env
}

# Start backend server
Write-Host "Starting backend server on http://127.0.0.1:8000..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
