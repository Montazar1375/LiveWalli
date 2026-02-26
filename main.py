#!/usr/bin/env python3
"""
LiveWalli — macOS Live Wallpaper Engine.
Menu bar app (no Dock icon). Manages video wallpapers per monitor.
"""
# Hide from Dock as early as possible (before any other imports that might activate the app)
import AppKit
_nsapp = AppKit.NSApplication.sharedApplication()
_nsapp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSTimer,
    NSRunLoop,
    NSDefaultRunLoopMode,
)

from livewalli.screen_manager import ScreenManager
from livewalli.menu_bar import MenuBarController
from livewalli.manager_ui import show_manager, process_qt_events


class QtEventPump:
    """Target for NSTimer to process Qt events so Manager window stays responsive."""

    def qtPump_(self, _):
        process_qt_events()


def main():
    nsapp = NSApplication.sharedApplication()

    screen_manager = ScreenManager()
    screen_manager.start()

    def on_manage():
        show_manager(screen_manager)

    def on_pause_toggle():
        if screen_manager.is_paused():
            screen_manager.resume_all()
        else:
            screen_manager.pause_all()
        menu_controller.refresh_pause_label()

    def on_settings():
        show_manager(screen_manager)

    menu_controller = MenuBarController(
        on_manage=on_manage,
        on_pause_toggle=on_pause_toggle,
        on_settings=on_settings,
    )
    menu_controller.setup(is_paused_callback=screen_manager.is_paused)

    # Pump Qt events periodically so Manager window works while Cocoa run loop is active
    pump = QtEventPump()
    pump_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        0.03, pump, "qtPump:", None, True
    )
    NSRunLoop.currentRunLoop().addTimer_forMode_(pump_timer, NSDefaultRunLoopMode)

    # Ensure we stay out of the Dock (can be reset by some frameworks)
    nsapp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    nsapp.activateIgnoringOtherApps_(True)
    nsapp.run()


if __name__ == "__main__":
    main()
