<#
.SYNOPSIS
    Registers Tech Alert Agent tasks in Windows Task Scheduler.
.DESCRIPTION
    Creates four scheduled tasks so everything runs automatically after
    every PC restart — no terminal steps needed:
      - TechAlert-TrayApp         : starts tray icon + bot listener at logon
      - TechAlert-FullBriefing-AM : full news briefing daily at 08:00
      - TechAlert-FullBriefing-PM : full news briefing daily at 20:00
      - TechAlert-AlertScan       : HIGH ALERT scan every hour
.NOTES
    Must be run as Administrator.
.EXAMPLE
    # Right-click PowerShell -> "Run as Administrator", then:
    cd C:\Users\You\tech-alert-agent
    PowerShell -ExecutionPolicy Bypass -File deploy\schedule_windows.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Admin check ────────────────────────────────────────────────────────────
$me = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $me.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host ""
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    Write-Host "Right-click PowerShell and choose 'Run as Administrator'." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Tech Alert Agent — Task Scheduler     " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Resolve paths ──────────────────────────────────────────────────────────
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPython  = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: $VenvPython not found." -ForegroundColor Red
    Write-Host "Run deploy\setup_windows.ps1 first." -ForegroundColor Yellow
    exit 1
}

$MainScript  = Join-Path $ProjectRoot "main.py"
$TrayScript  = Join-Path $ProjectRoot "tray_app.py"
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Write-Host "Project root : $ProjectRoot"
Write-Host "Python       : $VenvPython"
Write-Host "Running as   : $CurrentUser"
Write-Host ""

# ── Helper ─────────────────────────────────────────────────────────────────
function Register-AlertTask {
    param(
        [string]$Name,
        [string]$Description,
        [string]$Arguments,
        $Trigger
    )
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue

    $action = New-ScheduledTaskAction `
        -Execute          $VenvPython `
        -Argument         $Arguments `
        -WorkingDirectory $ProjectRoot

    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit  (New-TimeSpan -Hours 1) `
        -StartWhenAvailable `
        -MultipleInstances   IgnoreNew `
        -Hidden

    $principal = New-ScheduledTaskPrincipal `
        -UserId    $CurrentUser `
        -LogonType Interactive `
        -RunLevel  Highest

    Register-ScheduledTask `
        -TaskName    $Name `
        -Description $Description `
        -Action      $action `
        -Trigger     $Trigger `
        -Settings    $settings `
        -Principal   $principal `
        -Force | Out-Null

    Write-Host "  [OK] $Name" -ForegroundColor Green
}

# ── Task 1: Tray App at logon (manages bot_listener automatically) ─────────
Write-Host "Registering tasks..." -ForegroundColor Cyan
$trigLogon = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
Register-AlertTask `
    -Name        "TechAlert-TrayApp" `
    -Description "Tech Alert system tray controller — starts at Windows logon" `
    -Arguments   "`"$TrayScript`"" `
    -Trigger     $trigLogon

# ── Task 2: Full briefing AM ───────────────────────────────────────────────
$trigAM = New-ScheduledTaskTrigger -Daily -At "08:00"
Register-AlertTask `
    -Name        "TechAlert-FullBriefing-AM" `
    -Description "Tech Alert full news briefing — morning (08:00)" `
    -Arguments   "`"$MainScript`" --mode full" `
    -Trigger     $trigAM

# ── Task 3: Full briefing PM ───────────────────────────────────────────────
$trigPM = New-ScheduledTaskTrigger -Daily -At "20:00"
Register-AlertTask `
    -Name        "TechAlert-FullBriefing-PM" `
    -Description "Tech Alert full news briefing — evening (20:00)" `
    -Arguments   "`"$MainScript`" --mode full" `
    -Trigger     $trigPM

# ── Task 4: Hourly alert scan ──────────────────────────────────────────────
$trigHourly = New-ScheduledTaskTrigger -Daily -At "00:00"
$trigHourly.Repetition.Interval = "PT1H"
$trigHourly.Repetition.Duration = "P1D"
Register-AlertTask `
    -Name        "TechAlert-AlertScan" `
    -Description "Tech Alert HIGH ALERT scan — every hour" `
    -Arguments   "`"$MainScript`" --mode alert" `
    -Trigger     $trigHourly

# ── Summary ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All tasks registered successfully!    " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "What happens now:" -ForegroundColor Cyan
Write-Host "  - Next time you log in to Windows, the tray icon appears automatically."
Write-Host "  - The bot listener starts with it (handles Telegram 'RUN NEWS' / 'RUN ALERT')."
Write-Host "  - Full briefings fire at 08:00 and 20:00 every day."
Write-Host "  - Alert scans run every hour in the background."
Write-Host ""
Write-Host "Manage tasks: open Task Scheduler (taskschd.msc)"
Write-Host "  or run: Get-ScheduledTask -TaskName 'TechAlert-*'"
Write-Host ""
Write-Host "IMPORTANT: LM Studio must be running with a model loaded" -ForegroundColor Yellow
Write-Host "           for the AI categorization to work." -ForegroundColor Yellow
Write-Host ""
Write-Host "Start the tray app right now (no need to log out):"
Write-Host "  `"$VenvPython`" `"$TrayScript`""
Write-Host ""
