"""
Dell G15 Dynamic Fan Curve Controller Engine
Monitors temperature in a background daemon thread and computes fan speed % based on configurable curve profiles.
"""

import time
import threading
from typing import List, Tuple, Dict, Optional, Callable
from dell_fan_backend import DellFanBackend


class FanCurveEngine:
    """Manages dynamic fan curves with linear interpolation and hysteresis."""

    PRESETS: Dict[str, List[Tuple[int, int]]] = {
        "Silent / Stealth": [
            (40, 0),
            (60, 10),
            (70, 35),
            (80, 65),
            (90, 100)
        ],
        "Balanced Curve": [
            (40, 15),
            (55, 30),
            (68, 55),
            (78, 80),
            (88, 100)
        ],
        "Aggressive Cooling": [
            (40, 30),
            (50, 50),
            (65, 75),
            (75, 90),
            (82, 100)
        ],
        "Max Performance (Turbo)": [
            (30, 100),
            (100, 100)
        ]
    }

    def __init__(self, backend: DellFanBackend):
        self.backend = backend
        self.curve_points: List[Tuple[int, int]] = list(self.PRESETS["Balanced Curve"])
        self.preset_name: str = "Balanced Curve"
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self.polling_interval: float = 1.0  # seconds (fast, responsive hardware polling)
        self.hysteresis_temp: float = 2.0   # degree C buffer to prevent rapid fluctuating
        self._last_applied_pct: int = 0
        self._last_highest_temp: float = 0.0
        
        # Callback for telemetry updates
        self.on_update_callback: Optional[Callable[[Dict], None]] = None

    def set_curve(self, points: List[Tuple[int, int]], name: str = "Custom"):
        """Set temperature vs fan speed % curve points: [(temp1, fan1), (temp2, fan2), ...]"""
        with self._lock:
            # Sort by temperature
            sorted_pts = sorted(points, key=lambda x: x[0])
            # Ensure clamped
            clamped = [(max(0, min(110, t)), max(0, min(100, f))) for t, f in sorted_pts]
            if len(clamped) >= 2:
                self.curve_points = clamped
                self.preset_name = name

    def set_preset(self, preset_name: str):
        """Set a preset curve by name."""
        if preset_name in self.PRESETS:
            self.set_curve(self.PRESETS[preset_name], preset_name)

    def calculate_fan_pct(self, temp: float) -> int:
        """Calculate target fan percentage for a given temperature using linear interpolation."""
        with self._lock:
            points = list(self.curve_points)

        if not points:
            return 50

        if temp <= points[0][0]:
            return points[0][1]
        if temp >= points[-1][0]:
            return points[-1][1]

        for i in range(len(points) - 1):
            t1, f1 = points[i]
            t2, f2 = points[i + 1]
            if t1 <= temp <= t2:
                if t2 == t1:
                    return f1
                ratio = (temp - t1) / float(t2 - t1)
                return int(round(f1 + ratio * (f2 - f1)))

        return points[-1][1]

    def start(self):
        """Start background curve controller thread."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background curve controller thread."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run_loop(self):
        """Background control loop."""
        while self.is_running:
            try:
                telemetry = self.backend.get_telemetry()
                highest_temp = max(telemetry.get("cpu_temp", 0.0), telemetry.get("gpu_temp", 0.0))
                
                # Check hysteresis: only adjust fan if temp shifted by hysteresis_temp or if temp increased
                target_fan_pct = self.calculate_fan_pct(highest_temp)
                
                temp_diff = abs(highest_temp - self._last_highest_temp)
                should_apply = False
                
                if highest_temp > self._last_highest_temp:
                    # Temperature increasing -> react quickly
                    should_apply = (target_fan_pct != self._last_applied_pct)
                elif temp_diff >= self.hysteresis_temp:
                    # Temperature decreasing -> only adjust after cooling down past buffer
                    should_apply = (target_fan_pct != self._last_applied_pct)

                if should_apply or self._last_applied_pct == 0:
                    self.backend.set_fan_boost(target_fan_pct, target_fan_pct)
                    self._last_applied_pct = target_fan_pct
                    self._last_highest_temp = highest_temp

                if self.on_update_callback:
                    try:
                        self.on_update_callback({
                            "telemetry": telemetry,
                            "target_fan_pct": target_fan_pct,
                            "applied_pct": self._last_applied_pct,
                            "preset": self.preset_name
                        })
                    except Exception:
                        pass
            except Exception:
                pass

            time.sleep(self.polling_interval)
