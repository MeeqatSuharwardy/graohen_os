# Build FlashDash for Windows (PowerShell Script)
# Usage: .\build-windows.ps1 [-Sign]

param(
    [switch]$Sign
)

$ErrorActionPreference = "Stop"

Write-Host "🔨 Building FlashDash for Windows..." -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Check if signing is requested
if ($Sign) {
    if (-not $env:CSC_LINK) {
        Write-Host "❌ Error: -Sign flag used but CSC_LINK not set" -ForegroundColor Red
        Write-Host ""
        Write-Host "Set certificate path:"
        Write-Host "  `$env:CSC_LINK = 'C:\path\to\certificate.pfx'"
        Write-Host "  `$env:CSC_KEY_PASSWORD = 'your-password'"
        exit 1
    }
    
    if (-not (Test-Path $env:CSC_LINK)) {
        Write-Host "❌ Error: Certificate file not found: $env:CSC_LINK" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🔐 Code signing enabled" -ForegroundColor Green
    Write-Host "   Certificate: $env:CSC_LINK"
} else {
    if (-not $env:CSC_LINK) {
        Write-Host "⚠️  Warning: No code signing certificate set (CSC_LINK)" -ForegroundColor Yellow
        Write-Host "   Building unsigned executable (SmartScreen warning will appear)"
        Write-Host ""
        Write-Host "To sign the executable, set:"
        Write-Host "  `$env:CSC_LINK = 'C:\path\to\certificate.pfx'"
        Write-Host "  `$env:CSC_KEY_PASSWORD = 'your-password'"
        Write-Host "  .\build-windows.ps1 -Sign"
        Write-Host ""
    } else {
        Write-Host "🔐 Code signing certificate found, will sign automatically" -ForegroundColor Green
    }
}

Set-Location "frontend\electron"

# Install dependencies if needed
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
    npm install
}

# Build for Windows
Write-Host ""
Write-Host "🏗️  Building Windows EXE..." -ForegroundColor Cyan
Write-Host ""

try {
    npm run build:win
    
    Write-Host ""
    Write-Host "✅ Build complete!" -ForegroundColor Green
    Write-Host ""
    
    # Find the output file
    $outputDir = "..\build"
    if (Test-Path $outputDir) {
        $exeFile = Get-ChildItem -Path $outputDir -Filter "FlashDash Setup *.exe" | Select-Object -First 1
        
        if ($exeFile) {
            Write-Host "📦 Output: $($exeFile.FullName)" -ForegroundColor Cyan
            
            # Check if signed
            if ($env:CSC_LINK -and (Get-Command signtool -ErrorAction SilentlyContinue)) {
                Write-Host ""
                Write-Host "🔍 Verifying signature..." -ForegroundColor Cyan
                try {
                    $verify = & signtool verify /pa $exeFile.FullName 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "✓ Executable is signed" -ForegroundColor Green
                    } else {
                        Write-Host "⚠️  Executable signature verification failed (may be normal for self-signed)" -ForegroundColor Yellow
                    }
                } catch {
                    Write-Host "⚠️  Could not verify signature" -ForegroundColor Yellow
                }
            }
        }
    }
    
    Write-Host ""
    Write-Host "📋 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Test the installer on a Windows machine"
    Write-Host "   2. Check SmartScreen behavior"
    Write-Host "   3. Distribute through trusted channels (GitHub, website)"
} catch {
    Write-Host ""
    Write-Host "❌ Build failed!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
