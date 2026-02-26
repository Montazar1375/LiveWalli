"""Detect whether the Mac is on AC power or battery (macOS)."""
import subprocess


def is_on_ac_power() -> bool:
    """
    Return True if the system is on AC power, False if on battery.
    On desktops (no battery) or if detection fails, returns True so wallpapers keep running.
    """
    try:
        result = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return True
        # "Now drawing from 'AC Power'" or "Now drawing from 'Battery Power'"
        out = result.stdout or ""
        if "Now drawing from 'AC Power'" in out:
            return True
        if "Now drawing from 'Battery Power'" in out:
            return False
        # No battery (desktop) or unknown: allow wallpapers
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return True
