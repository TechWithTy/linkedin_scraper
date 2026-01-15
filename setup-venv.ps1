# Setup script for LinkedIn scraper virtual environment using uv (Windows)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "[*] Setting up LinkedIn scraper virtual environment..." -ForegroundColor Cyan

# Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[X] Error: uv is not installed" -ForegroundColor Red
    Write-Host "[!] Please install uv first: powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor Yellow
    exit 1
}

# Create virtual environment
Write-Host "[*] Creating virtual environment..." -ForegroundColor Cyan
uv venv .venv

# Activate virtual environment
Write-Host "[*] Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "[*] Installing dependencies..." -ForegroundColor Cyan
uv pip install -e .

# Install Playwright browsers
Write-Host "[*] Installing Playwright browsers..." -ForegroundColor Cyan
python -m playwright install chromium

Write-Host "[OK] LinkedIn scraper setup complete!" -ForegroundColor Green
Write-Host "[*] To activate the virtual environment, run:" -ForegroundColor Cyan
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow


