#!/bin/bash

set -e

INSTALL_DIR="$HOME/dripfetch"
VENV_DIR="$INSTALL_DIR/.venv"
BIN_PATH="$HOME/.local/bin/dripfetch"

echo "Uninstalling DripFetch..."

if [ -L "$BIN_PATH" ] || [ -e "$BIN_PATH" ]; then
    rm -f "$BIN_PATH"
    echo "Removed: $BIN_PATH"
fi

if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
    echo "Removed: $VENV_DIR"
fi

for path in \
    "$INSTALL_DIR/build" \
    "$INSTALL_DIR/dist" \
    "$INSTALL_DIR/dripfetch.egg-info"
do
    if [ -e "$path" ]; then
        rm -rf "$path"
        echo "Removed: $path"
    fi
done

find "$INSTALL_DIR" \
    -type d \
    -name "__pycache__" \
    -prune \
    -exec rm -rf {} +

echo
echo "DripFetch has been uninstalled."
echo
echo "Preserved:"
echo "Application source: $INSTALL_DIR"
echo "Configuration: $HOME/.config/dripfetch/config.yaml"