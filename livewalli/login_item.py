"""Start LiveWalli at login via a Launch Agent (macOS)."""
import os
import subprocess
import sys
import plistlib

LAUNCH_AGENT_LABEL = "com.livewalli.app"
PLIST_NAME = LAUNCH_AGENT_LABEL + ".plist"


def _project_root() -> str:
    """Path to the LiveWalli project directory (parent of livewalli package)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _app_path() -> str:
    """Path to LiveWalli.app, or empty if not found."""
    # When running inside a built .app (py2app), executable is .app/Contents/MacOS/...
    exe = os.path.abspath(sys.executable)
    if ".app" in exe and "Contents" in exe:
        # Go up from .../App.app/Contents/MacOS/python to .../App.app
        for _ in range(3):
            exe = os.path.dirname(exe)
        if exe.endswith(".app") and os.path.isdir(exe):
            return exe
    root = _project_root()
    app_path = os.path.join(root, "LiveWalli.app")
    return app_path if os.path.isdir(app_path) else ""


def _launch_agent_plist_path() -> str:
    return os.path.expanduser("~/Library/LaunchAgents/" + PLIST_NAME)


def is_login_enabled() -> bool:
    """True if the Launch Agent plist exists (start at login is enabled)."""
    return os.path.isfile(_launch_agent_plist_path())


def set_login_enabled(enabled: bool) -> bool:
    """
    Enable or disable start at login. Returns True on success.
    Uses a Launch Agent that runs `open -a LiveWalli.app` at login.
    """
    plist_path = _launch_agent_plist_path()
    if enabled:
        app_path = _app_path()
        if not app_path:
            return False
        content = {
            "Label": LAUNCH_AGENT_LABEL,
            "ProgramArguments": ["/usr/bin/open", "-a", app_path],
            "RunAtLoad": True,
        }
        launch_agents_dir = os.path.dirname(plist_path)
        try:
            os.makedirs(launch_agents_dir, exist_ok=True)
            with open(plist_path, "wb") as f:
                plistlib.dump(content, f, sort_keys=False)
        except OSError:
            return False
        # Do NOT launchctl load here: that would run the job immediately and start a second instance.
        # The plist will be loaded automatically at next login.
        return True
    else:
        try:
            subprocess.run(
                ["launchctl", "unload", plist_path],
                capture_output=True,
                timeout=5,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        try:
            if os.path.isfile(plist_path):
                os.remove(plist_path)
        except OSError:
            return False
        return True


def can_use_login_item() -> bool:
    """True if start-at-login is available (LiveWalli.app exists)."""
    return bool(_app_path())
