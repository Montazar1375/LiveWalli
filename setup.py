"""
py2app build script for LiveWalli.
Builds a standalone macOS .app with Python and dependencies bundled.

Usage:
    pip install py2app
    python setup.py py2app

Output:
    dist/LiveWalli.app  (standalone, no Python required on target Mac)
"""
from setuptools import setup

APP = ["main.py"]
DATA_FILES = []

# Merge our Info.plist with py2app defaults (LSUIElement = no Dock icon)
PLIST = {
    "CFBundleName": "LiveWalli",
    "CFBundleDisplayName": "LiveWalli",
    "CFBundleIdentifier": "com.livewalli.app",
    "CFBundleVersion": "1.0.0",
    "CFBundleShortVersionString": "1.0.0",
    "LSMinimumSystemVersion": "10.13",
    "LSUIElement": True,
    "NSHighResolutionCapable": True,
    "NSHumanReadableCopyright": "",
}

OPTIONS = {
    "argv_emulation": False,
    "plist": PLIST,
    "packages": [
        "livewalli",
        "PySide6",
        "shiboken6",
    ],
    "includes": [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    # Only bundle essential Qt plugins (no WebEngine, 3D, etc.)
    "qt_plugins": ["platforms", "styles"],
    # Hard excludes: don't bundle these even if on sys.path (saves ~1GB+)
    "excludes": [
        "tkinter",
        "unittest",
        "email",
        "http",
        "xmlrpc",
        "pydoc",
        "doctest",
        "numpy",
        "pandas",
        "matplotlib",
        "PIL",
        "cv2",
        # Qt WebEngine (Chromium-sized)
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        # Qt 3D (massive)
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DExtras",
        # QML / Quick (we use widgets only)
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQml",
        # Charts, graphs, data viz
        "PySide6.QtCharts",
        "PySide6.QtGraphs",
        "PySide6.QtGraphsWidgets",
        "PySide6.QtDataVisualization",
        # Virtual keyboard (touchscreens)
        "PySide6.QtVirtualKeyboard",
        # Other heavy/unused
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtSpatialAudio",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtNetworkAuth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtLocation",
        "PySide6.QtSerialPort",
        "PySide6.QtSerialBus",
        "PySide6.QtSensors",
        "PySide6.QtStateMachine",
        "PySide6.QtTextToSpeech",
        "PySide6.QtHttpServer",
        "PySide6.QtWebSockets",
        "PySide6.QtWebChannel",
        "PySide6.QtWebView",
        "PySide6.QtBluetooth",
        "PySide6.QtUiTools",
    ],
}

setup(
    name="LiveWalli",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
