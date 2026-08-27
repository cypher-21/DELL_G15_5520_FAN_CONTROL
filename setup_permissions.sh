#!/bin/bash
# ==============================================================================
# Dell G15 5520 Fan & Thermal Controller - Udev Permissions Setup
# This script installs udev rules allowing non-root users to adjust fan boost
# and switch thermal profiles directly without requiring root/sudo passwords.
# ==============================================================================

set -e

RULES_FILE="/etc/udev/rules.d/99-dell-g15-fan.rules"

echo "[*] Creating udev rules for Dell G15 fan boost and thermal profiles..."

cat << 'EOF' | sudo tee "$RULES_FILE" > /dev/null
# Udev rules for Dell G15 / Alienware Fan & Thermal Profile Control
# Grants rw access to sysfs fan boost and platform-profile nodes

# Alienware WMI Fan Boost Nodes
SUBSYSTEM=="hwmon", ATTR{name}=="alienware_wmi", RUN+="/bin/chmod 0666 /sys/class/hwmon/%k/fan1_boost /sys/class/hwmon/%k/fan2_boost"

# Dell SMM HWMon PWM Nodes
SUBSYSTEM=="hwmon", ATTR{name}=="dell_smm", RUN+="/bin/chmod 0666 /sys/class/hwmon/%k/pwm1 /sys/class/hwmon/%k/pwm2 /sys/class/hwmon/%k/pwm1_enable /sys/class/hwmon/%k/pwm2_enable"

# Platform Profile Nodes
SUBSYSTEM=="platform-profile", RUN+="/bin/chmod 0666 /sys/class/platform-profile/%k/profile"

# Global ACPI Platform Profile
KERNEL=="platform_profile", SUBSYSTEM=="acpi", RUN+="/bin/chmod 0666 /sys/firmware/acpi/platform_profile"
EOF

echo "[*] Reloading and triggering udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "[*] Setting immediate file permissions for currently active hwmon sysfs nodes..."
sudo chmod -R a+rw /sys/class/hwmon/hwmon*/fan*_boost 2>/dev/null || true
sudo chmod -R a+rw /sys/class/hwmon/hwmon*/pwm* 2>/dev/null || true
sudo chmod -R a+rw /sys/class/platform-profile/*/profile 2>/dev/null || true
sudo chmod a+rw /sys/firmware/acpi/platform_profile 2>/dev/null || true

echo "[+] Done! Direct fan control and thermal profile switching are now unlocked."
