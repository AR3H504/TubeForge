"""
Small persistent settings store.

Saves to a per-user config directory so preferences (like last output folder)
survive app restarts. If nothing has been saved yet, callers get sensible
OS-appropriate defaults (e.g. the user's Downloads folder).
"""

from __future__ import annotations

import json
import os
import sys

APP_NAME = "Tubeforge"


def _config_dir() -> str:
    """OS-appropriate location for a small settings file."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:  # Linux and other unix-likes
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _config_path() -> str:
    return os.path.join(_config_dir(), "settings.json")


def default_download_dir() -> str:
    """The 'just works' default: ~/Downloads/Tubeforge, created if needed."""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(downloads):
        # Fall back to home directory if there's no Downloads folder (rare, some Linux setups)
        downloads = os.path.expanduser("~")
    target = os.path.join(downloads, "Tubeforge")
    os.makedirs(target, exist_ok=True)
    return target


def load() -> dict:
    path = _config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save(data: dict) -> None:
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass  # non-fatal — worst case, preference just doesn't persist


def get_output_dir() -> str:
    """Last-used output folder if the user set one and it still exists, else default."""
    data = load()
    saved = data.get("output_dir")
    if saved and os.path.isdir(saved):
        return saved
    return default_download_dir()


def set_output_dir(path: str) -> None:
    data = load()
    data["output_dir"] = path
    save(data)
