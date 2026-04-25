"""
Tech Alert Agent — Windows system tray controller.

Auto-starts at Windows logon (registered by deploy/schedule_windows.ps1).
Manages the bot_listener subprocess, monitors LM Studio health, and
provides one-click manual runs with balloon notifications.

Icon colour:
  Green  — LM Studio reachable, bot listener running
  Yellow — LM Studio not reachable (bot listener still runs)
  Red    — Both LM Studio and bot listener are down
"""

import os
import sys
import subprocess
import threading
import time
import datetime

import httpx
import pystray
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON       = sys.executable
LOG_FILE     = os.path.join(PROJECT_ROOT, "logs", "tech_alert.log")
ENV_FILE     = os.path.join(PROJECT_ROOT, ".env")
LM_HEALTH    = "http://localhost:1234/v1/models"
# Path to LM Studio executable (common install locations)
_LM_STUDIO_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\LM Studio\LM Studio.exe"),
    os.path.expandvars(r"%APPDATA%\LM Studio\LM Studio.exe"),
    r"C:\Program Files\LM Studio\LM Studio.exe",
]

_WIN32 = sys.platform == "win32"
_NO_WIN = subprocess.CREATE_NO_WINDOW if _WIN32 else 0

_last_run: dict  = {"full": None, "alert": None}
_last_err: dict  = {"full": None, "alert": None}
_bot_proc        = None
_lm_ok: bool     = False
_bot_ok: bool    = False
_lock            = threading.Lock()


# ---------------------------------------------------------------------------
# Icon drawing

def _make_icon(lm: bool, bot: bool) -> Image.Image:
    if lm and bot:
        color = "#27ae60"    # green — all good
    elif lm or bot:
        color = "#e67e22"    # orange — partial
    else:
        color = "#e74c3c"    # red — both down
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
    text = "TA"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - 2), text, fill="white", font=font)
    return img


# ---------------------------------------------------------------------------
# LM Studio helpers

def _check_lm() -> bool:
    try:
        r = httpx.get(LM_HEALTH, timeout=2)
        return r.is_success
    except Exception:
        return False


def _open_lm_studio(_icon, _item):
    for path in _LM_STUDIO_PATHS:
        if os.path.exists(path):
            os.startfile(path)
            return
    # Fallback: try the system PATH
    try:
        subprocess.Popen(["LM Studio"], creationflags=_NO_WIN, shell=True)
    except Exception:
        _icon.notify(
            "LM Studio not found in common locations.\n"
            "Open it manually from the Start Menu.",
            "Tech Alert"
        )


# ---------------------------------------------------------------------------
# Bot listener management

def _spawn_bot_listener():
    global _bot_proc
    script = os.path.join(PROJECT_ROOT, "bot_listener.py")
    _bot_proc = subprocess.Popen(
        [PYTHON, script],
        cwd=PROJECT_ROOT,
        creationflags=_NO_WIN,
    )


def _bot_watchdog(icon: pystray.Icon):
    """Restart bot_listener automatically if it exits unexpectedly."""
    global _bot_proc, _bot_ok
    while True:
        time.sleep(10)
        with _lock:
            alive = _bot_proc is not None and _bot_proc.poll() is None
            _bot_ok = alive
        if not alive:
            icon.notify("Bot listener stopped — restarting…", "Tech Alert")
            _spawn_bot_listener()


# ---------------------------------------------------------------------------
# Run helpers

def _run_mode(icon: pystray.Icon, mode: str):
    label = "Full Briefing" if mode == "full" else "Alert Scan"
    icon.notify(f"Starting {label}…", "Tech Alert")

    proc = subprocess.Popen(
        [PYTHON, os.path.join(PROJECT_ROOT, "main.py"), "--mode", mode],
        cwd=PROJECT_ROOT,
        creationflags=_NO_WIN,
    )

    def _wait():
        proc.wait()
        now = datetime.datetime.now()
        if proc.returncode == 0:
            _last_run[mode] = now
            _last_err[mode] = None
            icon.notify(f"{label} done ✓", "Tech Alert")
        else:
            _last_err[mode] = now
            icon.notify(f"{label} failed (code {proc.returncode}) — check logs", "Tech Alert")
        _refresh_tooltip(icon)

    threading.Thread(target=_wait, daemon=True).start()


# ---------------------------------------------------------------------------
# Tooltip

def _fmt_ago(t: datetime.datetime | None) -> str:
    if t is None:
        return "never"
    delta = datetime.datetime.now() - t
    mins  = int(delta.total_seconds() / 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"
    return f"{int(mins/60)}h {mins%60}m ago"


def _refresh_tooltip(icon: pystray.Icon):
    lm  = "✓ LM Studio running"  if _lm_ok  else "✗ LM Studio NOT running"
    bot = "✓ Bot listener alive" if _bot_ok  else "✗ Bot listener stopped"
    err_full  = f"  (last error: {_fmt_ago(_last_err['full'])})"  if _last_err["full"]  else ""
    err_alert = f"  (last error: {_fmt_ago(_last_err['alert'])})" if _last_err["alert"] else ""
    icon.title = (
        f"Tech Alert Agent\n"
        f"{lm}\n"
        f"{bot}\n"
        f"Last briefing : {_fmt_ago(_last_run['full'])}{err_full}\n"
        f"Last alert    : {_fmt_ago(_last_run['alert'])}{err_alert}"
    )


# ---------------------------------------------------------------------------
# Background status poller

def _status_loop(icon: pystray.Icon):
    global _lm_ok, _bot_ok
    while True:
        lm  = _check_lm()
        bot = _bot_proc is not None and _bot_proc.poll() is None
        with _lock:
            _lm_ok  = lm
            _bot_ok = bot
        icon.icon = _make_icon(lm, bot)
        _refresh_tooltip(icon)
        time.sleep(30)


# ---------------------------------------------------------------------------
# Menu actions

def _open_logs(_icon, _item):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
    os.startfile(LOG_FILE)


def _open_env(_icon, _item):
    if not os.path.exists(ENV_FILE):
        import shutil
        shutil.copy(os.path.join(PROJECT_ROOT, ".env.example"), ENV_FILE)
    os.startfile(ENV_FILE)


def _check_connection(icon: pystray.Icon, _item):
    ok = _check_lm()
    if ok:
        icon.notify("LM Studio is reachable on port 1234 ✓", "Tech Alert")
    else:
        icon.notify(
            "Cannot reach LM Studio on port 1234.\n"
            "Open LM Studio → Local Server tab → Start Server.",
            "Tech Alert — Connection Problem"
        )


def _restart_listener(icon: pystray.Icon, _item):
    global _bot_proc
    if _bot_proc and _bot_proc.poll() is None:
        _bot_proc.terminate()
    _spawn_bot_listener()
    icon.notify("Bot listener restarted.", "Tech Alert")


def _exit(icon: pystray.Icon, _item):
    if _bot_proc and _bot_proc.poll() is None:
        _bot_proc.terminate()
    icon.stop()


# ---------------------------------------------------------------------------
# Entry point

def main():
    _spawn_bot_listener()

    menu = pystray.Menu(
        pystray.MenuItem("Run News Now",         lambda icon, item: _run_mode(icon, "full")),
        pystray.MenuItem("Run Alert Scan",       lambda icon, item: _run_mode(icon, "alert")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Check LM Studio",      _check_connection),
        pystray.MenuItem("Open LM Studio",       _open_lm_studio),
        pystray.MenuItem("Restart Bot Listener", _restart_listener),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("View Logs",            _open_logs),
        pystray.MenuItem("Edit Settings (.env)", _open_env),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit",                 _exit),
    )

    icon = pystray.Icon(
        "TechAlert",
        _make_icon(False, False),
        "Tech Alert Agent — starting…",
        menu,
    )

    threading.Thread(target=_status_loop,  args=(icon,), daemon=True).start()
    threading.Thread(target=_bot_watchdog, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()
