#!/usr/bin/env python3
"""
Post-build script: remove unused Qt components from LiveWalli.app to get under 200MB.
Run after: python setup.py py2app
"""
import os
import shutil
import sys

APP = "dist/LiveWalli.app"
RESOURCES = os.path.join(APP, "Contents", "Resources")
PYSIDE = os.path.join(RESOURCES, "lib", "python3.9", "PySide6")
QT_LIB = os.path.join(PYSIDE, "Qt", "lib")
QT_QML = os.path.join(PYSIDE, "Qt", "qml")

# Heavy frameworks we don't use (widgets app: Core, Gui, Widgets, + optional Multimedia)
REMOVE_FRAMEWORKS = [
    "QtWebEngineCore.framework",   # ~576 MB
    "QtPdf.framework",
    "QtQuick.framework",
    "QtQml.framework",
    "QtShaderTools.framework",
    "QtDesigner.framework",
    "QtDesignerComponents.framework",
    "QtQuick3D.framework",
    "QtQuick3DRuntimeRender.framework",
    "Qt3DRender.framework",
    "QtGraphs.framework",
    "QtCharts.framework",
    "QtDataVisualization.framework",
    "QtLocation.framework",
    "QtQmlCompiler.framework",
    "QtWebEngineQuick.framework",
    "QtSpatialAudio.framework",
    "QtRemoteObjects.framework",
    "QtUiTools.framework",
    "QtQuickDialogs2QuickImpl.framework",
    "QtQuickControls2Imagine.framework",
    "QtQuickControls2Material.framework",
    "QtQuickControls2Basic.framework",
    "QtQuickControls2Universal.framework",
    "QtQuickControls2Fusion.framework",
    "QtQuickTemplates2.framework",
]
# Python modules (.abi3.so + .pyi) we don't use
REMOVE_MODULES = [
    "QtWebEngineCore", "QtWebEngine", "QtWebEngineWidgets", "QtWebEngineQuick",
    "Qt3DCore", "Qt3DRender", "Qt3DInput", "Qt3DLogic", "Qt3DAnimation", "Qt3DExtras",
    "QtQuick", "QtQuick3D", "QtQml", "QtCharts", "QtGraphs", "QtGraphsWidgets",
    "QtDataVisualization", "QtPdf", "QtPdfWidgets", "QtDesigner", "QtHelp",
    "QtSpatialAudio", "QtRemoteObjects", "QtScxml", "QtNetworkAuth", "QtNfc",
    "QtPositioning", "QtLocation", "QtSerialPort", "QtSerialBus", "QtSensors",
    "QtStateMachine", "QtTextToSpeech", "QtHttpServer", "QtWebSockets", "QtWebChannel",
    "QtWebView", "QtBluetooth", "QtUiTools", "QtSql", "QtPrintSupport", "QtXml",
    "QtQuickWidgets", "QtQuickTest", "QtQuickControls2", "QtDBus", "QtConcurrent",
]
# Top-level PySide6 dirs to remove
REMOVE_DIRS = [
    "Assistant.app", "Designer.app", "Linguist.app", "qmlls", "qmlformat", "qsb",
    "qmllint", "lrelease", "lupdate", "svgtoqml", "balsam", "balsamui", "doc",
    "scripts", "support", "typesystems", "include",
]

def rm(path, kind="path"):
    if os.path.exists(path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"  removed {kind}: {path}")
        except Exception as e:
            print(f"  WARN: could not remove {path}: {e}", file=sys.stderr)

def main():
    if not os.path.isdir(RESOURCES):
        print(f"Not found: {RESOURCES}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(PYSIDE):
        print(f"Not found: {PYSIDE}", file=sys.stderr)
        sys.exit(1)

    print("Trimming LiveWalli.app ...")
    # Remove heavy Qt frameworks
    for name in REMOVE_FRAMEWORKS:
        rm(os.path.join(QT_LIB, name), "framework")
    # Remove entire QML (we use widgets only)
    rm(QT_QML, "qml")
    # Remove unused .abi3.so and .pyi
    for mod in REMOVE_MODULES:
        for ext in (".abi3.so", ".pyi"):
            rm(os.path.join(PYSIDE, mod + ext), "module")
    # Remove top-level PySide6 dirs
    for name in REMOVE_DIRS:
        rm(os.path.join(PYSIDE, name), "dir")

    # Phase 2: In Qt/lib keep only what we need; remove everything else
    # QtDBus is required by QtGui on macOS. We drop QtMultimedia to get under 200MB (manager shows "Preview N/A").
    KEEP_FRAMEWORKS = {
        "QtCore.framework", "QtGui.framework", "QtWidgets.framework",
        "QtNetwork.framework", "QtOpenGL.framework", "QtSvg.framework", "QtDBus.framework",
    }
    if os.path.isdir(QT_LIB):
        for name in os.listdir(QT_LIB):
            path = os.path.join(QT_LIB, name)
            if os.path.isdir(path) and name.endswith(".framework"):
                if name not in KEEP_FRAMEWORKS:
                    rm(path, "framework")
            elif os.path.isfile(path) and (name.startswith("libav") or name.startswith("libsw")):
                rm(path, "dylib")  # ffmpeg: only needed for QtMultimedia
            elif os.path.isfile(path) and name.endswith(".dylib"):
                if "libpyside" not in name and "libshiboken" not in name:
                    rm(path, "dylib")
    # Remove QtMultimedia Python modules so app doesn't try to load missing frameworks
    for mod in ("QtMultimedia", "QtMultimediaWidgets"):
        for ext in (".abi3.so", ".pyi"):
            rm(os.path.join(PYSIDE, mod + ext), "module")

    # Phase 2: In Qt/plugins keep only platforms, styles, imageformats, multimedia
    QT_PLUGINS = os.path.join(PYSIDE, "Qt", "plugins")
    KEEP_PLUGINS = {"platforms", "styles", "imageformats", "multimedia"}
    if os.path.isdir(QT_PLUGINS):
        for name in os.listdir(QT_PLUGINS):
            if name not in KEEP_PLUGINS:
                rm(os.path.join(QT_PLUGINS, name), "plugin")

    # Remove translations (saves ~16 MB)
    rm(os.path.join(PYSIDE, "Qt", "translations"), "translations")

    print("Trim done.")

if __name__ == "__main__":
    main()
