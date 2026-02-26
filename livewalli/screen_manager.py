"""Multi-monitor wallpaper: one WallpaperWindow per NSScreen, hotplug handling."""
from typing import List, Optional, Tuple, Any

from AppKit import (
    NSScreen,
    NSApplicationDidChangeScreenParametersNotification,
    NSTimer,
    NSRunLoop,
    NSDefaultRunLoopMode,
)
from Foundation import NSNotificationCenter

from .wallpaper_window import WallpaperWindow
from . import storage
from . import power_source


def _display_name_for_screen(screen: Any, index: int) -> str:
    """Return display name for screen (e.g. 'Built-in Display', 'LG HDR 4K'). Fallback to Monitor N."""
    try:
        if hasattr(screen, "localizedName") and callable(getattr(screen, "localizedName")):
            name = screen.localizedName()
            if name and isinstance(name, str) and name.strip():
                return name.strip()
    except Exception:
        pass
    frame = screen.frame()
    return f"Monitor {index + 1} ({int(frame.size.width)}×{int(frame.size.height)})"


def _unique_screens() -> List[object]:
    """One NSScreen per physical display (deduplicate by frame: same frame = same monitor)."""
    screens = NSScreen.screens()
    if not screens:
        return []
    seen_frames = set()
    unique = []
    for screen in screens:
        frame = screen.frame()
        key = (
            int(frame.origin.x),
            int(frame.origin.y),
            int(frame.size.width),
            int(frame.size.height),
        )
        if key in seen_frames:
            continue
        seen_frames.add(key)
        unique.append(screen)
    return unique


class ScreenManager:
    """Creates and updates a WallpaperWindow for each screen. Listens for screen changes."""

    def __init__(self):
        self._windows = {}  # screen index -> WallpaperWindow
        self._paused = False
        self._observer = None
        self._occlusion_timer = None

    def start(self):
        self._rebuild_windows()
        nc = NSNotificationCenter.defaultCenter()
        self._observer = nc.addObserverForName_object_queue_usingBlock_(
            NSApplicationDidChangeScreenParametersNotification,
            None,
            None,
            lambda _: self._rebuild_windows(),
        )
        # Energy efficiency: pause when desktop is occluded by full-screen apps
        self._start_occlusion_check()

    def _start_occlusion_check(self):
        def check(_):
            power_ok = not storage.get_power_connected_only() or power_source.is_on_ac_power()
            for win in self._windows.values():
                if getattr(win, "is_visible", lambda: True)():
                    if not self._paused and power_ok:
                        win.play()
                    else:
                        win.pause()
                else:
                    win.pause()
        target = _OcclusionTarget(check)
        self._occlusion_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, target, "tick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(
            self._occlusion_timer, NSDefaultRunLoopMode
        )

    def stop(self):
        if self._observer is not None:
            NSNotificationCenter.defaultCenter().removeObserver_(self._observer)
            self._observer = None
        if self._occlusion_timer is not None:
            self._occlusion_timer.invalidate()
            self._occlusion_timer = None
        for w in self._windows.values():
            w.orderOut_(None)
            w.close()
        self._windows.clear()

    def _rebuild_windows(self):
        screens = _unique_screens()
        current_indices = set()
        for i, screen in enumerate(screens):
            current_indices.add(i)
            if i in self._windows:
                win = self._windows[i]
                win.updateFrame()
                continue
            path = storage.get_path_for_screen(i)
            scale = storage.get_scale_mode(i)
            win = WallpaperWindow.alloc().initWithScreen_videoPath_scaleMode_(
                screen, path, scale
            )
            win.orderFrontRegardless()
            if self._paused or (storage.get_power_connected_only() and not power_source.is_on_ac_power()):
                win.pause()
            self._windows[i] = win
        # Remove windows for disconnected screens
        for idx in list(self._windows.keys()):
            if idx not in current_indices:
                self._windows[idx].orderOut_(None)
                self._windows[idx].close()
                del self._windows[idx]

    def set_wallpaper(self, screen_index: int, path: Optional[str]):
        storage.set_path_for_screen(screen_index, path)
        if screen_index in self._windows:
            self._windows[screen_index].setVideoPath_(path or "")
            power_ok = not storage.get_power_connected_only() or power_source.is_on_ac_power()
            if path and not self._paused and power_ok:
                self._windows[screen_index].play()
        else:
            self._rebuild_windows()

    def set_scale_mode(self, screen_index: int, mode: str):
        storage.set_scale_mode(screen_index, mode)
        if screen_index in self._windows:
            self._windows[screen_index].setScaleMode_(mode)

    def pause_all(self):
        self._paused = True
        for w in self._windows.values():
            w.pause()

    def resume_all(self):
        self._paused = False
        power_ok = not storage.get_power_connected_only() or power_source.is_on_ac_power()
        if power_ok:
            for w in self._windows.values():
                w.play()
        else:
            for w in self._windows.values():
                w.pause()

    def is_paused(self) -> bool:
        return self._paused

    def get_screens(self) -> List[Tuple[int, object, str]]:
        """Return list of (index, NSScreen, display_name), one entry per physical display."""
        screens = _unique_screens()
        return [(i, screen, _display_name_for_screen(screen, i)) for i, screen in enumerate(screens)]

    def apply_power_setting(self) -> None:
        """Apply power-connected-only setting immediately (pause/play based on AC and preference)."""
        power_ok = not storage.get_power_connected_only() or power_source.is_on_ac_power()
        if self._paused or not power_ok:
            for w in self._windows.values():
                w.pause()
        else:
            for win in self._windows.values():
                if getattr(win, "is_visible", lambda: True)():
                    win.play()
                else:
                    win.pause()


class _OcclusionTarget:
    def __init__(self, callback):
        self._callback = callback

    def tick_(self, timer):
        self._callback(timer)
