import os

# Minimal env for tests — prevents hard crashes on config.py import
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")
os.environ.setdefault("TELEGRAM_CHAT_ID",   "test")
os.environ.setdefault("ANTHROPIC_API_KEY",  "test")
