# Dell G15 5520 Thermal & Fan Command Center for Linux

A high-performance hardware fan controller, thermal profile manager, and telemetry monitor engineered specifically for the **Dell G15 5520** (Intel Core i5-12500H / i7-12700H + NVIDIA GeForce RTX 3050 / 3060) running Linux.

This utility brings complete Alienware Command Center (AWCC) functionality to Linux, restoring native **G-Mode Turbo (Game Shift 100% Fans)**, direct dual-fan manual boost sliders, intelligent background fan curves with hysteresis protection, and comprehensive hardware sensor telemetry.

---

## Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation Guide](#installation-guide)
- [Setting Up Direct Permissions](#setting-up-direct-permissions)
- [Launching the Application](#launching-the-application)
- [Command-Line (CLI) Reference](#command-line-cli-reference)
- [Binding the G-Key (Fn + F9) in Linux](#binding-the-g-key-fn--f9-in-linux)
- [Smart Fan Curve Engine](#smart-fan-curve-engine)
- [Monitored Hardware Sensors](#monitored-hardware-sensors)
- [Architecture & Linux Kernel Interface](#architecture--linux-kernel-interface)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [License](#license)

---

## Features

- **Thermal Profile Switching**:
  - **Quiet Mode**: Low acoustic profile and lowered fan thresholds for quiet office/library environments.
  - **Balanced Mode**: Standard intelligent Dell dynamic firmware thermal curve.
  - **Performance Mode**: Unlocks higher power envelopes and aggressive fan curves.
  - **G-Mode Turbo (Game Shift)**: 1-Click hardware toggle that pins CPU and GPU fans to 100% boost (~4000 RPM CPU / ~4300 RPM GPU) for maximum cooling under intense gaming/workloads.
  - **Custom Mode**: Independent manual fan boost sliders (0% to 100%).
- **Precision Hardware Tachometers & Telemetry**:
  - Live RPM tachometers for both CPU and GPU cooling fans with animated turbine indicators.
  - Instantaneous dual-core thermal meters with peak temperature tracking.
  - Intel RAPL CPU Package Power (Watts), CPU clock frequency (GHz), and total load (%).
  - Real-time oscilloscope sparkline graph tracking temperatures and fan speeds.
- **Smart Fan Curve Engine**:
  - Background loop calculating dynamic fan speeds via linear interpolation.
  - Built-in hysteresis protection (2.5 deg C threshold) to eliminate annoying fan pulsing/cycling.
  - Built-in presets (*Silent/Stealth*, *Balanced Dynamic*, *Aggressive Performance*, *Maximum Turbo*) plus an editable 5-point threshold table.
- **System Tray Integration**:
  - Minimizes to the system tray with live temperature/RPM tooltips and a right-click quick menu.
- **Full CLI & Hotkey Integration**:
  - Fast, scriptable command-line interface with formatted ASCII telemetry tables.
  - One-command G-Mode toggle designed for global keyboard shortcut integration.
- **Passwordless Sysfs Operation**:
  - Includes automated udev rules so non-root users can adjust fan speeds and profiles without password prompts.

---

## System Requirements

- **Supported Laptops**: Dell G15 5520, 5521, 5525 (and compatible Alienware/Dell G-Series laptops).
- **Supported Linux Distributions**: Kali Linux, Debian, Ubuntu, Linux Mint, Fedora, Arch Linux, Pop!_OS.
- **Kernel Requirement**: Linux Kernel 5.15+ (Kernel 6.x recommended with `alienware_wmi` and `dell_smm_hwmon` loaded).
- **Python**: Python 3.10 or newer.

---

## Installation Guide

### Step 1: Install System Dependencies

#### Debian / Ubuntu / Kali Linux:
```bash
sudo apt update
sudo apt install -y python3 python3-pyqt6 python3-psutil git
```

#### Arch Linux / Manjaro:
```bash
sudo pacman -S python python-pyqt6 python-psutil git
```

#### Fedora / RHEL:
```bash
sudo dnf install -y python3 python3-pyqt6 python3-psutil git
```

---

### Step 2: Clone the Repository

```bash
git clone https://github.com/your-username/dell-g15-fan-controller.git
cd dell-g15-fan-controller
```

---

### Step 3: Run the Installer

Run the automated installer script to set up execution permissions, desktop shortcuts, and the CLI executable:

```bash
chmod +x install.sh setup_permissions.sh main.py dell_g15_fan_cli.py dell_g15_fan_gui.py
./install.sh
```

---

## Setting Up Direct Permissions

By default, writing to Linux `/sys/class/hwmon/` fan boost nodes and `/sys/class/platform-profile/` requires root privileges.

To allow the application to adjust fan speeds and profiles in real time without prompting for your `sudo` password on every slider drag:

```bash
sudo ./setup_permissions.sh
```

This installs `/etc/udev/rules.d/99-dell-g15-fan.rules` and updates live sysfs permissions permanently across reboots.

---

## Launching the Application

### 1. From Desktop Application Menu
Open your desktop launcher (GNOME Activities, XFCE Menu, KDE Launcher) and search for **"Dell G15 Fan Command Center"**.

### 2. From the Terminal
```bash
# Using the installed symlink
dell-g15-fan

# Or directly from the cloned repository
python3 main.py
```

---

## Command-Line (CLI) Reference

The CLI utility provides fast, scriptable control over all hardware functions without opening the GUI.

### Command Reference Table

| Flag | Argument | Description |
|---|---|---|
| `-s`, `--status` | None | Display complete formatted ASCII telemetry table |
| `-g`, `--gmode-toggle` | None | Instant toggle between G-Mode Turbo (100% fans) and Balanced |
| `--gmode-on` | None | Force G-Mode Turbo ON (100% fan boost) |
| `--gmode-off` | None | Force G-Mode Turbo OFF (return to Balanced profile) |
| `-m`, `--mode` | `quiet` / `balanced` / `performance` / `custom` | Set ACPI platform thermal profile |
| `-f`, `--fan` | `0` - `100` | Set boost percentage for both CPU and GPU fans |
| `--cpu-fan` | `0` - `100` | Set CPU fan boost percentage independently |
| `--gpu-fan` | `0` - `100` | Set GPU fan boost percentage independently |
| `--monitor` | None | Live terminal dashboard updating every 1.5 seconds |
| `--install-rules` | None | Install udev permissions rules (requires sudo) |
| `--gui` | None | Launch graphical interface |

### CLI Examples

#### Check Live System Status:
```bash
dell-g15-fan --status
```
*Output:*
```text
================================================================
             DELL G15 5520 THERMAL & FAN COMMAND CENTER         
================================================================

Thermal Profile : BALANCED  [ NORMAL ]
CPU Processor   : 2.10 GHz | Load: 15% | Package Power: 24.5 W
Power Source    : Connected (AC) (Battery: 54% (12.26V) • Discharge: 32.9W)

Thermal Sensors :
   * CPU Package Temperature : 50.0 deg C (Peak: 50.0 deg C)
   * GPU Core Temperature    : 50.0 deg C (Peak: 50.0 deg C)
   * NVMe SSD Drive          : 37.9 deg C
   * DDR5 System RAM         : 49.0 deg C
   * Motherboard Ambient     : 51.0 deg C

Cooling Fans :
   * CPU Fan : 1839 RPM (46.0%) [Boost: 0%] [#########...........]
   * GPU Fan : 1979 RPM (46.0%) [Boost: 0%] [#########...........]

Hardware Access Status :
   * Fan Boost Control : Direct Access Active
   * Platform Profile  : Active
================================================================
```

#### Toggle G-Mode Turbo:
```bash
dell-g15-fan --gmode-toggle
```

#### Set Manual Fan Speed:
```bash
# Set both fans to 75%
dell-g15-fan --fan 75

# Set CPU fan to 50% and GPU fan to 90%
dell-g15-fan --cpu-fan 50 --gpu-fan 90

# Reset back to automatic firmware control
dell-g15-fan --fan 0
```

#### Set Operating Profile:
```bash
dell-g15-fan --mode quiet
dell-g15-fan --mode performance
```

---

## Binding the G-Key (Fn + F9) in Linux

You can configure your laptop's physical **G-Key** (or any custom keyboard shortcut) to toggle G-Mode Turbo instantly just like in Windows.

### GNOME / Kali / Ubuntu:
1. Open **Settings** -> **Keyboard** -> **Keyboard Shortcuts** -> **View and Customize Shortcuts** -> **Custom Shortcuts**.
2. Click **Add Shortcut (+)**:
   - **Name**: `Dell G-Mode Turbo Toggle`
   - **Command**: `dell-g15-fan --gmode-toggle`
   - **Shortcut**: Press <kbd>F9</kbd> (or <kbd>Fn</kbd> + <kbd>F9</kbd>, or <kbd>Super</kbd> + <kbd>G</kbd>).
3. Click **Add**.

### KDE Plasma:
1. Open **System Settings** -> **Shortcuts** -> **Custom Shortcuts**.
2. Click **Edit** -> **New** -> **Global Shortcut** -> **Command/URL**.
3. Set Trigger to <kbd>F9</kbd> and Action to `dell-g15-fan --gmode-toggle`.

### XFCE / i3 / Sway:
Add the following line to your `~/.config/i3/config` or `~/.config/sway/config`:
```bash
bindsym XF86Launch1 exec --no-startup-id dell-g15-fan --gmode-toggle
# Or for F9:
bindsym F9 exec --no-startup-id dell-g15-fan --gmode-toggle
```

---

## Smart Fan Curve Engine

The built-in Smart Fan Curve Engine operates as a lightweight background daemon that continuously computes target fan speeds based on real-time CPU and GPU temperatures.

### How it Works:
1. **Linear Interpolation**: Computes the exact fan speed between defined temperature thresholds.
2. **Hysteresis Algorithm**: Incorporates a 2.5 deg C deadband. Fans will immediately ramp up when temperature rises past a threshold, but will only step down once the temperature drops at least 2.5 deg C below the threshold. This eliminates fan surging/pulsing.
3. **Preset Profiles**:
   - **Silent / Stealth**: Optimized for silent acoustic operation (fans remain low until 70 deg C).
   - **Balanced Dynamic**: Smooth everyday computing balance.
   - **Aggressive Performance**: Early ramp-up for sustained CPU/GPU rendering and compiling.
   - **Maximum Turbo**: Aggressive high-duty cooling.

---

## Monitored Hardware Sensors

The application monitors all available hardware sensors exposed by the Linux kernel:

| Sensor Category | Subsystem | Metrics Exposed |
|---|---|---|
| **CPU Package & Cores** | `coretemp` (`hwmon3`) | Package temperature, Per-Core temps (#0 to #11), Peak tracking |
| **GPU Core** | `dell_smm` (`hwmon7`) / NVIDIA sysfs | Live temperature, Peak tracking |
| **Cooling Fans** | `alienware_wmi` (`hwmon5`) & `dell_smm` (`hwmon7`) | Fan 1 (CPU) RPM, Fan 2 (GPU) RPM, Boost registers (0-255) |
| **Solid State Drive** | `nvme` (`hwmon1`) | NVMe SSD composite temperature |
| **System Memory** | `spd5118` (`hwmon4`) | DDR5 System RAM thermal sensor |
| **Motherboard Ambient** | `dell_smm` (`hwmon7`) | Chassis ambient thermal zone |
| **Network Adapter** | `iwlwifi` (`hwmon2`) | Intel Wi-Fi 6 adapter temperature |
| **CPU Power & Clock** | `intel-rapl` & `psutil` | RAPL Package Power (Watts), CPU core clock (GHz), CPU load (%) |
| **Battery & Power** | `BAT0` / `AC` (`hwmon0`) | State of charge (%), Voltage (V), Discharge flow (W), AC status |

---

## Architecture & Linux Kernel Interface

The application interacts directly with Linux kernel sysfs nodes and ACPI interfaces:

```text
+-------------------------------------------------------------+
|               Dell G15 Fan Command Center                   |
|           (PyQt6 GUI  /  CLI Engine  /  Fan Curve)          |
+------------------------------+------------------------------+
                               |
               +---------------+---------------+
               |   DellFanBackend Controller   |
               +---------------+---------------+
                               |
       +-----------------------+-----------------------+
       |                       |                       |
       v                       v                       v
+---------------+      +---------------+      +----------------+
| alienware_wmi |      |   dell_smm    |      |    ACPI WMI    |
| (fan*_boost)  |      |  (tachometers)|      |platform-profile|
+---------------+      +---------------+      +----------------+
       |                       |                       |
       +-----------------------+-----------------------+
                               |
                               v
               +-------------------------------+
               |    Dell G15 5520 Hardware     |
               | (Dual Fans, EC, Thermal Zones)|
               +-------------------------------+
```

- **Fan Boost**: `/sys/class/hwmon/hwmon5/fan1_boost` and `fan2_boost` (Integer range 0-255).
- **Fan Tachometers**: `/sys/class/hwmon/hwmon7/fan1_input` and `fan2_input` (RPM).
- **Thermal Profiles**: `/sys/class/platform-profile/platform-profile-0/profile` (`quiet`, `balanced`, `balanced-performance`, `performance`, `custom`).

---

## Troubleshooting & FAQ

### 1. Fans are not responding to manual sliders
- Make sure you ran `sudo ./setup_permissions.sh` to grant non-root access to the sysfs boost nodes.
- Verify that the `alienware_wmi` kernel module is loaded:
  ```bash
  lsmod | grep alienware_wmi
  ```
  If not loaded, load it with:
  ```bash
  sudo modprobe alienware_wmi
  ```

### 2. RPM reading shows 0 RPM
- The fan tachometer requires the `dell_smm_hwmon` kernel module. Check if it is active:
  ```bash
  lsmod | grep dell_smm_hwmon
  ```
  To load it:
  ```bash
  sudo modprobe dell_smm_hwmon restricted=0 ignore_dmi=1
  ```

### 3. How do I uninstall?
To remove the application shortcut and CLI symlink:
```bash
rm -f ~/.local/bin/dell-g15-fan
rm -f ~/.local/share/applications/dell-g15-fan.desktop
rm -f ~/.local/share/icons/hicolor/256x256/apps/dell-g15-fan.png
sudo rm -f /etc/udev/rules.d/99-dell-g15-fan.rules
sudo udevadm control --reload-rules
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
