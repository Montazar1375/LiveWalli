"""PySide6 Management UI: one card per monitor, display name, scale, Clear, Recent, preview."""
import os
from typing import Optional, List, Callable

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QPushButton,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent

try:
    from PySide6.QtMultimedia import QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAS_QT_VIDEO = True
except ImportError:
    HAS_QT_VIDEO = False

from . import storage
from . import login_item
from . import codec

ALLOWED_EXT = tuple(codec.ALLOWED_EXTENSIONS)


def _can_accept(path: str) -> bool:
    return codec.is_allowed_extension(path)


# Scale options: label -> storage value
SCALE_OPTIONS = [
    ("Fill", "fill"),
    ("Fit", "fit"),
    ("Stretch", "stretch"),
    ("Center", "center"),
]


class VideoPreviewWidget(QFrame):
    """Small video preview that loops when given a path. Uses QMediaPlayer + QVideoWidget if available."""

    def __init__(self, width: int = 160, height: int = 90, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setStyleSheet("VideoPreviewWidget { background: #1a1a1c; border: 1px solid #333; }")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._path: Optional[str] = None
        self._player = None
        self._video_widget = None
        self._no_preview_label = QLabel("No video")
        self._no_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_preview_label.setStyleSheet("color: #555; font-size: 11px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._no_preview_label)
        if HAS_QT_VIDEO:
            self._video_widget = QVideoWidget(self)
            self._video_widget.setStyleSheet("background: #1a1a1c;")
            self._video_widget.setMinimumSize(1, 1)
            layout.addWidget(self._video_widget)
            self._video_widget.hide()
            self._player = QMediaPlayer(self)
            self._player.setVideoOutput(self._video_widget)
            self._player.setAudioOutput(None)
            self._player.playbackStateChanged.connect(self._on_state_changed)
            self._player.setLoops(-1)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState and self._player.error() != QMediaPlayer.Error.NoError:
            self._no_preview_label.setText("Preview failed")
            self._no_preview_label.show()
            if self._video_widget:
                self._video_widget.hide()

    def set_path(self, path: Optional[str]) -> None:
        if path == self._path:
            return
        self._path = path
        if not path or not HAS_QT_VIDEO or not self._player:
            self._no_preview_label.setText("No video" if not path else "Preview N/A")
            self._no_preview_label.show()
            if self._video_widget:
                self._video_widget.hide()
            return
        self._player.stop()
        self._no_preview_label.setText("Loading…")
        self._no_preview_label.show()
        if self._video_widget:
            self._video_widget.hide()
        url = QUrl.fromLocalFile(path)
        self._player.setSource(url)
        self._player.play()
        self._no_preview_label.hide()
        self._video_widget.show()

    def clear(self) -> None:
        self.set_path(None)
        if self._player:
            self._player.stop()
            self._player.setSource(QUrl())


class MonitorSquare(QFrame):
    """One card per monitor: display name, resolution, preview, drop zone, scale, Clear, Recent."""

    SIZE = 160
    PREVIEW_SIZE = (160, 90)

    def __init__(
        self,
        screen_index: int,
        monitor_name: str,
        resolution: str,
        on_set_wallpaper: Optional[Callable[[int, Optional[str]], None]] = None,
        on_set_scale: Optional[Callable[[int, str], None]] = None,
        on_clear: Optional[Callable[[int], None]] = None,
        refresh_recent: Optional[Callable[[], None]] = None,
    ):
        super().__init__()
        self._screen_index = screen_index
        self._on_set_wallpaper = on_set_wallpaper
        self._on_set_scale = on_set_scale
        self._on_clear = on_clear
        self._refresh_recent = refresh_recent
        self.setAcceptDrops(True)
        self.setFixedSize(self.SIZE, self.SIZE + 120)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setStyleSheet(
            "MonitorSquare { background: #2a2a2e; border: 1px solid #444; "
            "color: #ccc; font-size: 12px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        # Monitor name (display name)
        self._title = QLabel(monitor_name)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("font-weight: bold; color: #eee;")
        self._title.setWordWrap(True)
        layout.addWidget(self._title)
        self._resolution = QLabel(resolution)
        self._resolution.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._resolution.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(self._resolution)
        # Preview
        self._preview = VideoPreviewWidget(self.PREVIEW_SIZE[0], self.PREVIEW_SIZE[1], self)
        layout.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignHCenter)
        # Hint
        self._hint = QLabel("Drop video or click")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self._hint)
        # Scale dropdown
        self._scale_combo = QComboBox()
        for label, mode in SCALE_OPTIONS:
            self._scale_combo.addItem(label, mode)
        current = storage.get_scale_mode(screen_index)
        idx = self._scale_combo.findData(current)
        if idx >= 0:
            self._scale_combo.setCurrentIndex(idx)
        self._scale_combo.currentIndexChanged.connect(self._scale_changed)
        self._scale_combo.setStyleSheet(
            "QComboBox { background: #3a3a3c; color: #fff; border: 1px solid #555; "
            "border-radius: 4px; padding: 4px 8px; min-width: 80px; }"
        )
        layout.addWidget(self._scale_combo)
        # Clear button
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setStyleSheet(
            "QPushButton { background: #4a2a2a; color: #e88; border: 1px solid #666; "
            "border-radius: 4px; padding: 4px 8px; } "
            "QPushButton:hover { background: #5a3333; } "
            "QPushButton:disabled { color: #666; }"
        )
        self._clear_btn.clicked.connect(self._do_clear)
        layout.addWidget(self._clear_btn)
        self._update_hint(storage.get_path_for_screen(screen_index))
        self._update_preview_and_clear_state()

    def _update_hint(self, path: Optional[str]):
        if path:
            self._hint.setText(os.path.basename(path)[:20] + ("…" if len(os.path.basename(path)) > 20 else ""))
        else:
            self._hint.setText("Drop video or click")

    def _update_preview_and_clear_state(self):
        path = storage.get_path_for_screen(self._screen_index)
        self._preview.set_path(path)
        self._clear_btn.setEnabled(bool(path))

    def _scale_changed(self, index: int):
        mode = self._scale_combo.currentData()
        if mode and self._on_set_scale:
            self._on_set_scale(self._screen_index, mode)
        if mode:
            storage.set_scale_mode(self._screen_index, mode)

    def _do_clear(self):
        if self._on_clear:
            self._on_clear(self._screen_index)
        self._update_hint(None)
        self._update_preview_and_clear_state()

    def _apply_path(self, path: Optional[str], from_drop_or_picker: bool = False):
        if from_drop_or_picker and path:
            ok, err = codec.check_playable(path)
            if not ok:
                QMessageBox.warning(self, "LiveWalli", err or "Unsupported format.")
                return
            storage.add_recent_path(path)
            if self._refresh_recent:
                self._refresh_recent()
        self._update_hint(path)
        if self._on_set_wallpaper:
            self._on_set_wallpaper(self._screen_index, path)
        self._update_preview_and_clear_state()

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls()
        if urls and _can_accept(urls[0].toLocalFile()):
            event.acceptProposedAction()
            self.setStyleSheet(
                "MonitorSquare { background: #1e3a5f; border: 2px solid #4a9eff; "
                "color: #ccc; font-size: 12px; }"
            )

    def dragLeaveEvent(self, event):
        self.setStyleSheet(
            "MonitorSquare { background: #2a2a2e; border: 1px solid #444; "
            "color: #ccc; font-size: 12px; }"
        )

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if _can_accept(path):
                self._apply_path(path, from_drop_or_picker=True)
        self.setStyleSheet(
            "MonitorSquare { background: #2a2a2e; border: 1px solid #444; "
            "color: #ccc; font-size: 12px; }"
        )

    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video Wallpaper", "", f"Video (*.mp4 *.mov);;All (*)"
        )
        if path:
            self._apply_path(path, from_drop_or_picker=True)

    def set_from_recent(self, path: str):
        """Set wallpaper from a recent path (no codec message if already in recent)."""
        self._apply_path(path, from_drop_or_picker=True)


class ManagerWindow(QMainWindow):
    """Management window: monitor cards, Recent list, scale, Clear, preview, codec handling."""

    def __init__(self, screen_manager, parent=None):
        super().__init__(parent)
        self._screen_manager = screen_manager
        self.setWindowTitle("LiveWalli")
        self.setMinimumSize(480, 400)
        self.setStyleSheet(
            "QMainWindow { background: #1c1c1e; } "
            "QLabel { color: #ccc; } "
            "QScrollArea { border: none; background: transparent; }"
        )
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        # Recent section (above cards)
        recent_label = QLabel("Recent (click to set on first monitor)")
        recent_label.setStyleSheet("font-weight: bold; color: #aaa; margin-top: 4px;")
        layout.addWidget(recent_label)
        self._recent_layout = QVBoxLayout()
        recent_inner = QWidget()
        recent_inner.setLayout(self._recent_layout)
        layout.addWidget(recent_inner)
        self._refresh_recent_buttons()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        self._grid = QGridLayout(scroll_content)
        self._grid.setSpacing(16)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        # Run only when power connected
        self._power_cb = QCheckBox("Run only when power connected")
        self._power_cb.setStyleSheet("QCheckBox { color: #ccc; } QCheckBox::indicator { width: 16px; height: 16px; }")
        self._power_cb.setToolTip("Pause wallpapers when on battery.")
        self._power_cb.stateChanged.connect(self._on_power_toggled)
        layout.addWidget(self._power_cb)
        # Start at login
        self._login_cb = QCheckBox("Start LiveWalli at login")
        self._login_cb.setStyleSheet("QCheckBox { color: #ccc; } QCheckBox::indicator { width: 16px; height: 16px; }")
        self._login_cb.stateChanged.connect(self._on_login_toggled)
        if not login_item.can_use_login_item():
            self._login_cb.setEnabled(False)
            self._login_cb.setToolTip("Place LiveWalli.app in the project folder to enable start at login.")
        layout.addWidget(self._login_cb)
        self._card_widgets: List[QWidget] = []
        self._squares: List[MonitorSquare] = []
        self._refresh_cards()
        self._update_login_checkbox()
        self._update_power_checkbox()

    def _refresh_recent_buttons(self):
        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        recent = storage.get_recent_paths()
        if not recent:
            return
        for path in recent[:5]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(6)
            btn = QPushButton(os.path.basename(path)[:40] + ("…" if len(os.path.basename(path)) > 40 else ""))
            btn.setToolTip(path)
            btn.setStyleSheet(
                "QPushButton { background: #3a3a3c; color: #ccc; border: 1px solid #555; "
                "border-radius: 4px; padding: 4px 8px; text-align: left; } "
                "QPushButton:hover { background: #454548; }"
            )
            btn.clicked.connect(lambda checked=False, p=path: self._apply_recent_to_first_or_focused(p))
            row_layout.addWidget(btn, 1)
            remove_btn = QPushButton("×")
            remove_btn.setFixedSize(24, 24)
            remove_btn.setToolTip("Remove from recent")
            remove_btn.setStyleSheet(
                "QPushButton { background: #3a3a3c; color: #888; border: 1px solid #555; "
                "border-radius: 4px; font-size: 14px; font-weight: bold; } "
                "QPushButton:hover { background: #4a2a2a; color: #e88; }"
            )
            remove_btn.clicked.connect(lambda checked=False, p=path: self._remove_recent(p))
            row_layout.addWidget(remove_btn, 0)
            self._recent_layout.addWidget(row)

    def _remove_recent(self, path: str) -> None:
        storage.remove_recent_path(path)
        self._refresh_recent_buttons()

    def _apply_recent_to_first_or_focused(self, path: str):
        if self._squares:
            self._squares[0].set_from_recent(path)

    def _refresh_cards(self):
        for w in self._card_widgets:
            w.deleteLater()
        self._card_widgets.clear()
        self._squares.clear()
        screens = self._screen_manager.get_screens()
        if not screens:
            label = QLabel("No monitors detected")
            label.setStyleSheet("color: #888;")
            self._grid.addWidget(label, 0, 0)
            return
        cols = 2
        for i, (idx, screen, display_name) in enumerate(screens):
            frame = screen.frame()
            resolution = f"{int(frame.size.width)} × {int(frame.size.height)}"
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(6)
            square = MonitorSquare(
                idx,
                display_name,
                resolution,
                on_set_wallpaper=self._on_set_wallpaper,
                on_set_scale=self._on_set_scale,
                on_clear=self._on_clear,
                refresh_recent=self._refresh_recent_buttons,
            )
            cell_layout.addWidget(square, 0, Qt.AlignmentFlag.AlignHCenter)
            row, col = i // cols, i % cols
            self._grid.addWidget(cell, row, col, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            self._card_widgets.append(cell)
            self._squares.append(square)

    def _on_set_wallpaper(self, screen_index: int, path: Optional[str]):
        self._screen_manager.set_wallpaper(screen_index, path)

    def _on_set_scale(self, screen_index: int, mode: str):
        self._screen_manager.set_scale_mode(screen_index, mode)

    def _on_clear(self, screen_index: int):
        self._screen_manager.set_wallpaper(screen_index, None)

    def _update_login_checkbox(self):
        self._login_cb.blockSignals(True)
        self._login_cb.setChecked(login_item.is_login_enabled())
        self._login_cb.blockSignals(False)

    def _on_login_toggled(self, state):
        enabled = state == Qt.CheckState.Checked.value
        if login_item.set_login_enabled(enabled):
            return
        self._update_login_checkbox()

    def _update_power_checkbox(self):
        self._power_cb.blockSignals(True)
        self._power_cb.setChecked(storage.get_power_connected_only())
        self._power_cb.blockSignals(False)

    def _on_power_toggled(self, state):
        enabled = state == Qt.CheckState.Checked.value
        storage.set_power_connected_only(enabled)
        self._screen_manager.apply_power_setting()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_cards()
        self._refresh_recent_buttons()
        self._update_login_checkbox()
        self._update_power_checkbox()


_qt_app = None
_manager_window = None


def get_qt_app():
    global _qt_app
    if _qt_app is None:
        _qt_app = QApplication.instance()
        if _qt_app is None:
            _qt_app = QApplication([])
    return _qt_app


def show_manager(screen_manager):
    """Show the manager window; create if needed."""
    global _manager_window
    get_qt_app()
    if _manager_window is None:
        _manager_window = ManagerWindow(screen_manager)
    _manager_window._refresh_cards()
    _manager_window._refresh_recent_buttons()
    _manager_window.show()
    _manager_window.raise_()
    _manager_window.activateWindow()


def process_qt_events():
    """Call from Cocoa run loop to process Qt events."""
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
