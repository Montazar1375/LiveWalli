"""Persistent storage for wallpaper paths per screen (JSON)."""
from __future__ import annotations

import json
import os
from typing import Optional

CONFIG_DIR = os.path.expanduser("~/.config/livewalli")
CONFIG_PATH = os.path.join(CONFIG_DIR, "wallpapers.json")

# Keys: screen index (int as str) or "default" -> path (str)
# Scale mode: "scale_modes" -> { screen_index: "fill"|"fit"|"stretch"|"center" }
# Recent: "recent_paths" -> [path, ...] (max RECENT_MAX)

RECENT_MAX = 10


def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_wallpapers() -> dict:
    """Load { "0": "/path/to/video.mp4", "1": "...", "scale_modes": {"0": "fill"} }."""
    _ensure_config_dir()
    if not os.path.exists(CONFIG_PATH):
        return {"scale_modes": {}}
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        if "scale_modes" not in data:
            data["scale_modes"] = {}
        return data
    except (json.JSONDecodeError, IOError):
        return {"scale_modes": {}}


def save_wallpapers(data: dict) -> None:
    """Save wallpaper paths and scale modes."""
    _ensure_config_dir()
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_path_for_screen(screen_index: int) -> Optional[str]:
    data = load_wallpapers()
    key = str(screen_index)
    return data.get(key)


def set_path_for_screen(screen_index: int, path: Optional[str]) -> None:
    data = load_wallpapers()
    key = str(screen_index)
    if path is None:
        data.pop(key, None)
    else:
        data[key] = path
    save_wallpapers(data)


def get_scale_mode(screen_index: int) -> str:
    """One of 'fill', 'fit', 'stretch', 'center'. Default 'fill'."""
    data = load_wallpapers()
    modes = data.get("scale_modes", {})
    return modes.get(str(screen_index), "fill")


def set_scale_mode(screen_index: int, mode: str) -> None:
    data = load_wallpapers()
    if "scale_modes" not in data:
        data["scale_modes"] = {}
    data["scale_modes"][str(screen_index)] = mode
    save_wallpapers(data)


def get_power_connected_only() -> bool:
    """True if wallpapers should run only when AC power is connected."""
    data = load_wallpapers()
    return data.get("power_connected_only", False)


def set_power_connected_only(enabled: bool) -> None:
    """Set whether wallpapers run only when power is connected."""
    data = load_wallpapers()
    data["power_connected_only"] = enabled
    save_wallpapers(data)


def get_recent_paths() -> list:
    """Return list of recently used video paths (newest first), max RECENT_MAX."""
    data = load_wallpapers()
    return list(data.get("recent_paths", []))[:RECENT_MAX]


def add_recent_path(path: str) -> None:
    """Prepend path to recent list, deduplicate, trim to RECENT_MAX."""
    if not path or not path.strip():
        return
    data = load_wallpapers()
    recent = data.get("recent_paths", [])
    path = os.path.normpath(path)
    recent = [path] + [p for p in recent if os.path.normpath(p) != path]
    data["recent_paths"] = recent[:RECENT_MAX]
    save_wallpapers(data)


def remove_recent_path(path: str) -> None:
    """Remove path from the recent list."""
    if not path or not path.strip():
        return
    data = load_wallpapers()
    recent = data.get("recent_paths", [])
    path_norm = os.path.normpath(path)
    recent = [p for p in recent if os.path.normpath(p) != path_norm]
    data["recent_paths"] = recent
    save_wallpapers(data)
