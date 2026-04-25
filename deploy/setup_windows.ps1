<#
.SYNOPSIS
    One-time setup for Tech Alert Agent on Windows with LM Studio.
.DESCRIPTION
    Creates a Python virtual environment, installs all dependencies, and
    installs the Playwright Chromium browser needed for Twitter/Nitter scraping.
    Run this once from the project root before using the bot.
.EXAMPLE
    cd C:\Users\You\tech-alert-agent
    PowerShell -ExecutionPolicy Bypass -File deploy\setup_windows.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Tech Alert Agent — Windows Setup      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Resolve project root (this script lives in deploy\, so go one level up)
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "Project root: $ProjectRoot"
Set-Location $ProjectRoot

# ── Python check ──────────────────────────────────────────────────────────
try {
    $pyVer = python --version 2>&1
    Write-Host "Python found: $pyVer" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "ERROR: Python not found on PATH." -ForegroundColor Red
    Write-Host "Download Python 3.11+ from https://python.org" -ForegroundColor Yellow
    Write-Host "Make sure 'Add Python to PATH' is checked during install." -ForegroundColor Yellow
    exit 1
}

# ── Virtual environment ────────────────────────────────────────────────────
$VenvPath   = Join-Path $ProjectRoot "venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip    = Join-Path $VenvPath "Scripts\pip.exe"

if (Test-Path $VenvPython) {
    Write-Host "Virtual environment already exists — skipping creation." -ForegroundColor DarkGray
} else {
    Write-Host "Creating virtual environment..."
    python -m venv $VenvPath
    if (-not (Test-Path $VenvPython)) {
        Write-Host "ERROR: venv creation failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Created: $VenvPath" -ForegroundColor Green
}

# ── Python dependencies ────────────────────────────────────────────────────
Write-Host "Installing Python dependencies (this may take a minute)..."
& $VenvPip install --upgrade pip --quiet
& $VenvPip install -r (Join-Path $ProjectRoot "requirements.txt")
Write-Host "  Dependencies installed." -ForegroundColor Green

# ── Playwright Chromium ────────────────────────────────────────────────────
Write-Host "Installing Playwright Chromium browser..."
& $VenvPython -m playwright install chromium
Write-Host "  Playwright Chromium ready." -ForegroundColor Green

# ── .env file ─────────────────────────────────────────────────────────────
$EnvFile    = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"
if (Test-Path $EnvFile) {
    Write-Host ".env already exists — not overwritten." -ForegroundColor DarkGray
} else {
    Copy-Item $EnvExample $EnvFile
    Write-Host ""
    Write-Host "  >>> .env created from .env.example" -ForegroundColor Yellow
    Write-Host "  >>> Edit it now with your Telegram credentials:" -ForegroundColor Yellow
    Write-Host "      notepad `"$EnvFile`"" -ForegroundColor White
}

# ── logs directory ─────────────────────────────────────────────────────────
$LogsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
    Write-Host "Created logs\ directory." -ForegroundColor Green
}

# ── Summary ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup complete!                       " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open LM Studio, download 'Phi-3.5-mini-instruct (Q4_K_M)',"
Write-Host "     load the model, and click 'Start Server' (port 1234)."
Write-Host ""
Write-Host "  2. Fill in your Telegram credentials in .env:"
Write-Host "       notepad `"$EnvFile`""
Write-Host ""
Write-Host "  3. Run a quick smoke test:"
Write-Host "       `"$VenvPython`" main.py --mode alert"
Write-Host ""
Write-Host "  4. Register scheduled tasks (run as Administrator):"
Write-Host "       PowerShell -ExecutionPolicy Bypass -File deploy\schedule_windows.ps1"
Write-Host ""
