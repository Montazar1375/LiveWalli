#!/bin/bash
# Run LiveWalli from Terminal (has full disk access). Used by LiveWalli.app.
cd "$(dirname "$0")" || exit 1
LOG="$(pwd)/livewalli_launch.log"

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

# Run in background and detach so we can close Terminal; log output
nohup "$PYTHON" main.py >> "$LOG" 2>&1 &
disown
exit 0
