"""
Internal job scheduler.

Fires run_full() at 08:00 and 20:00 MYT and run_alert() every hour.
All times are converted to the machine's local clock at startup using
zoneinfo so the schedule is correct regardless of the Windows timezone.
"""

import datetime
import threading
import time
import zoneinfo
from typing import Callable

import schedule

from config import SCHEDULE_TZ
from logger import get_logger

logger = get_logger(__name__)


class Scheduler:
    def __init__(self) -> None:
        self._running    = False
        self._thread: threading.Thread | None = None
        self._on_full:  Callable | None = None
        self._on_alert: Callable | None = None

    def start(self, on_full: Callable, on_alert: Callable) -> None:
        self._on_full  = on_full
        self._on_alert = on_alert

        local_hour_full, local_hour_full_pm = self._myt_to_local(8), self._myt_to_local(20)

        schedule.every().day.at(f"{local_hour_full:02d}:00").do(self._fire_full)
        schedule.every().day.at(f"{local_hour_full_pm:02d}:00").do(self._fire_full)
        schedule.every().hour.do(self._fire_alert)

        logger.info(
            f"Scheduler started — full briefings at "
            f"{local_hour_full:02d}:00 and {local_hour_full_pm:02d}:00 local time "
            f"(08:00 and 20:00 {SCHEDULE_TZ}); alert scan every hour"
        )

        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="Scheduler")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        schedule.clear()

    def next_run_times(self) -> dict:
        """Return next fire times for the GUI schedule panel."""
        jobs  = schedule.get_jobs()
        full  = [j.next_run for j in jobs if j.job_func.__name__ == "_fire_full"]
        alert = [j.next_run for j in jobs if j.job_func.__name__ == "_fire_alert"]
        return {
            "next_full":  min(full)  if full  else None,
            "next_alert": min(alert) if alert else None,
        }

    # ------------------------------------------------------------------

    def _myt_to_local(self, myt_hour: int) -> int:
        """Convert an MYT hour to the equivalent local-clock hour."""
        try:
            tz        = zoneinfo.ZoneInfo(SCHEDULE_TZ)
            now_local = datetime.datetime.now()
            now_tz    = datetime.datetime.now(tz).replace(tzinfo=None)
            offset    = round((now_local - now_tz).total_seconds() / 3600)
        except Exception:
            offset = 0  # if zoneinfo lookup fails, treat local == MYT
        return (myt_hour + offset) % 24

    def _loop(self) -> None:
        while self._running:
            schedule.run_pending()
            time.sleep(30)

    def _fire_full(self) -> None:
        threading.Thread(target=self._on_full, daemon=True, name="run_full").start()

    def _fire_alert(self) -> None:
        threading.Thread(target=self._on_alert, daemon=True, name="run_alert").start()
