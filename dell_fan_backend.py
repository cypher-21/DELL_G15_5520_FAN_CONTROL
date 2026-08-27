"""
Dell G15 5520 Fan & Thermal Hardware Backend
Provides hardware discovery, telemetry monitoring, thermal profile management,
and manual fan boost control via Linux kernel drivers (alienware_wmi, dell_smm, platform_profile).
"""

import os
import glob
import subprocess
import time
from typing import Dict, Optional, Tuple, List, Any
import psutil


class DellFanBackend:
    """Hardware controller and telemetry collector for Dell G-Series laptops."""

    def __init__(self):
        self.alienware_hwmon: Optional[str] = None
        self.dell_smm_hwmon: Optional[str] = None
        self.coretemp_hwmon: Optional[str] = None
        self.dell_ddv_hwmon: Optional[str] = None
        self.nvme_hwmon: Optional[str] = None
        self.ram_hwmon: Optional[str] = None
        self.wifi_hwmon: Optional[str] = None
        self.bat_hwmon: Optional[str] = None
        
        self.alienware_profile_path: Optional[str] = None
        self.dell_pc_profile_path: Optional[str] = None
        self.acpi_profile_path: str = "/sys/firmware/acpi/platform_profile"
        self.acpi_choices_path: str = "/sys/firmware/acpi/platform_profile_choices"
        
        self.available_profiles: List[str] = []
        self.fan_specs: Dict[str, Dict[str, Any]] = {
            "fan1": {"label": "CPU Fan", "max_rpm": 4000, "min_rpm": 0},
            "fan2": {"label": "GPU Fan", "max_rpm": 4300, "min_rpm": 0}
        }

        self._peak_cpu_temp: float = 0.0
        self._peak_gpu_temp: float = 0.0
        self._last_rapl_energy: int = 0
        self._last_rapl_ts: float = 0.0
        
        self.discover_hardware()

    def discover_hardware(self):
        """Locate active hwmon directories and platform-profile sysfs paths."""
        # 1. Discover hwmon devices by driver name
        for path in sorted(glob.glob('/sys/class/hwmon/hwmon*')):
            name_file = os.path.join(path, 'name')
            if os.path.isfile(name_file):
                try:
                    with open(name_file, 'r') as f:
                        name = f.read().strip()
                        if name == 'alienware_wmi':
                            self.alienware_hwmon = path
                        elif name == 'dell_smm':
                            self.dell_smm_hwmon = path
                        elif name == 'coretemp':
                            self.coretemp_hwmon = path
                        elif name == 'dell_ddv':
                            self.dell_ddv_hwmon = path
                        elif name == 'nvme':
                            self.nvme_hwmon = path
                        elif name == 'spd5118':
                            self.ram_hwmon = path
                        elif name.startswith('iwlwifi'):
                            self.wifi_hwmon = path
                        elif name == 'BAT0':
                            self.bat_hwmon = path
                except Exception:
                    pass

        # 2. Discover platform-profile devices
        for path in sorted(glob.glob('/sys/class/platform-profile/platform-profile*')):
            name_file = os.path.join(path, 'name')
            if os.path.isfile(name_file):
                try:
                    with open(name_file, 'r') as f:
                        name = f.read().strip()
                        if name == 'alienware-wmi':
                            self.alienware_profile_path = path
                        elif name == 'dell-pc':
                            self.dell_pc_profile_path = path
                except Exception:
                    pass

        # 3. Read fan limits if available
        if self.alienware_hwmon:
            for fan_id, key in [("fan1", "CPU Fan"), ("fan2", "GPU Fan")]:
                max_path = os.path.join(self.alienware_hwmon, f"{fan_id}_max")
                label_path = os.path.join(self.alienware_hwmon, f"{fan_id}_label")
                if os.path.isfile(max_path):
                    try:
                        with open(max_path, 'r') as f:
                            self.fan_specs[fan_id]["max_rpm"] = int(f.read().strip())
                    except Exception:
                        pass
                if os.path.isfile(label_path):
                    try:
                        with open(label_path, 'r') as f:
                            self.fan_specs[fan_id]["label"] = f.read().strip()
                    except Exception:
                        pass

        # 4. Determine available profile choices
        if self.alienware_profile_path:
            choices_file = os.path.join(self.alienware_profile_path, 'choices')
            if os.path.isfile(choices_file):
                try:
                    with open(choices_file, 'r') as f:
                        self.available_profiles = f.read().strip().split()
                except Exception:
                    pass
        elif os.path.isfile(self.acpi_choices_path):
            try:
                with open(self.acpi_choices_path, 'r') as f:
                    self.available_profiles = f.read().strip().split()
            except Exception:
                pass
                
        if not self.available_profiles:
            self.available_profiles = ["quiet", "balanced", "performance"]

    def _read_int(self, path: str, default: int = 0) -> int:
        """Safely read an integer from a sysfs file."""
        if not path or not os.path.isfile(path):
            return default
        try:
            with open(path, 'r') as f:
                return int(f.read().strip())
        except Exception:
            return default

    def _read_str(self, path: str, default: str = "") -> str:
        """Safely read a string from a sysfs file."""
        if not path or not os.path.isfile(path):
            return default
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except Exception:
            return default

    def has_write_permissions(self) -> Dict[str, bool]:
        """Check if current user can write to fan boost and profile nodes without sudo."""
        status = {
            "fan_boost": False,
            "platform_profile": False
        }
        
        if self.alienware_hwmon:
            b1 = os.path.join(self.alienware_hwmon, "fan1_boost")
            status["fan_boost"] = os.path.isfile(b1) and os.access(b1, os.W_OK)
            
        if self.alienware_profile_path:
            p = os.path.join(self.alienware_profile_path, "profile")
            status["platform_profile"] = os.path.isfile(p) and os.access(p, os.W_OK)
        elif os.path.isfile(self.acpi_profile_path):
            status["platform_profile"] = os.access(self.acpi_profile_path, os.W_OK)
            
        return status

    def get_telemetry(self) -> Dict[str, Any]:
        """Gather all real-time temperatures, fan RPMs, power, and profile states."""
        data: Dict[str, Any] = {
            "timestamp": time.time(),
            "cpu_temp": 0.0,
            "gpu_temp": 0.0,
            "peak_cpu_temp": 0.0,
            "peak_gpu_temp": 0.0,
            "ssd_temp": None,
            "ram_temp": None,
            "wifi_temp": None,
            "ambient_temp": None,
            "core_temps": [],
            "fan1_rpm": 0,
            "fan2_rpm": 0,
            "fan1_pct": 0.0,
            "fan2_pct": 0.0,
            "fan1_boost": 0,
            "fan2_boost": 0,
            "fan1_max": self.fan_specs["fan1"]["max_rpm"],
            "fan2_max": self.fan_specs["fan2"]["max_rpm"],
            "active_profile": "balanced",
            "is_g_mode": False,
            "cpu_power_w": 0.0,
            "cpu_freq_ghz": 0.0,
            "cpu_usage_pct": 0.0,
            "battery_pct": None,
            "battery_voltage_v": None,
            "battery_rate_w": None,
            "is_ac_online": True
        }

        # 1. Temperatures & Fan Speeds from alienware_wmi
        if self.alienware_hwmon:
            t1 = self._read_int(os.path.join(self.alienware_hwmon, "temp1_input"))
            t2 = self._read_int(os.path.join(self.alienware_hwmon, "temp2_input"))
            data["cpu_temp"] = round(t1 / 1000.0, 1) if t1 > 0 else 0.0
            data["gpu_temp"] = round(t2 / 1000.0, 1) if t2 > 0 else 0.0

            r1 = self._read_int(os.path.join(self.alienware_hwmon, "fan1_input"))
            r2 = self._read_int(os.path.join(self.alienware_hwmon, "fan2_input"))
            data["fan1_rpm"] = r1
            data["fan2_rpm"] = r2
            
            b1 = self._read_int(os.path.join(self.alienware_hwmon, "fan1_boost"))
            b2 = self._read_int(os.path.join(self.alienware_hwmon, "fan2_boost"))
            data["fan1_boost"] = b1
            data["fan2_boost"] = b2
            
            # Calculate % of max RPM
            max1 = data["fan1_max"] if data["fan1_max"] > 0 else 4000
            max2 = data["fan2_max"] if data["fan2_max"] > 0 else 4300
            data["fan1_pct"] = round(min(100.0, (r1 / max1) * 100.0), 1)
            data["fan2_pct"] = round(min(100.0, (r2 / max2) * 100.0), 1)

        # Fallback to dell_smm if alienware_wmi not providing fan speeds
        elif self.dell_smm_hwmon:
            r1 = self._read_int(os.path.join(self.dell_smm_hwmon, "fan1_input"))
            r2 = self._read_int(os.path.join(self.dell_smm_hwmon, "fan2_input"))
            data["fan1_rpm"] = r1
            data["fan2_rpm"] = r2
            t1 = self._read_int(os.path.join(self.dell_smm_hwmon, "temp1_input"))
            t2 = self._read_int(os.path.join(self.dell_smm_hwmon, "temp2_input"))
            data["cpu_temp"] = round(t1 / 1000.0, 1) if t1 > 0 else data["cpu_temp"]
            data["gpu_temp"] = round(t2 / 1000.0, 1) if t2 > 0 else data["gpu_temp"]

        # Track peak temperatures
        if data["cpu_temp"] > self._peak_cpu_temp:
            self._peak_cpu_temp = data["cpu_temp"]
        if data["gpu_temp"] > self._peak_gpu_temp:
            self._peak_gpu_temp = data["gpu_temp"]
        data["peak_cpu_temp"] = self._peak_cpu_temp
        data["peak_gpu_temp"] = self._peak_gpu_temp

        # 2. Auxiliary Sensors (SSD, RAM, WiFi, Ambient)
        if self.nvme_hwmon:
            t = self._read_int(os.path.join(self.nvme_hwmon, "temp1_input"))
            if t > 0:
                data["ssd_temp"] = round(t / 1000.0, 1)

        if self.ram_hwmon:
            t = self._read_int(os.path.join(self.ram_hwmon, "temp1_input"))
            if t > 0:
                data["ram_temp"] = round(t / 1000.0, 1)

        if self.wifi_hwmon:
            t = self._read_int(os.path.join(self.wifi_hwmon, "temp1_input"))
            if t > 0:
                data["wifi_temp"] = round(t / 1000.0, 1)

        if self.dell_ddv_hwmon:
            t = self._read_int(os.path.join(self.dell_ddv_hwmon, "temp2_input"))
            if t > 0:
                data["ambient_temp"] = round(t / 1000.0, 1)

        # Coretemp per-core temps
        if self.coretemp_hwmon:
            core_temps = []
            for temp_f in sorted(glob.glob(os.path.join(self.coretemp_hwmon, "temp*_input"))):
                val = self._read_int(temp_f)
                if val > 0:
                    core_temps.append(round(val / 1000.0, 1))
            if core_temps:
                data["core_temps"] = core_temps
                if data["cpu_temp"] == 0.0 and len(core_temps) > 0:
                    data["cpu_temp"] = core_temps[0]

        # 3. CPU Frequencies & Utilization
        try:
            data["cpu_usage_pct"] = psutil.cpu_percent(interval=None)
            freqs = psutil.cpu_freq(percpu=True)
            if freqs:
                avg_freq = sum(f.current for f in freqs) / len(freqs)
                data["cpu_freq_ghz"] = round(avg_freq / 1000.0, 2)
        except Exception:
            pass

        # 4. Thermal Profile Status
        if self.alienware_profile_path:
            prof = self._read_str(os.path.join(self.alienware_profile_path, "profile"), "balanced")
            data["active_profile"] = prof
            data["is_g_mode"] = (prof == "performance" and data["fan1_boost"] >= 95) or (prof == "performance")
        elif os.path.isfile(self.acpi_profile_path):
            prof = self._read_str(self.acpi_profile_path, "balanced")
            data["active_profile"] = prof
            data["is_g_mode"] = (prof == "performance")

        # 5. RAPL CPU Package Power (Watts)
        rapl_candidates = glob.glob("/sys/class/powercap/intel-rapl*/energy_uj") + glob.glob("/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj")
        for rapl_path in rapl_candidates:
            try:
                e1 = self._read_int(rapl_path)
                if e1 > 0:
                    t1_ts = time.time()
                    if self._last_rapl_energy > 0 and self._last_rapl_ts > 0:
                        dt = t1_ts - self._last_rapl_ts
                        de = e1 - self._last_rapl_energy
                        if dt > 0 and de >= 0:
                            data["cpu_power_w"] = round((de / dt) / 1_000_000.0, 1)
                    self._last_rapl_energy = e1
                    self._last_rapl_ts = t1_ts
                    break
            except Exception:
                pass

        # 6. AC Power & Battery Status
        ac_online = self._read_int("/sys/class/power_supply/AC/online", -1)
        if ac_online != -1:
            data["is_ac_online"] = (ac_online == 1)
            
        bat_capacity = self._read_int("/sys/class/power_supply/BAT0/capacity", -1)
        if bat_capacity != -1:
            data["battery_pct"] = bat_capacity

        bat_volt_uv = self._read_int("/sys/class/power_supply/BAT0/voltage_now", 0)
        bat_curr_ua = self._read_int("/sys/class/power_supply/BAT0/current_now", 0)
        if bat_volt_uv > 0:
            data["battery_voltage_v"] = round(bat_volt_uv / 1_000_000.0, 2)
            if bat_curr_ua > 0:
                # Wattage = Volts * Amps
                data["battery_rate_w"] = round((bat_volt_uv * bat_curr_ua) / 1_000_000_000_000.0, 1)

        return data

    def _write_sysfs(self, path: str, value: str) -> bool:
        """Attempt to write directly, or fallback to pkexec/sudo if needed."""
        if not path:
            return False
            
        # Try direct write first
        try:
            with open(path, 'w') as f:
                f.write(str(value).strip() + '\n')
            return True
        except PermissionError:
            try:
                res = subprocess.run(["pkexec", "sh", "-c", f"echo {value} > {path}"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                return res.returncode == 0
            except Exception:
                return False
        except Exception:
            return False

    def set_fan_boost(self, fan1_pct: int, fan2_pct: Optional[int] = None, sync_profile: bool = True) -> bool:
        """
        Set fan boost percentage (0% to 100%).
        Maps 0-100% directly to alienware_wmi sysfs nodes (0-100 scale).
        When boost > 0, automatically engages 'custom' mode in platform-profile so firmware respects the manual override.
        """
        if fan2_pct is None:
            fan2_pct = fan1_pct

        b1 = max(0, min(100, int(fan1_pct)))
        b2 = max(0, min(100, int(fan2_pct)))

        # If user is applying manual boost > 0 and we are not in performance/gmode, switch profile to 'custom'
        if sync_profile:
            if b1 > 0 or b2 > 0:
                cur_prof = self.get_telemetry().get("active_profile", "").lower()
                if cur_prof not in ["performance", "custom"]:
                    if self.alienware_profile_path:
                        self._write_sysfs(os.path.join(self.alienware_profile_path, "profile"), "custom")
            else:
                # If both fans set to 0, restore balanced if previously in custom
                cur_prof = self.get_telemetry().get("active_profile", "").lower()
                if cur_prof == "custom":
                    if self.alienware_profile_path:
                        self._write_sysfs(os.path.join(self.alienware_profile_path, "profile"), "balanced")

        success = True
        # 1. Alienware WMI Fan Boost Nodes (0-100 percentage scale)
        if self.alienware_hwmon:
            p1 = os.path.join(self.alienware_hwmon, "fan1_boost")
            p2 = os.path.join(self.alienware_hwmon, "fan2_boost")
            ok1 = self._write_sysfs(p1, str(b1))
            ok2 = self._write_sysfs(p2, str(b2))
            success = ok1 and ok2

        return success

    def set_thermal_profile(self, profile: str) -> bool:
        """
        Set thermal profile: 'quiet', 'balanced', 'balanced-performance', 'performance', 'low-power', 'custom'.
        """
        profile = profile.lower().strip()
        success = False

        # 1. Alienware WMI platform profile
        if self.alienware_profile_path:
            p_file = os.path.join(self.alienware_profile_path, "profile")
            success = self._write_sysfs(p_file, profile)

        # 2. Dell PC platform profile fallback / synchronization
        if self.dell_pc_profile_path:
            p_file = os.path.join(self.dell_pc_profile_path, "profile")
            mapped = profile
            if profile == "low-power":
                mapped = "cool"
            elif profile == "balanced-performance":
                mapped = "performance"
            elif profile == "custom":
                mapped = "balanced"
            self._write_sysfs(p_file, mapped)

        # 3. Global ACPI platform profile or powerprofilesctl fallback
        if not success:
            if os.path.isfile(self.acpi_profile_path):
                mapped = profile
                if profile in ["low-power", "quiet"]:
                    mapped = "quiet"
                elif profile in ["balanced-performance", "performance", "custom"]:
                    mapped = "performance"
                else:
                    mapped = "balanced"
                success = self._write_sysfs(self.acpi_profile_path, mapped)
                
            if not success:
                p_map = {"quiet": "power-saver", "low-power": "power-saver", "balanced": "balanced", 
                         "balanced-performance": "performance", "performance": "performance", "custom": "balanced"}
                target = p_map.get(profile, "balanced")
                try:
                    res = subprocess.run(["powerprofilesctl", "set", target], timeout=3)
                    success = (res.returncode == 0)
                except Exception:
                    pass

        # When switching profiles:
        if profile in ["quiet", "balanced", "low-power"]:
            self.set_fan_boost(0, 0)
        elif profile == "performance":
            self.set_fan_boost(100, 100)

        return success

    def set_g_mode(self, enable: bool) -> bool:
        """
        Activate or deactivate Alienware/Dell G-Mode Turbo.
        In G-Mode: Sets profile to 'performance' and fan boosts to 100% (255).
        Off: Sets profile to 'balanced' and fan boosts to 0 (auto firmware control).
        """
        if enable:
            ok_prof = self.set_thermal_profile("performance")
            ok_fan = self.set_fan_boost(100, 100)
            return ok_prof or ok_fan
        else:
            ok_prof = self.set_thermal_profile("balanced")
            ok_fan = self.set_fan_boost(0, 0)
            return ok_prof and ok_fan
