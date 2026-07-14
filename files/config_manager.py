"""
config_manager.py
Handles saving/loading app settings to a local JSON file.
"""
import json
import os

import base64
import json
import os

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".file_monitor_config.json")
APP_VERSION = "1.0.0"

DEFAULT_CONFIG = {
    "sender_email": "",
    "sender_app_password": "",
    "receiver_email": "",
    "watch_folder": "",
    "watch_folders": [],
    "file_extensions": [".txt", ".pdf", ".docx", ".xlsx", ".jpg", ".png", ".csv"],
    "watch_created": True,
    "watch_deleted": True,
    "watch_modified": False,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "excluded_paths": ["AppData", "Temp", "~$", "$", "Recycle.Bin", "Edge", "Windows", "Cache", ".git", "node_modules", "__pycache__"],
    "run_in_background_on_close": False,
    "run_on_startup": False,
}


def obfuscate(plain_text: str) -> str:
    """Obfuscate plain text to base64 to avoid plain text visibility on disk."""
    if not plain_text:
        return ""
    try:
        return base64.b64encode(plain_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return plain_text


def deobfuscate(cipher_text: str) -> str:
    """Deobfuscate base64 text back to plain text."""
    if not cipher_text:
        return ""
    try:
        return base64.b64decode(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return cipher_text


def load_config():
    """Load config from disk, or return defaults if not present."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Fill in any missing keys with defaults (handles upgrades)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            if merged.get("sender_app_password"):
                merged["sender_app_password"] = deobfuscate(merged["sender_app_password"])
            return merged
        except (json.JSONDecodeError, OSError):
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Save config dict to disk, obfuscating the password first."""
    config_copy = config.copy()
    if "sender_app_password" in config_copy:
        config_copy["sender_app_password"] = obfuscate(config_copy["sender_app_password"])
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_copy, f, indent=2)


def get_icon_path():
    """Get absolute path to app_icon.png, supporting PyInstaller bundles and dev environments."""
    import sys
    try:
        # If running in PyInstaller bundle
        base_path = sys._MEIPASS
        return os.path.join(base_path, "files", "app_icon.png")
    except Exception:
        # Development environment (config_manager.py is in files/)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")
