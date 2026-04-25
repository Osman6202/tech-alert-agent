"""
Tech Alert Agent — Windows system tray controller.

Auto-starts at Windows logon (registered by deploy/schedule_windows.ps1).
Manages the bot_listener subprocess and provides one-click manual runs.

Icon colour:
  Green  — LM Studio reachable, bot listener running
  Yellow — LM Studio not reachable (bot listener still runs for Telegram cmds)
  Red    — Fatal startup error
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

_last_run: dict = {"full": None, "alert": None}   # datetime or None
_bot_proc: subprocess.Popen | None = None
_lm_ok   : bool = False


# ---------------------------------------------------------------------------
# Icon drawing

def _make_icon(color: str) -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Filled circle
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    # "TA" label — use default font, centred
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
# LM Studio health

def _check_lm() -> bool:
    try:
        r = httpx.get(LM_HEALTH, timeout=2)
        return r.is_success
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Subprocess helpers

def _start_bot_listener():
    global _bot_proc
    script = os.path.join(PROJECT_ROOT, "bot_listener.py")
    _bot_proc = subprocess.Popen(
        [PYTHON, script],
        cwd=PROJECT_ROOT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def _run_mode(icon: pystray.Icon, mode: str):
    label = "Full Briefing" if mode == "full" else "Alert Scan"
    icon.notify(f"Starting {label}…", "Tech Alert")
    proc = subprocess.Popen(
        [PYTHON, os.path.join(PROJECT_ROOT, "main.py"), "--mode", mode],
        cwd=PROJECT_ROOT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    def _wait():
        proc.wait()
        _last_run[mode] = datetime.datetime.now()
        result = "done ✓" if proc.returncode == 0 else f"failed (code {proc.returncode})"
        icon.notify(f"{label} {result}", "Tech Alert")
        _refresh_tooltip(icon)

    threading.Thread(target=_wait, daemon=True).start()


# ---------------------------------------------------------------------------
# Tooltip / status

def _fmt_last(mode: str) -> str:
    t = _last_run.get(mode)
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
    lm_status = "LM Studio: OK" if _lm_ok else "LM Studio: NOT running"
    bot_alive  = _bot_proc is not None and _bot_proc.poll() is None
    bot_status = "Bot listener: running" if bot_alive else "Bot listener: stopped"
    icon.title = (
        f"Tech Alert Agent\n"
        f"{lm_status}\n"
        f"{bot_status}\n"
        f"Last news: {_fmt_last('full')}  |  Last alert: {_fmt_last('alert')}"
    )


# ---------------------------------------------------------------------------
# Background status poller

def _status_loop(icon: pystray.Icon):
    global _lm_ok
    while True:
        _lm_ok = _check_lm()
        icon.icon = _make_icon("#27ae60" if _lm_ok else "#e67e22")
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
    msg = "LM Studio is reachable on port 1234." if ok else (
        "Cannot reach LM Studio.\n"
        "Make sure LM Studio is open and the local server is started."
    )
    icon.notify(msg, "Tech Alert — Connection Check")


def _restart_listener(icon: pystray.Icon, _item):
    global _bot_proc
    if _bot_proc and _bot_proc.poll() is None:
        _bot_proc.terminate()
    _start_bot_listener()
    icon.notify("Bot listener restarted.", "Tech Alert")


def _exit(icon: pystray.Icon, _item):
    if _bot_proc and _bot_proc.poll() is None:
        _bot_proc.terminate()
    icon.stop()


# ---------------------------------------------------------------------------
# Entry point

def main():
    _start_bot_listener()

    menu = pystray.Menu(
        pystray.MenuItem("Run News Now",   lambda icon, item: _run_mode(icon, "full")),
        pystray.MenuItem("Run Alert Scan", lambda icon, item: _run_mode(icon, "alert")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Check LM Studio", _check_connection),
        pystray.MenuItem("Restart Bot Listener", _restart_listener),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("View Logs",      _open_logs),
        pystray.MenuItem("Edit Settings",  _open_env),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit",           _exit),
    )

    icon = pystray.Icon(
        "TechAlert",
        _make_icon("#e67e22"),   # start yellow until first health check
        "Tech Alert Agent — starting…",
        menu,
    )

    threading.Thread(target=_status_loop, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()
