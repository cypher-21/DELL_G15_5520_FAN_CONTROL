#!/bin/bash
# ==============================================================================
# Dell G15 5520 Fan & Thermal Controller - Clean Uninstaller Script
# Removes all user symlinks, desktop entries, icons, systemd units, and udev rules.
# ==============================================================================

set -e

echo "[*] Stopping and disabling systemd user services..."
systemctl --user stop dell-g15-fan.service 2>/dev/null || true
systemctl --user disable dell-g15-fan.service 2>/dev/null || true

echo "[*] Removing user files..."
rm -f "$HOME/.local/bin/dell-g15-fan"
rm -f "$HOME/.local/share/applications/dell-g15-fan.desktop"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/dell-g15-fan.png"
rm -f "$HOME/.config/systemd/user/dell-g15-fan.service"

# Reload user systemd daemon
systemctl --user daemon-reload 2>/dev/null || true

# Update desktop database
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# Check for system-level udev rules
if [ -f "/etc/udev/rules.d/99-dell-g15-fan.rules" ]; then
    echo "[*] Removing udev rules (requires sudo)..."
    sudo rm -f "/etc/udev/rules.d/99-dell-g15-fan.rules"
    sudo udevadm control --reload-rules 2>/dev/null || true
fi

echo ""
echo "=========================================================================="
echo "[OK] Dell G15 Fan Command Center has been completely removed."
echo "=========================================================================="
