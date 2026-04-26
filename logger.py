import logging
import sys
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "tech_alert.log")

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.INFO)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(_fmt)
    logger.addHandler(file_handler)

    # pythonw.exe has no stdout — skip the console handler when there's no terminal
    if sys.stdout is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(_fmt)
        logger.addHandler(console_handler)

    return logger


def add_gui_handler(handler: logging.Handler) -> None:
    """Attach a handler to the root logger so every module emits to the GUI."""
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)
