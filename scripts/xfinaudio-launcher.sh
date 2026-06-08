#!/bin/bash
# XfinAudio macOS launcher — runs the app with process name "XfinAudio"
# so the system menu bar shows the correct label.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    echo "Python not found at $PYTHON — run 'uv sync' first."
    exit 1
fi
# Create a temporary symlink named XfinAudio pointing to the python binary.
# macOS reads the executable name from the filesystem for the app menu label.
TMP_DIR=$(mktemp -d)
ln -sf "$PYTHON" "$TMP_DIR/XfinAudio"
export PYTHONPATH="$REPO_ROOT/src:$PYTHONPATH"
"$TMP_DIR/XfinAudio" -m xfinaudio.desktop.app "$@"
rm -rf "$TMP_DIR"
