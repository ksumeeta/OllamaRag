import os
from datetime import datetime

LOG_FILE = "debug_log.txt"

def log_debug(message: str):
    """Logs a message to debug_log.txt in the project root."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Failed to log debug message: {e}")
