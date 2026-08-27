#!/usr/bin/env python3
"""
Dell G15 5520 Thermal & Fan CLI Tool
Command-line utility for monitoring telemetry, switching thermal profiles,
setting fan speeds, and toggling G-Mode Turbo.
"""

import sys
import os
import argparse
import time
import subprocess
import ast
from dell_fan_backend import DellFanBackend


# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"
ORANGE = "\033[38;5;208m"
PURPLE = "\033[35m"


def print_status(backend: DellFanBackend):
    data = backend.get_telemetry()
    perms = backend.has_write_permissions()

    print(f"\n{BOLD}{CYAN}================================================================{RESET}")
    print(f"{BOLD}{CYAN}             DELL G15 5520 THERMAL & FAN COMMAND CENTER         {RESET}")
    print(f"{BOLD}{CYAN}================================================================{RESET}")

    # Platform Profile
    prof = data["active_profile"].upper()
    g_mode_str = f"{BOLD}{RED}[ G-MODE TURBO ACTIVE ]{RESET}" if data["is_g_mode"] else f"{DIM}[ NORMAL ]{RESET}"
    
    prof_color = GREEN if prof == "QUIET" else (CYAN if prof == "BALANCED" else (ORANGE if "PERFORMANCE" in prof else RED))
    print(f"\n{BOLD}Thermal Profile :{RESET} {prof_color}{prof}{RESET}  {g_mode_str}")
    
    # CPU & Power Telemetry
    f_ghz = data.get("cpu_freq_ghz", 0.0)
    c_load = data.get("cpu_usage_pct", 0.0)
    freq_str = f"{f_ghz:.2f} GHz" if f_ghz > 0 else "N/A"
    power_str = f"{data['cpu_power_w']} W" if data["cpu_power_w"] > 0 else "N/A"
    print(f"{BOLD}CPU Processor   :{RESET} {freq_str} | Load: {c_load:.0f}% | Package Power: {power_str}")

    # Power & Battery
    ac_str = f"{GREEN}Connected (AC){RESET}" if data["is_ac_online"] else f"{YELLOW}Battery{RESET}"
    bat_str = f"{data['battery_pct']}%" if data["battery_pct"] is not None else "N/A"
    volt_str = f" ({data['battery_voltage_v']}V)" if data.get("battery_voltage_v") else ""
    rate_str = f" • Discharge: {data['battery_rate_w']}W" if data.get("battery_rate_w") else ""
    print(f"{BOLD}Power Source    :{RESET} {ac_str} (Battery: {bat_str}{volt_str}{rate_str})")

    # Temperatures
    c_temp = data["cpu_temp"]
    g_temp = data["gpu_temp"]
    c_color = GREEN if c_temp < 60 else (YELLOW if c_temp < 75 else (ORANGE if c_temp < 85 else RED))
    g_color = GREEN if g_temp < 60 else (YELLOW if g_temp < 75 else (ORANGE if g_temp < 85 else RED))
    
    print(f"\n{BOLD}Thermal Sensors :{RESET}")
    print(f"   * CPU Package Temperature : {c_color}{c_temp} deg C{RESET} (Peak: {data.get('peak_cpu_temp', c_temp)} deg C)")
    print(f"   * GPU Core Temperature    : {g_color}{g_temp} deg C{RESET} (Peak: {data.get('peak_gpu_temp', g_temp)} deg C)")
    if data.get("ssd_temp") is not None:
        print(f"   * NVMe SSD Drive          : {CYAN}{data['ssd_temp']} deg C{RESET}")
    if data.get("ram_temp") is not None:
        print(f"   * DDR5 System RAM         : {CYAN}{data['ram_temp']} deg C{RESET}")
    if data.get("ambient_temp") is not None:
        print(f"   * Motherboard Ambient     : {CYAN}{data['ambient_temp']} deg C{RESET}")

    # Fans
    f1_rpm = data["fan1_rpm"]
    f1_pct = data["fan1_pct"]
    f1_boost = data["fan1_boost"]
    f2_rpm = data["fan2_rpm"]
    f2_pct = data["fan2_pct"]
    f2_boost = data["fan2_boost"]

    f1_bar = render_bar(f1_pct)
    f2_bar = render_bar(f2_pct)

    print(f"\n{BOLD}Cooling Fans :{RESET}")
    print(f"   * CPU Fan : {BOLD}{f1_rpm} RPM{RESET} ({f1_pct}%) [Boost: {f1_boost}%] {f1_bar}")
    print(f"   * GPU Fan : {BOLD}{f2_rpm} RPM{RESET} ({f2_pct}%) [Boost: {f2_boost}%] {f2_bar}")

    # Permissions
    print(f"\n{BOLD}Hardware Access Status :{RESET}")
    boost_perm = f"{GREEN}Direct Access Active{RESET}" if perms["fan_boost"] else f"{YELLOW}Root required (Run with --install-rules){RESET}"
    prof_perm = f"{GREEN}Active{RESET}" if perms["platform_profile"] else f"{YELLOW}Standard/D-Bus{RESET}"
    print(f"   * Fan Boost Control : {boost_perm}")
    print(f"   * Platform Profile  : {prof_perm}")
    print(f"{BOLD}{CYAN}================================================================{RESET}\n")


def render_bar(pct: float, width: int = 20) -> str:
    filled = int(round((pct / 100.0) * width))
    empty = width - filled
    bar_color = GREEN if pct < 50 else (YELLOW if pct < 75 else RED)
    return f"[{bar_color}{'#' * filled}{DIM}{'.' * empty}{RESET}]"


def install_udev_rules():
    """Install udev rules to allow non-root users direct control over Dell fan and profiles."""
    rules_content = """# Udev rules for Dell G15 / Alienware Fan & Thermal Profile Control
# Grants rw access to sysfs fan boost and platform-profile nodes to plugdev/users

# Alienware WMI Fan Boost Nodes
SUBSYSTEM=="hwmon", ATTR{name}=="alienware_wmi", RUN+="/bin/chmod 0666 /sys/class/hwmon/%k/fan1_boost /sys/class/hwmon/%k/fan2_boost"

# Dell SMM HWMon PWM Nodes
SUBSYSTEM=="hwmon", ATTR{name}=="dell_smm", RUN+="/bin/chmod 0666 /sys/class/hwmon/%k/pwm1 /sys/class/hwmon/%k/pwm2 /sys/class/hwmon/%k/pwm1_enable /sys/class/hwmon/%k/pwm2_enable"

# Platform Profile Nodes
SUBSYSTEM=="platform-profile", RUN+="/bin/chmod 0666 /sys/class/platform-profile/%k/profile"

# Intel RAPL CPU Package Power Nodes
SUBSYSTEM=="powercap", RUN+="/bin/chmod -R 0444 /sys/class/powercap/intel-rapl*"

# Global ACPI Platform Profile
KERNEL=="platform_profile", SUBSYSTEM=="acpi", RUN+="/bin/chmod 0666 /sys/firmware/acpi/platform_profile"
"""
    rule_file = "/tmp/99-dell-g15-fan.rules"
    target_path = "/etc/udev/rules.d/99-dell-g15-fan.rules"
    with open(rule_file, "w") as f:
        f.write(rules_content)

    print(f"{CYAN}Installing udev rule for passwordless fan control...{RESET}")
    cmd = f"cp {rule_file} {target_path} && udevadm control --reload-rules && udevadm trigger && chmod -R a+rw /sys/class/hwmon/hwmon*/fan*_boost 2>/dev/null; chmod -R a+rw /sys/class/platform-profile/*/profile 2>/dev/null; chmod a+rw /sys/firmware/acpi/platform_profile 2>/dev/null; chmod -R a+r /sys/class/powercap/intel-rapl* 2>/dev/null"
    
    import subprocess
    res = subprocess.run(["pkexec", "sh", "-c", cmd])
    if res.returncode == 0:
        print(f"{GREEN}[OK] Udev rules successfully installed! Fan controls unlocked for all users.{RESET}")
    else:
        print(f"{RED}[FAIL] Failed to install udev rules. Try running with sudo.{RESET}")


def install_systemd_service():
    """Install and enable user systemd service for background fan curve control."""
    service_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(service_dir, exist_ok=True)
    service_path = os.path.join(service_dir, "dell-g15-fan.service")
    
    script_path = os.path.abspath(__file__)
    main_path = os.path.join(os.path.dirname(script_path), "main.py")
    exec_target = main_path if os.path.isfile(main_path) else script_path
    
    service_content = f"""[Unit]
Description=Dell G15 5520 Thermal & Smart Fan Curve Background Daemon
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {exec_target} --daemon
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
"""
    with open(service_path, "w") as f:
        f.write(service_content)
        
    print(f"{CYAN}[*] Wrote systemd unit to: {service_path}{RESET}")
    
    import subprocess
    subprocess.run(["systemctl", "--user", "daemon-reload"])
    res = subprocess.run(["systemctl", "--user", "enable", "--now", "dell-g15-fan.service"])
    if res.returncode == 0:
        print(f"{GREEN}[OK] Systemd user service successfully installed and started!{RESET}")
        print(f"  * Check status: dell-g15-fan --service-status")
        print(f"  * View logs   : journalctl --user -u dell-g15-fan -f")
    else:
        print(f"{RED}[FAIL] Failed to enable systemd service.{RESET}")


def remove_systemd_service():
    """Stop and remove user systemd service."""
    import subprocess
    subprocess.run(["systemctl", "--user", "stop", "dell-g15-fan.service"], stderr=subprocess.DEVNULL)
    subprocess.run(["systemctl", "--user", "disable", "dell-g15-fan.service"], stderr=subprocess.DEVNULL)
    service_path = os.path.expanduser("~/.config/systemd/user/dell-g15-fan.service")
    if os.path.isfile(service_path):
        os.remove(service_path)
    subprocess.run(["systemctl", "--user", "daemon-reload"])
    print(f"{GREEN}[OK] Systemd user service stopped and removed.{RESET}")


def check_systemd_service():
    """Display status of the user systemd service."""
    import subprocess
    subprocess.run(["systemctl", "--user", "status", "dell-g15-fan.service"])


def run_daemon(backend: DellFanBackend, preset: str = "Balanced Curve", auto_power: bool = True):
    """Run headless fan curve engine in the foreground."""
    from fan_curve_engine import FanCurveEngine
    engine = FanCurveEngine(backend)
    engine.set_preset(preset)
    backend.auto_power_switch_enabled = auto_power

    print(f"{BOLD}{CYAN}================================================================{RESET}")
    print(f"{BOLD}{CYAN}      DELL G15 5520 SMART FAN CURVE BACKGROUND DAEMON           {RESET}")
    print(f"{BOLD}{CYAN}================================================================{RESET}")
    print(f"Active Curve Preset : {BOLD}{preset}{RESET}")
    print(f"Auto Power Switch   : {BOLD}{'ENABLED (AC/Battery)' if auto_power else 'DISABLED'}{RESET}")
    print(f"Hardware Polling    : 1.0s (Hysteresis: 2.0 deg C)")
    print(f"{DIM}Press Ctrl+C to terminate daemon...{RESET}\n")

    backend.send_osd_notification("Dell G15 Fan Daemon", f"Started with {preset} active", "low")
    engine.start()

    try:
        while True:
            telem = backend.get_telemetry()
            c_temp = telem["cpu_temp"]
            g_temp = telem["gpu_temp"]
            f1 = telem["fan1_rpm"]
            f2 = telem["fan2_rpm"]
            b1 = telem["fan1_boost"]
            power = f"{telem['cpu_power_w']:.1f}W" if telem.get("cpu_power_w") else "N/A"
            ac = "AC" if telem.get("is_ac_online") else "BAT"
            
            ts = time.strftime("%H:%M:%S")
            print(f"\r[{ts}] CPU: {c_temp:.1f}C | GPU: {g_temp:.1f}C | PKG: {power:>6s} | Fans: {f1:4d}/{f2:4d} RPM | Boost: {b1:2d}% | Source: {ac} | Prof: {telem['active_profile'].upper():<10s}", end="", flush=True)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n\n[*] Stopping Smart Fan Curve Engine...")
        engine.stop()
        backend.set_fan_boost(0, 0)
        print(f"{GREEN}[OK] Daemon stopped. Returned fans to firmware auto control.{RESET}")


def bind_gkey_shortcuts():
    """Automatically bind F9, Game Shift (XF86Launch1), Tools, and Super+G to /usr/bin/dell-g15-fan --gmode-toggle."""
    import ast
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    print(f"{CYAN}[*] Configuring G-Key (F9 / Game Shift) shortcuts for desktop: {desktop or 'Standard'}{RESET}")
    
    # Resolve executable path
    bin_path = "/usr/bin/dell-g15-fan"
    if not os.path.isfile(bin_path):
        import shutil
        found = shutil.which("dell-g15-fan")
        bin_path = found if found else os.path.abspath(sys.argv[0])

    exec_cmd = f"{bin_path} --gmode-toggle"

    # 1. GNOME / Unity / Cinnamon
    if any(d in desktop for d in ["GNOME", "UNITY", "CINNAMON", "UBUNTU"]):
        schema = "org.gnome.settings-daemon.plugins.media-keys"
        try:
            raw = subprocess.check_output(["gsettings", "get", schema, "custom-keybindings"]).decode().strip()
            kb_list = ast.literal_eval(raw) if raw and raw != "@as []" else []
            
            bindings_to_add = [
                ("Dell G-Mode Turbo (F9)", "F9"),
                ("Dell G-Mode Turbo (Game Shift)", "XF86Launch1"),
                ("Dell G-Mode Turbo (Tools)", "XF86Tools"),
                ("Dell G-Mode Turbo (Super+G)", "<Super>g")
            ]
            
            for name, key in bindings_to_add:
                assigned_path = None
                for path in kb_list:
                    rel = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{path}"
                    try:
                        n = subprocess.check_output(["gsettings", "get", rel, "name"]).decode().strip().strip("'\"")
                        if n == name:
                            assigned_path = path
                            break
                    except Exception:
                        pass
                
                if not assigned_path:
                    idx = 0
                    while f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom{idx}/" in kb_list:
                        idx += 1
                    assigned_path = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom{idx}/"
                    kb_list.append(assigned_path)
                    subprocess.run(["gsettings", "set", schema, "custom-keybindings", str(kb_list)])
                
                rel = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{assigned_path}"
                subprocess.run(["gsettings", "set", rel, "name", name])
                subprocess.run(["gsettings", "set", rel, "command", exec_cmd])
                subprocess.run(["gsettings", "set", rel, "binding", key])
                print(f"{GREEN}[OK] Bound {key} -> {exec_cmd} in GNOME{RESET}")
        except Exception as e:
            print(f"{YELLOW}[!] Could not automatically configure GNOME shortcut: {e}{RESET}")
    
    # 2. XFCE
    elif "XFCE" in desktop:
        try:
            for k in ["F9", "XF86Launch1", "XF86Tools", "<Super>g"]:
                subprocess.run(["xfconf-query", "-c", "xfce4-keyboard-shortcuts", "-p", f"/commands/custom/{k}", "-n", "-t", "string", "-s", exec_cmd])
            print(f"{GREEN}[OK] Bound F9, XF86Launch1, XF86Tools, and Super+G in XFCE.{RESET}")
        except Exception as e:
            print(f"{YELLOW}[!] Could not configure XFCE shortcut: {e}{RESET}")

    print(f"{GREEN}[OK] G-Key shortcuts ready! Press F9, Game Shift, or Super+G to toggle G-Mode Turbo.{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Dell G15 5520 Thermal & Fan CLI Control Center",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  dell-g15-fan --status                     # Display temperatures and fan RPMs
  dell-g15-fan --gmode-toggle               # Toggle G-Mode Turbo (Instant max fans)
  dell-g15-fan --bind-gkey                  # Automatically bind physical G-Key (F9 / Fn+F9)
  dell-g15-fan --mode performance           # Switch profile: quiet, balanced, performance, g-mode
  dell-g15-fan --fan 75                     # Set both fans to 75% boost
  dell-g15-fan --daemon                     # Run headless fan curve background daemon
  dell-g15-fan --service-install            # Enable systemd user service on system boot
  dell-g15-fan --install-rules              # Unlock sysfs permissions (one-time setup)
"""
    )
    
    parser.add_argument("-s", "--status", action="store_true", help="Show live temperatures, fan RPMs, and power status")
    parser.add_argument("-m", "--mode", type=str, choices=["quiet", "balanced", "performance", "g-mode", "custom", "low-power"],
                        help="Set thermal profile mode")
    parser.add_argument("-f", "--fan", type=int, help="Set both CPU and GPU fan speed percentage (0-100)")
    parser.add_argument("--cpu-fan", type=int, help="Set CPU fan speed percentage (0-100)")
    parser.add_argument("--gpu-fan", type=int, help="Set GPU fan speed percentage (0-100)")
    parser.add_argument("-g", "--gmode-toggle", action="store_true", help="Toggle Alienware/Dell G-Mode Turbo on/off (with OSD notification)")
    parser.add_argument("--gmode-on", action="store_true", help="Turn ON G-Mode Turbo")
    parser.add_argument("--gmode-off", action="store_true", help="Turn OFF G-Mode Turbo")
    parser.add_argument("--bind-gkey", action="store_true", help="Automatically configure physical G-Key (F9 / Fn+F9 / Super+G) shortcut")
    parser.add_argument("--daemon", action="store_true", help="Run background smart fan curve daemon in console")
    parser.add_argument("--curve-preset", type=str, default="Balanced Curve", 
                        choices=["Silent / Stealth", "Balanced Curve", "Aggressive Cooling", "Max Performance (Turbo)"],
                        help="Select curve preset for daemon mode")
    parser.add_argument("--service-install", action="store_true", help="Install and enable user systemd service (auto-starts on boot)")
    parser.add_argument("--service-remove", action="store_true", help="Stop and remove user systemd service")
    parser.add_argument("--service-status", action="store_true", help="Display status of user systemd service")
    parser.add_argument("--install-rules", action="store_true", help="Install udev rules for zero-password fan control")
    parser.add_argument("--monitor", action="store_true", help="Continuously monitor temperatures and fan speeds in terminal")
    parser.add_argument("--notify", action="store_true", help="Send a test desktop notification")

    args = parser.parse_args()
    backend = DellFanBackend()

    if args.bind_gkey:
        bind_gkey_shortcuts()
        return

    if args.notify:
        DellFanBackend.send_osd_notification("Dell G15 Command Center", "Notification test: OSD display is functioning properly.", "normal")
        print(f"{GREEN}[OK] OSD notification sent.{RESET}")
        return

    if args.service_install:
        install_systemd_service()
        return

    if args.service_remove:
        remove_systemd_service()
        return

    if args.service_status:
        check_systemd_service()
        return

    if args.install_rules:
        install_udev_rules()
        return

    if args.daemon:
        run_daemon(backend, preset=args.curve_preset)
        return

    if args.gmode_toggle:
        telem = backend.get_telemetry()
        new_state = not telem["is_g_mode"]
        backend.set_g_mode(new_state)
        msg = "G-Mode Turbo ENGAGED (100% Max Fans)" if new_state else "G-Mode Disengaged (Balanced Profile)"
        print(f"{BOLD}{msg}{RESET}")
        DellFanBackend.send_osd_notification(
            "Dell G15: Game Shift (G-Key)",
            msg,
            urgency="critical" if new_state else "normal"
        )
        return

    if args.gmode_on:
        backend.set_g_mode(True)
        print("G-Mode Turbo is now ACTIVE (Max Cooling & Performance)")
        DellFanBackend.send_osd_notification("Dell G15: G-Mode Turbo", "Engaged 100% Maximum Fan Speeds", "critical")
        return

    if args.gmode_off:
        backend.set_g_mode(False)
        print("G-Mode Turbo is now OFF (Balanced Mode)")
        DellFanBackend.send_osd_notification("Dell G15: G-Mode Off", "Restored Balanced Thermal Profile", "normal")
        return

    if args.mode:
        if args.mode == "g-mode":
            backend.set_g_mode(True)
            print(f"{GREEN}[OK] Activated G-Mode Turbo.{RESET}")
            DellFanBackend.send_osd_notification("Dell G15 Thermal Profile", "G-Mode Turbo Active (100% Fans)", "critical")
        else:
            ok = backend.set_thermal_profile(args.mode)
            print(f"{GREEN}[OK] Thermal profile set to: {args.mode.upper()}{RESET}")
            DellFanBackend.send_osd_notification("Dell G15 Thermal Profile", f"Switched to {args.mode.upper()} mode", "normal")

    if args.fan is not None:
        backend.set_fan_boost(args.fan, args.fan)
        print(f"{GREEN}[OK] Both fans set to {args.fan}% boost.{RESET}")

    if args.cpu_fan is not None or args.gpu_fan is not None:
        c_fan = args.cpu_fan if args.cpu_fan is not None else 0
        g_fan = args.gpu_fan if args.gpu_fan is not None else 0
        backend.set_fan_boost(c_fan, g_fan)
        print(f"{GREEN}[OK] CPU Fan: {c_fan}%, GPU Fan: {g_fan}%{RESET}")

    if args.monitor:
        try:
            while True:
                os.system("clear")
                print_status(backend)
                print(f"{DIM}Press Ctrl+C to stop monitoring...{RESET}")
                time.sleep(1.5)
        except KeyboardInterrupt:
            print("\nStopped monitor.")
            return

    if args.status or (len(sys.argv) == 1):
        print_status(backend)


if __name__ == "__main__":
    main()
