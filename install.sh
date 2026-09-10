#!/bin/bash

set -e

INSTALL_DIR="$HOME/dripfetch"
VENV_DIR="$INSTALL_DIR/.venv"
BIN_DIR="$HOME/.local/bin"
BIN_PATH="$BIN_DIR/dripfetch"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing DripFetch..."

mkdir -p "$INSTALL_DIR"
python3 -m venv "$VENV_DIR"

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install "$PROJECT_DIR"

mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/dripfetch" "$BIN_PATH"

case "$(basename "$SHELL")" in
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    bash)
        if [ "$(uname)" = "Darwin" ]; then
            SHELL_RC="$HOME/.bash_profile"
        else
            SHELL_RC="$HOME/.bashrc"
        fi
        ;;
    *)
        SHELL_RC=""
        ;;
esac

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    export PATH="$BIN_DIR:$PATH"

    if [ -n "$SHELL_RC" ] && ! grep -Fxq 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_RC" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    fi
fi

echo
echo "DripFetch installed."
echo
echo "Application: $INSTALL_DIR"
echo "Virtual environment: $VENV_DIR"
echo "Command: $BIN_PATH"
echo "Configuration: $HOME/.config/dripfetch/config.yaml"
echo
echo "Run: dripfetch"