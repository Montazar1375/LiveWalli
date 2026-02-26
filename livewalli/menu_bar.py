"""Menu bar status item with circle icon and menu (Manage, Pause, Settings, Quit)."""
from AppKit import (
    NSStatusBar,
    NSVariableStatusItemLength,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSApplication,
    NSBezierPath,
    NSColor,
)
from Foundation import NSMakeRect


def _make_circle_icon(size=18):
    """Create a small template image of a circle for the status bar."""
    img = NSImage.alloc().initWithSize_((size, size))
    img.setTemplate_(True)
    img.lockFocus()
    try:
        path = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(1, 1, size - 2, size - 2))
        NSColor.whiteColor().set()
        path.fill()
    finally:
        img.unlockFocus()
    return img


class MenuBarController:
    def __init__(self, on_manage=None, on_pause_toggle=None, on_settings=None):
        self._on_manage = on_manage
        self._on_pause_toggle = on_pause_toggle
        self._on_settings = on_settings
        self._status_item = None
        self._pause_item = None

    def setup(self, is_paused_callback=None):
        """Create status bar item and menu. is_pause_callback() -> bool for Pause label."""
        self._is_paused = is_paused_callback or (lambda: False)
        bar = NSStatusBar.systemStatusBar()
        self._status_item = bar.statusItemWithLength_(NSVariableStatusItemLength)
        self._status_item.setImage_(_make_circle_icon())
        self._status_item.setMenu_(self._build_menu())
        self._update_pause_label()

    def _build_menu(self):
        menu = NSMenu.alloc().init()
        manage = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Manage Wallpapers", "manageWallpapers:", ""
        )
        manage.setTarget_(self)
        menu.addItem_(manage)

        self._pause_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Pause All", "pauseToggle:", ""
        )
        self._pause_item.setTarget_(self)
        menu.addItem_(self._pause_item)

        settings = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings", "openSettings:", ""
        )
        settings.setTarget_(self)
        menu.addItem_(settings)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit LiveWalli", "quit:", ""
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)
        return menu

    def _update_pause_label(self):
        if self._pause_item is not None:
            self._pause_item.setTitle_("Resume All" if self._is_paused() else "Pause All")

    def manageWallpapers_(self, sender):
        if self._on_manage:
            self._on_manage()

    def pauseToggle_(self, sender):
        if self._on_pause_toggle:
            self._on_pause_toggle()
        self._update_pause_label()

    def openSettings_(self, sender):
        if self._on_settings:
            self._on_settings()

    def quit_(self, sender):
        NSApplication.sharedApplication().terminate_(None)

    def refresh_pause_label(self):
        self._update_pause_label()
