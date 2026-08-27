#!/bin/bash
# ==============================================================================
# Dell G15 5520 Fan & Thermal Controller - Installation Script
# Installs desktop launcher, application icons, and CLI symlink.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[*] Setting file execution permissions..."
chmod +x "$SCRIPT_DIR/main.py"
chmod +x "$SCRIPT_DIR/dell_g15_fan_cli.py"
chmod +x "$SCRIPT_DIR/dell_g15_fan_gui.py"
chmod +x "$SCRIPT_DIR/setup_permissions.sh"

echo "[*] Installing CLI symlink to ~/.local/bin/dell-g15-fan..."
mkdir -p "$HOME/.local/bin"
ln -sf "$SCRIPT_DIR/main.py" "$HOME/.local/bin/dell-g15-fan"

echo "[*] Installing Desktop Application Launcher..."
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"

cp "$SCRIPT_DIR/assets/icon.png" "$HOME/.local/share/icons/hicolor/256x256/apps/dell-g15-fan.png"
cp "$SCRIPT_DIR/dell-g15-fan.desktop" "$HOME/.local/share/applications/dell-g15-fan.desktop"
chmod +x "$HOME/.local/share/applications/dell-g15-fan.desktop"

# Update desktop database if available
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo ""
echo "=========================================================================="
echo "✓ Installation Complete!"
echo "• Launch GUI from Terminal    : dell-g15-fan (or ./main.py)"
echo "• Launch CLI Commands         : dell-g15-fan --status"
echo "• Application Menu Shortcut   : 'Dell G15 Fan Command Center' in App Launcher"
echo "• Setup Sysfs Permissions     : sudo ./setup_permissions.sh"
echo "=========================================================================="
