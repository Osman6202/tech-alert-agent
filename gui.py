"""
Tech Alert Agent — main GUI window.

Uses customtkinter for a modern look. All widget mutations happen on
the main (Tk) thread via after() + queue draining. Runner threads post
log lines and UI commands into thread-safe queues.
"""

import logging
import os
import queue
import subprocess
import sys
import threading
import time
import datetime
from typing import Callable

import customtkinter as ctk
import httpx
from PIL import Image, ImageDraw, ImageFont
import pystray

import runner
from scheduler import Scheduler
from config import SCHEDULE_TZ
from logger import get_logger, add_gui_handler

logger = get_logger(__name__)

_WIN32    = sys.platform == "win32"
_NO_WIN   = subprocess.CREATE_NO_WINDOW if _WIN32 else 0
LM_HEALTH = "http://localhost:1234/v1/models"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ---------------------------------------------------------------------------
# Thread-safe log handler

class _GUILogHandler(logging.Handler):
    def __init__(self, q: queue.Queue) -> None:
        super().__init__()
        self._q = q
        self.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._q.put_nowait(self.format(record))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tray icon helpers

def _make_tray_image(lm_ok: bool, bot_ok: bool) -> Image.Image:
    if lm_ok and bot_ok:
        color = "#27ae60"
    elif lm_ok or bot_ok:
        color = "#e67e22"
    else:
        color = "#e74c3c"
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
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - 2), text, fill="white", font=font)
    return img


# ---------------------------------------------------------------------------
# Main window

class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Tech Alert Agent")
        self.geometry("840x640")
        self.minsize(700, 520)

        # Queues for inter-thread communication
        self._log_queue: queue.Queue = queue.Queue()
        self._ui_queue:  queue.Queue = queue.Queue()

        # Run-lock events (prevent double-trigger)
        self._full_lock  = threading.Event()
        self._alert_lock = threading.Event()

        # State
        self._lm_ok        = False
        self._lm_model     = "unknown"
        self._bot_ok       = False
        self._bot_proc: subprocess.Popen | None = None
        self._tray_icon: pystray.Icon | None    = None
        self._last_full:  datetime.datetime | None = None
        self._last_alert: datetime.datetime | None = None

        # Wire logging to GUI
        add_gui_handler(_GUILogHandler(self._log_queue))

        self._build_ui()

        # Intercept close → minimize to tray
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start background threads
        self._start_bot_listener()
        threading.Thread(target=self._status_loop, daemon=True, name="StatusPoller").start()
        threading.Thread(target=self._run_tray,   daemon=True, name="TrayIcon").start()
        threading.Thread(target=self._bot_watchdog, daemon=True, name="BotWatchdog").start()

        # Start scheduler
        self._scheduler = Scheduler()
        self._scheduler.start(
            on_full  = self._run_full_worker,
            on_alert = self._run_alert_worker,
        )

        # Start the queue-drain loop
        self.after(200, self._drain_queues)

        logger.info("Tech Alert Agent started — all systems initialising…")

    # ------------------------------------------------------------------
    # UI construction

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)   # log panel expands

        # ── Status bar ─────────────────────────────────────────────────
        status_frame = ctk.CTkFrame(self, corner_radius=8)
        status_frame.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")
        status_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self._lbl_lm     = ctk.CTkLabel(status_frame, text="● LM Studio: checking…",
                                         font=ctk.CTkFont(size=13))
        self._lbl_tg     = ctk.CTkLabel(status_frame, text="● Telegram: configured",
                                         font=ctk.CTkFont(size=13), text_color="#27ae60")
        self._lbl_bot    = ctk.CTkLabel(status_frame, text="● Bot: starting…",
                                         font=ctk.CTkFont(size=13))
        self._lbl_lm.grid(row=0,  column=0, padx=16, pady=8, sticky="w")
        self._lbl_tg.grid(row=0,  column=1, padx=16, pady=8)
        self._lbl_bot.grid(row=0, column=2, padx=16, pady=8, sticky="e")

        # ── Schedule panel ─────────────────────────────────────────────
        sched_frame = ctk.CTkFrame(self, corner_radius=8)
        sched_frame.grid(row=1, column=0, padx=12, pady=4, sticky="ew")
        sched_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(sched_frame, text="SCHEDULE",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=0, column=0, columnspan=2,
                                             padx=16, pady=(8, 2), sticky="w")

        self._lbl_next_full  = ctk.CTkLabel(sched_frame, text="Next briefing: —",
                                             font=ctk.CTkFont(size=13))
        self._lbl_next_alert = ctk.CTkLabel(sched_frame, text="Next alert scan: —",
                                             font=ctk.CTkFont(size=13))
        self._lbl_last_full  = ctk.CTkLabel(sched_frame, text="Last briefing: never",
                                             font=ctk.CTkFont(size=12), text_color="gray")
        self._lbl_last_alert = ctk.CTkLabel(sched_frame, text="Last alert: never",
                                             font=ctk.CTkFont(size=12), text_color="gray")

        self._lbl_next_full.grid( row=1, column=0, padx=16, pady=2, sticky="w")
        self._lbl_next_alert.grid(row=1, column=1, padx=16, pady=2, sticky="w")
        self._lbl_last_full.grid( row=2, column=0, padx=16, pady=(2, 8), sticky="w")
        self._lbl_last_alert.grid(row=2, column=1, padx=16, pady=(2, 8), sticky="w")

        # ── Controls ───────────────────────────────────────────────────
        ctrl_frame = ctk.CTkFrame(self, corner_radius=8)
        ctrl_frame.grid(row=2, column=0, padx=12, pady=4, sticky="ew")
        ctrl_frame.grid_columnconfigure((0, 1), weight=1)

        self._btn_full  = ctk.CTkButton(ctrl_frame, text="▶  Run Full Briefing",
                                         command=self._run_full_clicked,
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         height=40)
        self._btn_alert = ctk.CTkButton(ctrl_frame, text="▶  Run Alert Scan",
                                         command=self._run_alert_clicked,
                                         font=ctk.CTkFont(size=14),
                                         height=40, fg_color="#c0392b",
                                         hover_color="#922b21")
        self._btn_full.grid( row=0, column=0, padx=16, pady=12, sticky="ew")
        self._btn_alert.grid(row=0, column=1, padx=16, pady=12, sticky="ew")

        # ── Activity log ───────────────────────────────────────────────
        log_frame = ctk.CTkFrame(self, corner_radius=8)
        log_frame.grid(row=3, column=0, padx=12, pady=4, sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="ACTIVITY LOG",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=0, column=0, padx=16, pady=(8, 0), sticky="w")

        self._log_box = ctk.CTkTextbox(log_frame, state="disabled",
                                        font=ctk.CTkFont(family="Courier New", size=12),
                                        wrap="word")
        self._log_box.grid(row=1, column=0, padx=8, pady=(4, 8), sticky="nsew")

        # ── Bottom bar ─────────────────────────────────────────────────
        bottom_frame = ctk.CTkFrame(self, corner_radius=8)
        bottom_frame.grid(row=4, column=0, padx=12, pady=(4, 12), sticky="ew")
        bottom_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(bottom_frame, text="Open Settings (.env)",
                      command=self._open_env, width=180,
                      fg_color="gray30", hover_color="gray20").grid(
            row=0, column=0, padx=16, pady=8, sticky="w")

        ctk.CTkButton(bottom_frame, text="View Logs",
                      command=self._open_logs, width=120,
                      fg_color="gray30", hover_color="gray20").grid(
            row=0, column=1, padx=4, pady=8, sticky="w")

        ctk.CTkButton(bottom_frame, text="Minimize to Tray",
                      command=self._on_close, width=150,
                      fg_color="gray30", hover_color="gray20").grid(
            row=0, column=2, padx=16, pady=8, sticky="e")

    # ------------------------------------------------------------------
    # Queue drain loop (runs on main thread via after())

    def _drain_queues(self) -> None:
        # Drain log lines
        try:
            while True:
                line = self._log_queue.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass

        # Drain UI commands
        try:
            while True:
                cmd, *args = self._ui_queue.get_nowait()
                self._handle_ui_cmd(cmd, args)
        except queue.Empty:
            pass

        self.after(200, self._drain_queues)

    def _append_log(self, line: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", line + "\n")
        # Ring buffer: keep last 200 lines
        idx  = self._log_box.index("end-1c")
        nlines = int(idx.split(".")[0])
        if nlines > 200:
            self._log_box.delete("1.0", f"{nlines - 200}.0")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _handle_ui_cmd(self, cmd: str, args: list) -> None:
        if cmd == "enable_btn":
            btn = self._btn_full if args[0] == "full" else self._btn_alert
            label = "▶  Run Full Briefing" if args[0] == "full" else "▶  Run Alert Scan"
            btn.configure(state="normal", text=label)
        elif cmd == "set_lm_status":
            ok, model = args
            self._lm_ok    = ok
            self._lm_model = model
            dot = "●"
            if ok:
                self._lbl_lm.configure(
                    text=f"{dot} LM Studio: {model}", text_color="#27ae60")
            else:
                self._lbl_lm.configure(
                    text=f"{dot} LM Studio: {model}", text_color="#e74c3c")
            self._refresh_tray_icon()
        elif cmd == "set_bot_status":
            ok = args[0]
            self._bot_ok = ok
            self._lbl_bot.configure(
                text=f"● Bot: {'running' if ok else 'stopped'}",
                text_color="#27ae60" if ok else "#e74c3c")
            self._refresh_tray_icon()
        elif cmd == "set_last_full":
            self._last_full = args[0]
            self._lbl_last_full.configure(
                text=f"Last briefing: {self._fmt_time(args[0])}")
        elif cmd == "set_last_alert":
            self._last_alert = args[0]
            self._lbl_last_alert.configure(
                text=f"Last alert: {self._fmt_time(args[0])}")
        elif cmd == "update_schedule":
            times = args[0]
            nf    = times.get("next_full")
            na    = times.get("next_alert")
            self._lbl_next_full.configure(
                text=f"Next briefing: {self._fmt_countdown(nf)}")
            self._lbl_next_alert.configure(
                text=f"Next alert scan: {self._fmt_countdown(na)}")

    # ------------------------------------------------------------------
    # Status polling (background thread, 30-second interval)

    def _status_loop(self) -> None:
        while True:
            # LM Studio
            try:
                r      = httpx.get(LM_HEALTH, timeout=2)
                models = r.json().get("data", [])
                if models:
                    self._ui_queue.put(("set_lm_status", True, models[0]["id"]))
                else:
                    self._ui_queue.put(("set_lm_status", False, "running — no model loaded"))
            except Exception:
                self._ui_queue.put(("set_lm_status", False, "not running"))

            # Bot listener
            alive = self._bot_proc is not None and self._bot_proc.poll() is None
            self._ui_queue.put(("set_bot_status", alive))

            # Schedule times
            try:
                times = self._scheduler.next_run_times()
                self._ui_queue.put(("update_schedule", times))
            except Exception:
                pass

            time.sleep(30)

    # ------------------------------------------------------------------
    # Bot listener subprocess lifecycle

    def _start_bot_listener(self) -> None:
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_listener.py")
        self._bot_proc = subprocess.Popen(
            [sys.executable, script],
            creationflags=_NO_WIN,
        )

    def _bot_watchdog(self) -> None:
        time.sleep(15)  # let it settle first
        while True:
            time.sleep(10)
            if self._bot_proc is None or self._bot_proc.poll() is not None:
                logger.warning("Bot listener stopped — restarting…")
                self._start_bot_listener()

    # ------------------------------------------------------------------
    # Tray icon

    def _run_tray(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Open Tech Alert", self._show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Run Full Briefing",
                             lambda icon, item: self._run_full_clicked()),
            pystray.MenuItem("Run Alert Scan",
                             lambda icon, item: self._run_alert_clicked()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._exit_app),
        )
        self._tray_icon = pystray.Icon(
            "TechAlert",
            _make_tray_image(False, False),
            "Tech Alert Agent",
            menu,
        )
        self._tray_icon.run()

    def _refresh_tray_icon(self) -> None:
        if self._tray_icon:
            self._tray_icon.icon  = _make_tray_image(self._lm_ok, self._bot_ok)
            self._tray_icon.title = (
                "Tech Alert Agent — OK" if (self._lm_ok and self._bot_ok)
                else "Tech Alert Agent — check status"
            )

    def _show_window(self, *_) -> None:
        self.after(0, self._do_show)

    def _do_show(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    # ------------------------------------------------------------------
    # Window close → minimize to tray

    def _on_close(self) -> None:
        self.withdraw()

    def _exit_app(self, *_) -> None:
        if self._bot_proc and self._bot_proc.poll() is None:
            self._bot_proc.terminate()
        self._scheduler.stop()
        if self._tray_icon:
            self._tray_icon.stop()
        self.after(0, self.destroy)

    # ------------------------------------------------------------------
    # Run buttons

    def _run_full_clicked(self) -> None:
        if self._full_lock.is_set():
            logger.warning("Full briefing already running — skipped")
            return
        self._btn_full.configure(state="disabled", text="Running…")
        threading.Thread(target=self._run_full_worker, daemon=True, name="run_full").start()

    def _run_alert_clicked(self) -> None:
        if self._alert_lock.is_set():
            logger.warning("Alert scan already running — skipped")
            return
        self._btn_alert.configure(state="disabled", text="Scanning…")
        threading.Thread(target=self._run_alert_worker, daemon=True, name="run_alert").start()

    def _run_full_worker(self) -> None:
        if self._full_lock.is_set():
            return
        self._full_lock.set()
        try:
            runner.run_full()
            self._ui_queue.put(("set_last_full", datetime.datetime.now()))
        except Exception as e:
            logger.error(f"run_full error: {e}", exc_info=True)
        finally:
            self._full_lock.clear()
            self._ui_queue.put(("enable_btn", "full"))

    def _run_alert_worker(self) -> None:
        if self._alert_lock.is_set():
            return
        self._alert_lock.set()
        try:
            runner.run_alert()
            self._ui_queue.put(("set_last_alert", datetime.datetime.now()))
        except Exception as e:
            logger.error(f"run_alert error: {e}", exc_info=True)
        finally:
            self._alert_lock.clear()
            self._ui_queue.put(("enable_btn", "alert"))

    # ------------------------------------------------------------------
    # Utilities

    def _open_env(self) -> None:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if not os.path.exists(env_path):
            import shutil
            shutil.copy(env_path + ".example", env_path)
        try:
            os.startfile(env_path)
        except Exception:
            subprocess.Popen(["notepad.exe", env_path])

    def _open_logs(self) -> None:
        log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "logs", "tech_alert.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        if not os.path.exists(log_path):
            open(log_path, "w").close()
        try:
            os.startfile(log_path)
        except Exception:
            subprocess.Popen(["notepad.exe", log_path])

    @staticmethod
    def _fmt_time(dt: datetime.datetime | None) -> str:
        if dt is None:
            return "never"
        delta = datetime.datetime.now() - dt
        mins  = int(delta.total_seconds() / 60)
        if mins < 1:
            return f"{dt:%H:%M} (just now)"
        if mins < 60:
            return f"{dt:%H:%M} ({mins}m ago)"
        return f"{dt:%H:%M} ({int(mins/60)}h {mins%60}m ago)"

    @staticmethod
    def _fmt_countdown(dt: datetime.datetime | None) -> str:
        if dt is None:
            return "—"
        delta = dt - datetime.datetime.now()
        total = int(delta.total_seconds())
        if total < 0:
            return "soon"
        h, rem = divmod(total, 3600)
        m      = rem // 60
        if h:
            return f"{dt:%H:%M} (in {h}h {m:02d}m)"
        return f"{dt:%H:%M} (in {m}m)"
