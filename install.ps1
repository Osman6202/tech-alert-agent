#Requires -Version 5.1
<#
.SYNOPSIS
    One-shot installer for Tech Alert Agent (Windows, no administrator required).

.DESCRIPTION
    1. Checks Python 3.11+
    2. Creates a virtual environment
    3. Installs Python dependencies
    4. Installs Playwright Chromium browser
    5. Creates .env from .env.example (if not present)
    6. Creates logs\ directory
    7. Adds a shortcut to the user's Startup folder so the app
       launches automatically on every Windows logon (no admin needed)

.EXAMPLE
    PowerShell -ExecutionPolicy Bypass -File install.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "=============================" -ForegroundColor Cyan
Write-Host "  Tech Alert Agent Installer" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Python version check ──────────────────────────────────────────
Write-Host "[1/7] Checking Python version..." -ForegroundColor Yellow
try {
    $verStr = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
    if ([version]$verStr -lt [version]"3.11") {
        Write-Error "Python 3.11 or newer is required. Found: $verStr"
        exit 1
    }
    Write-Host "      Python $verStr OK" -ForegroundColor Green
} catch {
    Write-Error "Python not found on PATH. Install from https://python.org"
    exit 1
}

# ── Step 2: Virtual environment ───────────────────────────────────────────
Write-Host "[2/7] Creating virtual environment..." -ForegroundColor Yellow
$VenvDir = Join-Path $ProjectRoot "venv"
if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
}
$Pip     = Join-Path $VenvDir "Scripts\pip.exe"
$Python  = Join-Path $VenvDir "Scripts\python.exe"
$Pythonw = Join-Path $VenvDir "Scripts\pythonw.exe"
Write-Host "      venv ready" -ForegroundColor Green

# ── Step 3: Install dependencies ──────────────────────────────────────────
Write-Host "[3/7] Installing Python dependencies..." -ForegroundColor Yellow
& $Pip install --upgrade pip --quiet
& $Pip install -r (Join-Path $ProjectRoot "requirements.txt") --quiet
& $Pip install sgmllib3k --quiet   # feedparser needs sgmllib on Python 3
Write-Host "      Dependencies installed" -ForegroundColor Green

# ── Step 4: Playwright Chromium ───────────────────────────────────────────
Write-Host "[4/7] Installing Playwright Chromium..." -ForegroundColor Yellow
& $Python -m playwright install chromium
Write-Host "      Chromium installed" -ForegroundColor Green

# ── Step 5: .env file ─────────────────────────────────────────────────────
Write-Host "[5/7] Setting up .env..." -ForegroundColor Yellow
$EnvFile    = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"
if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "      Created .env from template" -ForegroundColor Green
} else {
    Write-Host "      .env already exists — keeping it" -ForegroundColor Green
}

# ── Step 6: logs\ directory ───────────────────────────────────────────────
Write-Host "[6/7] Creating logs directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "logs") | Out-Null
Write-Host "      logs\ ready" -ForegroundColor Green

# ── Step 7: Startup shortcut ──────────────────────────────────────────────
Write-Host "[7/7] Adding to Windows Startup folder..." -ForegroundColor Yellow
$StartupDir   = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "TechAlertAgent.lnk"
$AppScript    = Join-Path $ProjectRoot "app.py"

$WS  = New-Object -ComObject WScript.Shell
$Lnk = $WS.CreateShortcut($ShortcutPath)
$Lnk.TargetPath       = $Pythonw
$Lnk.Arguments        = "`"$AppScript`""
$Lnk.WorkingDirectory = $ProjectRoot
$Lnk.Description      = "Tech Alert Agent"
$Lnk.Save()
Write-Host "      Startup shortcut created: $ShortcutPath" -ForegroundColor Green

# ── Done ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Installation complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Open LM Studio → load phi-3.5-mini-instruct → Start Server (port 1234)"
Write-Host "  2. Edit your credentials:"
Write-Host "       notepad `"$EnvFile`""
Write-Host "     Fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
Write-Host "  3. Launch the app:"
Write-Host "       & `"$Pythonw`" `"$AppScript`""
Write-Host ""
Write-Host "  The app will auto-start on every Windows logon from now on." -ForegroundColor Green
Write-Host ""
