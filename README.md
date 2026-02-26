# LiveWalli

macOS live wallpaper engine: video wallpapers per monitor, menu bar control, no Dock icon.

## Requirements

- macOS 10.13+
- Python 3.9+ (3.12+ recommended)
- M-series or Intel Mac

## Install

```bash
cd LiveWalli
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

**From Terminal (uses .venv if present):**
```bash
python3 main.py
```

**Double‑click LiveWalli.app** (in the project folder): uses system Python to avoid macOS permission errors. Install dependencies for system Python once:
```bash
pip3 install --user -r requirements.txt
```

If the **Python icon still appears in the Dock**, the system is showing the interpreter. To run with no Dock icon, use an app wrapper:

1. Open **Automator** → New Document → **Application**.
2. Add action **Run Shell Script**; set “Pass input” to **to stdin**.
3. In the script box put (adjust paths to your setup):
   ```bash
   cd /path/to/LiveWalli
   ./.venv/bin/python main.py
   ```
4. Save as **LiveWalli.app** (e.g. in the LiveWalli folder).
5. Hide its Dock icon (run once, replace `…` with the path to your `.app`):
   ```bash
   /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "…/LiveWalli.app/Contents/Info.plist"
   ```
   If you get “Key already exists”, use `Set` instead of `Add`.
6. Open **LiveWalli.app**; only the menu bar icon will show.

- **Menu bar**: Click the circle icon for **Manage Wallpapers**, **Pause All** / **Resume All**, **Settings**, **Quit**.
- **Manage Wallpapers**: Opens a window with one card per monitor. Drag-and-drop `.mp4` or `.mov` onto a card, or click to browse. Use **Scale** (Fill / Fit / Stretch) and **Clear** per monitor.
- **Pause All**: Pauses video on all screens; use **Resume All** to start again.
- The app does not appear in the Dock (menu bar only). When the desktop is covered by a full-screen app, playback is paused to save energy.

## Config

Wallpaper paths and scale modes are stored in `~/.config/livewalli/wallpapers.json`.

## Build a standalone app (no Python required)

To build a single **LiveWalli.app** that runs natively on any Mac without installing Python:

```bash
cd LiveWalli
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install py2app
python setup.py py2app
```

The app is created at **`dist/LiveWalli.app`**. You can move it to Applications or anywhere. It bundles Python and all dependencies, so other Macs do not need Python installed. The app uses **LSUIElement** (no Dock icon).

### Why is the app so large (~1.2 GB)? Dependency bloat

py2app copies whatever is in your Python environment. **Full PySide6** ships QtWebEngine (Chromium), Qt3D, QtCharts, QtGraphs, VirtualKeyboard, and QML styles for every platform (like including every Material library and emoji set in one APK). The app only needs QtCore, QtGui, QtWidgets (and optionally QtMultimedia for in-window preview).

**setup.py** now has **hard excludes** for the fat: Qt3D*, QtWebEngine*, QtCharts, QtGraphs, QtDataVisualization, QtVirtualKeyboard, QtQuick*, QtQml, and other unused modules. You still get the smallest result by building from a **clean env** so py2app never sees those packages.

### Building a smaller app (target: under 200 MB)

**Option A – Clean venv + minimal PySide6 (recommended, keeps video preview in manager)**

1. **Use a clean virtual environment** so only LiveWalli’s dependencies are installed (no numpy, pandas, or full Qt from elsewhere).

2. **Use only the pyobjc frameworks the app needs** (Cocoa, Quartz, AVFoundation, CoreMedia); the app no longer requires PyObjCTools.

3. **setup.py** excludes heavy modules (numpy, pandas, QtWebEngine, Qt3D, QtQml, etc.) so they are not bundled even if present in the env.

**Commands:**

```bash
cd LiveWalli
python3 -m venv clean_env
source clean_env/bin/activate
pip install -r requirements-build.txt
pip install py2app
python setup.py py2app
```

Result: **`dist/LiveWalli.app`** will still be large (~1 GB) because py2app copies the full PySide6 tree. **To get under 200 MB**, run the trim script after building:

```bash
python setup.py py2app
python trim_app_bundle.py
```

**`trim_app_bundle.py`** removes unused Qt frameworks (WebEngine, 3D, QML, Charts, etc.), keeps only Core/Gui/Widgets/Network/DBus/Svg/OpenGL, and drops QtMultimedia so the bundle stays under 200 MB. The manager window will show **"Preview N/A"** for video thumbnails; wallpaper playback is unchanged. Final size is typically **~160 MB**.

**Option B – Smallest possible: PySide6-Essentials (no in-window video preview)**

For the smallest bundle, use PySide6-Essentials so 3D/WebEngine/add-ons are never installed. The manager window will show "Preview N/A" for video thumbnails; wallpaper playback is unchanged.

```bash
cd LiveWalli
rm -rf clean_env
python3 -m venv clean_env
source clean_env/bin/activate
pip install PySide6-Essentials pyobjc-framework-Cocoa pyobjc-framework-Quartz pyobjc-framework-AVFoundation pyobjc-framework-CoreMedia
pip install py2app
python setup.py py2app
```

**If the .app is still large:** PySide6 may have copied QML/style folders for all platforms. After building, you can manually delete from inside the bundle, e.g.:

```bash
APP=dist/LiveWalli.app
# List dirs first: ls "$APP/Contents/Resources/lib/python3."*/PySide6/Qt/qml
rm -rf "$APP/Contents/Resources/lib/python3."*/PySide6/Qt/qml/QtQuick3D" 2>/dev/null
rm -rf "$APP/Contents/Resources/lib/python3."*/PySide6/Qt/qml/QtVirtualKeyboard" 2>/dev/null
```

### If the built app won’t run

Run it from Terminal to see the error:

```bash
/path/to/LiveWalli.app/Contents/MacOS/LiveWalli
```

(or drag the **LiveWalli** executable from `LiveWalli.app/Contents/MacOS/` into Terminal). Any Python traceback or missing-module error will appear there.

### Optional: Nuitka for even smaller size

[Nuitka](https://nuitka.net/) compiles Python to native code instead of bundling the interpreter. Can yield a smaller and faster binary:

```bash
pip install nuitka
python -m nuitka --standalone --macos-create-app-bundle --enable-plugin=pyside6 main.py
```
