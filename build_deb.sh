#!/bin/bash
# ==============================================================================
# Dell G15 5520 Fan & Thermal Controller - Debian Package Builder
# Builds a standalone .deb package for Debian, Ubuntu, Kali Linux, and Pop!_OS.
# ==============================================================================

set -e

PACKAGE_NAME="dell-g15-fan"
VERSION="2.0.0"
ARCH="all"
PKG_DIR="/tmp/${PACKAGE_NAME}_${VERSION}_${ARCH}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[*] Cleaning previous build artifacts..."
rm -rf "$PKG_DIR"
rm -f "$SCRIPT_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo "[*] Creating package directory tree..."
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/lib/$PACKAGE_NAME"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$PKG_DIR/usr/lib/systemd/user"
mkdir -p "$PKG_DIR/lib/udev/rules.d"
mkdir -p "$PKG_DIR/usr/share/doc/$PACKAGE_NAME"

echo "[*] Copying application files..."
cp "$SCRIPT_DIR/main.py" "$PKG_DIR/usr/lib/$PACKAGE_NAME/"
cp "$SCRIPT_DIR/dell_fan_backend.py" "$PKG_DIR/usr/lib/$PACKAGE_NAME/"
cp "$SCRIPT_DIR/dell_g15_fan_gui.py" "$PKG_DIR/usr/lib/$PACKAGE_NAME/"
cp "$SCRIPT_DIR/dell_g15_fan_cli.py" "$PKG_DIR/usr/lib/$PACKAGE_NAME/"
cp "$SCRIPT_DIR/fan_curve_engine.py" "$PKG_DIR/usr/lib/$PACKAGE_NAME/"

chmod 755 "$PKG_DIR/usr/lib/$PACKAGE_NAME/main.py"
chmod 755 "$PKG_DIR/usr/lib/$PACKAGE_NAME/dell_g15_fan_cli.py"

# Launcher symlink
ln -sf "/usr/lib/$PACKAGE_NAME/main.py" "$PKG_DIR/usr/bin/$PACKAGE_NAME"

# Desktop file
cat << EOF > "$PKG_DIR/usr/share/applications/$PACKAGE_NAME.desktop"
[Desktop Entry]
Name=Dell G15 Fan Command Center
GenericName=Fan & Thermal Controller
Comment=Monitor temperatures, control fan speeds, and toggle G-Mode Turbo on Dell G15 5520
Exec=/usr/bin/$PACKAGE_NAME
Icon=$PACKAGE_NAME
Terminal=false
Type=Application
Categories=System;Settings;HardwareSettings;Utility;
Keywords=dell;fan;thermal;g15;alienware;g-mode;turbo;cooling;
StartupNotify=true
EOF

# Icons
if [ -f "$SCRIPT_DIR/assets/icon.png" ]; then
    cp "$SCRIPT_DIR/assets/icon.png" "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/$PACKAGE_NAME.png"
fi

# Systemd User Unit
cat << EOF > "$PKG_DIR/usr/lib/systemd/user/$PACKAGE_NAME.service"
[Unit]
Description=Dell G15 5520 Thermal & Smart Fan Curve Background Daemon
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/$PACKAGE_NAME --daemon
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF

# Udev rules
cat << 'EOF' > "$PKG_DIR/lib/udev/rules.d/99-dell-g15-fan.rules"
# Udev rules for Dell G15 / Alienware Fan & Thermal Profile Control
SUBSYSTEM=="hwmon", ATTR{name}=="alienware_wmi", RUN+="/bin/chmod 0666 /sys/class/hwmon/%k/fan1_boost /sys/class/hwmon/%k/fan2_boost"
SUBSYSTEM=="platform-profile", RUN+="/bin/chmod 0666 /sys/class/platform-profile/%k/profile"
SUBSYSTEM=="powercap", RUN+="/bin/chmod -R 0444 /sys/class/powercap/intel-rapl*"
KERNEL=="platform_profile", SUBSYSTEM=="acpi", RUN+="/bin/chmod 0666 /sys/firmware/acpi/platform_profile"
EOF

# Documentation & License
cp "$SCRIPT_DIR/README.md" "$PKG_DIR/usr/share/doc/$PACKAGE_NAME/"
cp "$SCRIPT_DIR/LICENSE" "$PKG_DIR/usr/share/doc/$PACKAGE_NAME/copyright"

# Debian Control file
cat << EOF > "$PKG_DIR/DEBIAN/control"
Package: $PACKAGE_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: python3, python3-pyqt6, python3-psutil, libnotify-bin
Maintainer: Cypher <cypher@localhost>
Description: Hardware Fan & Thermal Controller Suite for Dell G15 5520
 High-performance Alienware/Dell G15 5520 fan control command center.
 Restores G-Mode Turbo (Fn + F9), custom fan curves, direct boost sliders,
 OSD notifications, and comprehensive hardware sensor telemetry.
EOF

# Postinst maintainer script
cat << 'EOF' > "$PKG_DIR/DEBIAN/postinst"
#!/bin/sh
set -e
if command -v udevadm > /dev/null 2>&1; then
    udevadm control --reload-rules || true
    udevadm trigger || true
fi
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
chmod -R a+rw /sys/class/hwmon/hwmon*/fan*_boost 2>/dev/null || true
chmod -R a+rw /sys/class/platform-profile/*/profile 2>/dev/null || true
chmod a+rw /sys/firmware/acpi/platform_profile 2>/dev/null || true
chmod -R a+r /sys/class/powercap/intel-rapl* 2>/dev/null || true
exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

# Postrm maintainer script
cat << 'EOF' > "$PKG_DIR/DEBIAN/postrm"
#!/bin/sh
set -e
if command -v udevadm > /dev/null 2>&1; then
    udevadm control --reload-rules || true
fi
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/postrm"

echo "[*] Building Debian package..."
dpkg-deb --root-owner-group --build "$PKG_DIR" "$SCRIPT_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo "[*] Cleaning up temporary build files..."
rm -rf "$PKG_DIR"

echo ""
echo "=========================================================================="
echo "[OK] Debian package successfully built:"
echo "     $SCRIPT_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "Install via:"
echo "     sudo apt install ./dell-g15-fan_${VERSION}_${ARCH}.deb"
echo "=========================================================================="
