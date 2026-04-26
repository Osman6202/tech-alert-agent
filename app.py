"""
Tech Alert Agent — entry point.

Launched by Windows Startup shortcut:
  pythonw.exe "path\\to\\app.py"

The os.chdir() call must come before any local imports because
the Startup shortcut working directory defaults to %USERPROFILE%.
"""

import os
import sys

# Anchor all relative paths (logs/, state.json, .env) to project root.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Validate required env vars before the GUI opens.
# Import config after load_dotenv() so os.environ is populated.
from config import validate_config
from logger import get_logger

logger = get_logger(__name__)

warnings = validate_config()
for w in warnings:
    logger.warning(f"Config: {w}")

from gui import MainWindow

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
