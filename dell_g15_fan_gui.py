"""
Dell G15 5520 Thermal & Fan Command Center
Engineered Industrial Hardware Interface for Linux.
Designed with precision typography, clean structural layout, and high-density telemetry.
"""

import sys
import os

# Enforce Fusion style to avoid GTK theme CSS bugs and ensure crisp dark UI rendering
os.environ["QT_STYLE_OVERRIDE"] = "Fusion"

import collections
from typing import List, Tuple, Optional, Dict, Any

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPainterPath, QIcon

from dell_fan_backend import DellFanBackend
from fan_curve_engine import FanCurveEngine


# -----------------------------------------------------------------------------
# Precision Industrial Design Tokens (No AI rainbow gradients)
# -----------------------------------------------------------------------------
COLOR_BG_DARK = "#0d1015"
COLOR_BG_PANEL = "#131720"
COLOR_BG_SUB = "#1a202c"
COLOR_BG_ACTIVE = "#222a3a"
COLOR_BG_HOVER = "#1e2533"

COLOR_BORDER = "#252d3d"
COLOR_BORDER_SUBTLE = "#1c222e"
COLOR_BORDER_FOCUS = "#00d2ff"

COLOR_TEXT_PRIMARY = "#f1f5f9"
COLOR_TEXT_SECONDARY = "#94a3b8"
COLOR_TEXT_MUTED = "#64748b"

# Deliberate, technical accent colors
COLOR_ACCENT = "#00d2ff"       # Dell Technical Cyan
COLOR_ACCENT_DIM = "#0084a8"
COLOR_ALERT = "#ef4444"        # Thermal High Load / G-Mode Trigger
COLOR_SUCCESS = "#10b981"      # Optimal / Active Green
COLOR_WARNING = "#f59e0b"      # Elevated Temp Amber


# -----------------------------------------------------------------------------
# Custom Widget: Precision Radial Thermal Meter
# -----------------------------------------------------------------------------
class PrecisionRadialMeter(QtWidgets.QWidget):
    """Clean technical radial gauge for Thermal Zones and Fan Tachometers."""

    def __init__(self, label: str, unit: str = "°C", min_val: float = 30.0, max_val: float = 100.0, is_rpm: bool = False, parent=None):
        super().__init__(parent)
        self.label = label
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.is_rpm = is_rpm
        
        self.current_val = 0.0
        self.peak_val = 0.0
        self.sub_text = ""
        self.fan_angle = 0.0
        
        self.setMinimumSize(180, 190)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        
        if self.is_rpm:
            self.anim_timer = QTimer(self)
            self.anim_timer.timeout.connect(self._step_fan)
            self.anim_timer.start(35)

    def _step_fan(self):
        if self.current_val > 100:
            speed = max(1.5, (self.current_val / 60.0) * 1.5)
            self.fan_angle = (self.fan_angle + speed) % 360.0
            self.update()

    def set_value(self, val: float, peak: float = 0.0, sub: str = ""):
        self.current_val = val
        if peak > 0:
            self.peak_val = peak
        elif val > self.peak_val:
            self.peak_val = val
        self.sub_text = sub
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        cx = w / 2.0
        cy = 68.0
        r = 46.0

        # Category Tag
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        painter.setFont(QFont("DejaVu Sans", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(0, 4, w, 16), Qt.AlignmentFlag.AlignCenter, self.label.upper())

        # Base Arc
        start_angle = 145 * 16
        span_angle = -230 * 16
        
        painter.setPen(QPen(QColor(COLOR_BORDER), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        arc_rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        painter.drawArc(arc_rect, start_angle, span_angle)

        # Active Value Arc
        ratio = max(0.0, min(1.0, (self.current_val - self.min_val) / (self.max_val - self.min_val)))
        active_span = int(round(-230 * 16 * ratio))

        if not self.is_rpm:
            if self.current_val < 65:
                accent = QColor(COLOR_ACCENT)
            elif self.current_val < 82:
                accent = QColor(COLOR_WARNING)
            else:
                accent = QColor(COLOR_ALERT)
        else:
            accent = QColor(COLOR_ACCENT)

        if active_span != 0:
            painter.setPen(QPen(accent, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            painter.drawArc(arc_rect, start_angle, active_span)

        if self.is_rpm:
            # Subtle Technical Turbine in Center
            inner_r = r * 0.44
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self.fan_angle)
            painter.setPen(Qt.PenStyle.NoPen)
            blade_col = QColor(COLOR_ACCENT_DIM)
            blade_col.setAlpha(160)
            painter.setBrush(QBrush(blade_col))
            for _ in range(6):
                path = QPainterPath()
                path.moveTo(0, 0)
                path.lineTo(inner_r * 0.7, -inner_r * 0.3)
                path.lineTo(inner_r, 0)
                path.lineTo(inner_r * 0.3, inner_r * 0.2)
                path.closeSubpath()
                painter.drawPath(path)
                painter.rotate(60.0)
            painter.restore()

            # RPM Large Readout Below
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont("DejaVu Sans Mono", 14, QFont.Weight.Bold))
            painter.drawText(QRectF(0, cy + r + 8, w, 22), Qt.AlignmentFlag.AlignCenter, f"{int(self.current_val):,} RPM")
        else:
            # Temperature Readout Inside Arc
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont("DejaVu Sans Mono", 18, QFont.Weight.Bold))
            painter.drawText(QRectF(0, cy - 12, w, 24), Qt.AlignmentFlag.AlignCenter, f"{self.current_val:.1f}{self.unit}")

            # Peak Readout Below
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.setFont(QFont("DejaVu Sans", 8, QFont.Weight.DemiBold))
            peak_str = f"PEAK {self.peak_val:.1f}{self.unit}" if self.peak_val > 0 else ""
            painter.drawText(QRectF(0, cy + r + 8, w, 18), Qt.AlignmentFlag.AlignCenter, peak_str)

        # Micro Sub-badge
        if self.sub_text:
            badge_rect = QRectF(cx - 65, cy + r + 28, 130, 18)
            painter.setPen(QPen(QColor(COLOR_BORDER), 1))
            painter.setBrush(QBrush(QColor(COLOR_BG_SUB)))
            painter.drawRect(badge_rect)
            painter.setPen(QColor(COLOR_TEXT_SECONDARY))
            painter.setFont(QFont("DejaVu Sans", 7, QFont.Weight.Bold))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self.sub_text.upper())


# -----------------------------------------------------------------------------
# Custom Widget: Precision Telemetry Oscilloscope Line Chart
# -----------------------------------------------------------------------------
class PrecisionTelemetryChart(QtWidgets.QWidget):
    """Clean technical oscilloscope chart with precise telemetry metrics."""

    def __init__(self, history_len: int = 60, parent=None):
        super().__init__(parent)
        self.history_len = history_len
        self.cpu_temps = collections.deque(maxlen=history_len)
        self.gpu_temps = collections.deque(maxlen=history_len)
        self.fan1_pcts = collections.deque(maxlen=history_len)
        self.fan2_pcts = collections.deque(maxlen=history_len)
        self.fan1_rpm = 0
        self.fan2_rpm = 0
        
        self.setMinimumHeight(130)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

    def add_sample(self, cpu_t: float, gpu_t: float, fan1_p: float, fan2_p: float, f1_rpm: int = 0, f2_rpm: int = 0):
        self.cpu_temps.append(cpu_t)
        self.gpu_temps.append(gpu_t)
        self.fan1_pcts.append(fan1_p)
        self.fan2_pcts.append(fan2_p)
        self.fan1_rpm = f1_rpm
        self.fan2_rpm = f2_rpm
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 36, 16, 26, 20
        plot_w = max(10, w - pad_l - pad_r)
        plot_h = max(10, h - pad_t - pad_b)

        # Flat Panel Surface
        painter.fillRect(0, 0, w, h, QColor(COLOR_BG_PANEL))
        painter.setPen(QPen(QColor(COLOR_BORDER), 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        # Technical Grid Lines
        for step in [25, 50, 75, 100]:
            y = pad_t + plot_h - (step / 100.0) * plot_h
            painter.setPen(QPen(QColor("#181d28"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.setFont(QFont("DejaVu Sans Mono", 7))
            painter.drawText(QRectF(0, y - 6, pad_l - 6, 12), Qt.AlignmentFlag.AlignRight, f"{step}")

        # Baseline 0
        y0 = pad_t + plot_h
        painter.setPen(QPen(QColor(COLOR_BORDER), 1))
        painter.drawLine(int(pad_l), int(y0), int(w - pad_r), int(y0))
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        painter.drawText(QRectF(0, y0 - 6, pad_l - 6, 12), Qt.AlignmentFlag.AlignRight, "0")

        # Telemetry Legend
        cur_c = self.cpu_temps[-1] if self.cpu_temps else 0.0
        cur_g = self.gpu_temps[-1] if self.gpu_temps else 0.0
        cur_f1 = self.fan1_pcts[-1] if self.fan1_pcts else 0.0
        cur_f2 = self.fan2_pcts[-1] if self.fan2_pcts else 0.0

        legend_items = [
            (f"CPU TEMP: {cur_c:.1f}°C", COLOR_ACCENT, Qt.PenStyle.SolidLine),
            (f"GPU TEMP: {cur_g:.1f}°C", COLOR_TEXT_PRIMARY, Qt.PenStyle.DashLine),
            (f"FAN 1: {cur_f1:.0f}% ({self.fan1_rpm} RPM)", COLOR_SUCCESS, Qt.PenStyle.SolidLine),
            (f"FAN 2: {cur_f2:.0f}% ({self.fan2_rpm} RPM)", COLOR_WARNING, Qt.PenStyle.SolidLine)
        ]
        
        painter.setFont(QFont("DejaVu Sans Mono", 8, QFont.Weight.Bold))
        leg_x = pad_l + 8
        for text, color_code, pen_style in legend_items:
            painter.setPen(QPen(QColor(color_code), 2, pen_style))
            painter.drawLine(int(leg_x), 13, int(leg_x + 14), 13)
            painter.setPen(QColor(COLOR_TEXT_SECONDARY))
            painter.drawText(QRectF(leg_x + 20, 6, 175, 14), Qt.AlignmentFlag.AlignLeft, text)
            leg_x += 185

        if len(self.cpu_temps) < 2:
            return

        # Plot Series
        n = len(self.cpu_temps)
        dx = plot_w / float(self.history_len - 1)
        start_x = pad_l + (self.history_len - n) * dx

        def draw_series(data, color, pen_style=Qt.PenStyle.SolidLine, max_val=100.0):
            path = QPainterPath()
            for i, val in enumerate(data):
                x = start_x + i * dx
                ratio = max(0.0, min(1.0, val / max_val))
                y = pad_t + plot_h - (ratio * plot_h)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            pen = QPen(QColor(color), 1.5, pen_style, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        draw_series(self.cpu_temps, COLOR_ACCENT)
        draw_series(self.gpu_temps, COLOR_TEXT_PRIMARY, Qt.PenStyle.DashLine)
        draw_series(self.fan1_pcts, COLOR_SUCCESS)
        draw_series(self.fan2_pcts, COLOR_WARNING)


# -----------------------------------------------------------------------------
# Custom Widget: Precision Thermal Transfer Function Graph
# -----------------------------------------------------------------------------
class PrecisionCurveGraph(QtWidgets.QWidget):
    """Oscilloscope-style curve plot for Fan Curve Engine."""

    def __init__(self, points: List[Tuple[int, int]], parent=None):
        super().__init__(parent)
        self.points = points
        self.setMinimumHeight(140)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

    def set_points(self, points: List[Tuple[int, int]]):
        self.points = sorted(points, key=lambda x: x[0])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 36, 16, 16, 24
        plot_w = max(10, w - pad_l - pad_r)
        plot_h = max(10, h - pad_t - pad_b)

        # Panel
        painter.fillRect(0, 0, w, h, QColor(COLOR_BG_SUB))
        painter.setPen(QPen(QColor(COLOR_BORDER), 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        # Grid lines
        for pct in [25, 50, 75, 100]:
            y = pad_t + plot_h - (pct / 100.0) * plot_h
            painter.setPen(QPen(QColor("#242d3d"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.setFont(QFont("DejaVu Sans Mono", 7))
            painter.drawText(QRectF(0, y - 6, pad_l - 6, 12), Qt.AlignmentFlag.AlignRight, f"{pct}%")

        min_t, max_t = 30.0, 100.0
        for t_mark in [40, 60, 80, 100]:
            x = pad_l + ((t_mark - min_t) / (max_t - min_t)) * plot_w
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.setFont(QFont("DejaVu Sans Mono", 7))
            painter.drawText(QRectF(x - 20, pad_t + plot_h + 4, 40, 14), Qt.AlignmentFlag.AlignCenter, f"{t_mark}°C")

        if not self.points:
            return

        # Curve Line
        path = QPainterPath()
        point_coords = []
        for i, (temp, fan) in enumerate(self.points):
            t_clamped = max(min_t, min(max_t, float(temp)))
            x = pad_l + ((t_clamped - min_t) / (max_t - min_t)) * plot_w
            y = pad_t + plot_h - (max(0.0, min(100.0, float(fan))) / 100.0) * plot_h
            point_coords.append((x, y))
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        pen = QPen(QColor(COLOR_ACCENT), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Step Handles
        for x, y in point_coords:
            painter.setPen(QPen(QColor(COLOR_BG_DARK), 1))
            painter.setBrush(QBrush(QColor(COLOR_ACCENT)))
            painter.drawRect(QRectF(x - 3.5, y - 3.5, 7, 7))


# -----------------------------------------------------------------------------
# Main Application Window
# -----------------------------------------------------------------------------
class DellG15MainWindow(QtWidgets.QMainWindow):
    """Main Application Window for Dell G15 Thermal and Fan Control Center."""

    def __init__(self, backend: DellFanBackend):
        super().__init__()
        self.backend = backend
        self.curve_engine = FanCurveEngine(backend)
        
        self.setWindowTitle("Dell G15 5520 Thermal Command Center")
        self.setMinimumSize(960, 720)
        self.resize(980, 750)
        
        self._init_ui()
        self._init_system_tray()
        
        # Periodic Telemetry Update (1.5s interval)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.refresh_telemetry)
        self.telemetry_timer.start(1500)
        
        self.refresh_telemetry()

    def _init_ui(self):
        # Precise, flat technical stylesheet with clean borders and high contrast
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLOR_BG_DARK};
            }}
            QWidget {{
                color: {COLOR_TEXT_PRIMARY};
                font-family: 'DejaVu Sans', 'Liberation Sans', sans-serif;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLOR_BORDER};
                background: {COLOR_BG_DARK};
                border-top: none;
            }}
            QTabBar::tab {{
                background: {COLOR_BG_PANEL};
                color: {COLOR_TEXT_SECONDARY};
                padding: 8px 24px;
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 0.5px;
                border: 1px solid {COLOR_BORDER};
                border-bottom: none;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {COLOR_BG_SUB};
                color: {COLOR_ACCENT};
                border-top: 2px solid {COLOR_ACCENT};
            }}
            QTabBar::tab:hover:!selected {{
                background: {COLOR_BG_HOVER};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {COLOR_BORDER};
                height: 4px;
                background: {COLOR_BG_SUB};
            }}
            QSlider::sub-page:horizontal {{
                background: {COLOR_ACCENT};
            }}
            QSlider::handle:horizontal {{
                background: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                width: 14px;
                margin-top: -6px;
                margin-bottom: -6px;
            }}
            QPushButton {{
                background-color: {COLOR_BG_PANEL};
                border: 1px solid {COLOR_BORDER};
                padding: 6px 14px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BG_HOVER};
                border-color: {COLOR_ACCENT};
                color: {COLOR_ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_BG_ACTIVE};
            }}
            QCheckBox {{
                spacing: 6px;
                font-size: 11px;
                font-weight: bold;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {COLOR_BORDER};
                background: {COLOR_BG_SUB};
            }}
            QCheckBox::indicator:checked {{
                background: {COLOR_ACCENT};
                border-color: {COLOR_ACCENT};
            }}
        """)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Technical Header Bar
        main_layout.addWidget(self._create_header())

        # 2. Main Workspace Tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._create_dashboard_tab(), "DASHBOARD")
        self.tabs.addTab(self._create_fan_curve_tab(), "FAN CURVES")
        self.tabs.addTab(self._create_sensors_tab(), "HARDWARE SENSORS")
        main_layout.addWidget(self.tabs)

        # 3. Status Bar
        self.status_bar_label = QtWidgets.QLabel("SYSTEM READY • HARDWARE POLLING ACTIVE")
        self.status_bar_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-family: 'DejaVu Sans Mono'; padding: 2px 2px;")
        main_layout.addWidget(self.status_bar_label)

    def _create_header(self) -> QtWidgets.QWidget:
        header_bar = QtWidgets.QFrame()
        header_bar.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER};")
        layout = QtWidgets.QHBoxLayout(header_bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Brand Signature
        brand_layout = QtWidgets.QVBoxLayout()
        brand_layout.setSpacing(1)
        
        brand_title = QtWidgets.QLabel("DELL G15 5520")
        brand_title.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 16px; font-weight: 900; letter-spacing: 1.5px; font-family: 'DejaVu Sans Mono';")
        
        brand_sub = QtWidgets.QLabel("Intel Core i5-12500H • NVIDIA GeForce RTX 3050 Mobile")
        brand_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-weight: demi-bold;")
        
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_sub)
        layout.addLayout(brand_layout)
        
        layout.addStretch()

        # Telemetry Status Readouts
        self.badge_freq = QtWidgets.QLabel("CPU -- GHz")
        self.badge_freq.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_TEXT_PRIMARY}; padding: 4px 8px; font-size: 11px; font-family: 'DejaVu Sans Mono'; border: 1px solid {COLOR_BORDER};")
        
        self.badge_power = QtWidgets.QLabel("PKG -- W")
        self.badge_power.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_TEXT_PRIMARY}; padding: 4px 8px; font-size: 11px; font-family: 'DejaVu Sans Mono'; border: 1px solid {COLOR_BORDER};")
        
        self.badge_battery = QtWidgets.QLabel("BAT --%")
        self.badge_battery.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_TEXT_PRIMARY}; padding: 4px 8px; font-size: 11px; font-family: 'DejaVu Sans Mono'; border: 1px solid {COLOR_BORDER};")

        self.btn_perms = QtWidgets.QPushButton("DIRECT CONTROL ACTIVE")
        self.btn_perms.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; font-size: 10px; font-family: 'DejaVu Sans Mono'; padding: 4px 10px;")
        self.btn_perms.clicked.connect(self._on_setup_permissions_clicked)

        layout.addWidget(self.badge_freq)
        layout.addWidget(self.badge_power)
        layout.addWidget(self.badge_battery)
        layout.addWidget(self.btn_perms)

        return header_bar

    def _create_dashboard_tab(self) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Profile Controller Strip
        prof_bar = QtWidgets.QFrame()
        prof_bar.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER};")
        prof_layout = QtWidgets.QHBoxLayout(prof_bar)
        prof_layout.setContentsMargins(8, 6, 8, 6)
        prof_layout.setSpacing(6)

        lbl_prof = QtWidgets.QLabel("OPERATING PROFILE:")
        lbl_prof.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        prof_layout.addWidget(lbl_prof)

        self.btn_mode_quiet = QtWidgets.QPushButton("QUIET")
        self.btn_mode_balanced = QtWidgets.QPushButton("BALANCED")
        self.btn_mode_perf = QtWidgets.QPushButton("PERFORMANCE")
        self.btn_mode_custom = QtWidgets.QPushButton("CUSTOM")
        self.btn_mode_gmode = QtWidgets.QPushButton("G-MODE TURBO")

        for btn in [self.btn_mode_quiet, self.btn_mode_balanced, self.btn_mode_perf, self.btn_mode_custom]:
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLOR_BG_SUB};
                    border: 1px solid {COLOR_BORDER};
                    color: {COLOR_TEXT_SECONDARY};
                    font-size: 11px;
                    font-weight: bold;
                    padding: 4px 12px;
                }}
                QPushButton:hover {{
                    border-color: {COLOR_ACCENT};
                    color: {COLOR_TEXT_PRIMARY};
                }}
                QPushButton:checked {{
                    background: {COLOR_BG_ACTIVE};
                    border: 1px solid {COLOR_ACCENT};
                    color: {COLOR_ACCENT};
                }}
            """)

        # Tactile G-Mode Turbo Button
        self.btn_mode_gmode.setCheckable(True)
        self.btn_mode_gmode.setMinimumHeight(30)
        self.btn_mode_gmode.setStyleSheet(f"""
            QPushButton {{
                background: #2b1118;
                border: 1px solid #571b29;
                color: #ff6685;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 14px;
            }}
            QPushButton:hover {{
                background: #3d1420;
                border-color: {COLOR_ALERT};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background: {COLOR_ALERT};
                border: 1px solid {COLOR_ALERT};
                color: #ffffff;
            }}
        """)

        self.btn_mode_quiet.clicked.connect(lambda: self._set_mode("quiet"))
        self.btn_mode_balanced.clicked.connect(lambda: self._set_mode("balanced"))
        self.btn_mode_perf.clicked.connect(lambda: self._set_mode("balanced-performance"))
        self.btn_mode_gmode.clicked.connect(self._toggle_gmode)
        self.btn_mode_custom.clicked.connect(lambda: self._set_mode("custom"))

        prof_layout.addWidget(self.btn_mode_quiet)
        prof_layout.addWidget(self.btn_mode_balanced)
        prof_layout.addWidget(self.btn_mode_perf)
        prof_layout.addWidget(self.btn_mode_custom)
        prof_layout.addStretch()
        prof_layout.addWidget(self.btn_mode_gmode)
        layout.addWidget(prof_bar)

        # 2. Main Workbench Row: Left Gauges / Right Controls
        wb_frame = QtWidgets.QFrame()
        wb_frame.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER};")
        wb_layout = QtWidgets.QHBoxLayout(wb_frame)
        wb_layout.setContentsMargins(10, 8, 10, 8)
        wb_layout.setSpacing(12)

        # Gauges
        self.gauge_cpu_temp = PrecisionRadialMeter("CPU Core", unit="°C", min_val=30, max_val=100)
        self.gauge_gpu_temp = PrecisionRadialMeter("GPU Core", unit="°C", min_val=30, max_val=100)
        self.gauge_cpu_fan = PrecisionRadialMeter("Fan 1 (CPU)", unit=" RPM", min_val=0, max_val=4000, is_rpm=True)
        self.gauge_gpu_fan = PrecisionRadialMeter("Fan 2 (GPU)", unit=" RPM", min_val=0, max_val=4300, is_rpm=True)

        wb_layout.addWidget(self.gauge_cpu_temp)
        wb_layout.addWidget(self.gauge_gpu_temp)
        wb_layout.addWidget(self.gauge_cpu_fan)
        wb_layout.addWidget(self.gauge_gpu_fan)
        layout.addWidget(wb_frame)

        # 3. Direct Fan Boost Control Strip
        ctrl_frame = QtWidgets.QFrame()
        ctrl_frame.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER};")
        ctrl_layout = QtWidgets.QVBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(12, 8, 12, 8)
        ctrl_layout.setSpacing(6)

        c_top = QtWidgets.QHBoxLayout()
        c_title = QtWidgets.QLabel("MANUAL FAN BOOST OVERRIDE")
        c_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        
        self.chk_sync_fans = QtWidgets.QCheckBox("SYNCHRONIZE CHANNELS")
        self.chk_sync_fans.setChecked(True)
        
        c_top.addWidget(c_title)
        c_top.addStretch()
        c_top.addWidget(self.chk_sync_fans)
        ctrl_layout.addLayout(c_top)

        # CPU Row
        r1 = QtWidgets.QHBoxLayout()
        lbl1 = QtWidgets.QLabel("CPU FAN BOOST:")
        lbl1.setFixedWidth(120)
        lbl1.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        
        self.slider_cpu = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_cpu.setRange(0, 100)
        self.slider_cpu.setValue(0)
        
        self.lbl_cpu_val = QtWidgets.QLabel("0%")
        self.lbl_cpu_val.setFixedWidth(44)
        self.lbl_cpu_val.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_ACCENT}; font-family: 'DejaVu Sans Mono'; font-weight: bold; font-size: 11px; border: 1px solid {COLOR_BORDER}; padding: 2px 4px;")
        self.lbl_cpu_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        r1.addWidget(lbl1)
        r1.addWidget(self.slider_cpu)
        r1.addWidget(self.lbl_cpu_val)
        ctrl_layout.addLayout(r1)

        # GPU Row
        r2 = QtWidgets.QHBoxLayout()
        lbl2 = QtWidgets.QLabel("GPU FAN BOOST:")
        lbl2.setFixedWidth(120)
        lbl2.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        
        self.slider_gpu = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_gpu.setRange(0, 100)
        self.slider_gpu.setValue(0)
        
        self.lbl_gpu_val = QtWidgets.QLabel("0%")
        self.lbl_gpu_val.setFixedWidth(44)
        self.lbl_gpu_val.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_TEXT_PRIMARY}; font-family: 'DejaVu Sans Mono'; font-weight: bold; font-size: 11px; border: 1px solid {COLOR_BORDER}; padding: 2px 4px;")
        self.lbl_gpu_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        r2.addWidget(lbl2)
        r2.addWidget(self.slider_gpu)
        r2.addWidget(self.lbl_gpu_val)
        ctrl_layout.addLayout(r2)

        # Presets Bar
        r3 = QtWidgets.QHBoxLayout()
        lbl_p = QtWidgets.QLabel("PRESETS:")
        lbl_p.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        r3.addWidget(lbl_p)

        for pct in [0, 25, 50, 75, 100]:
            name = "AUTO (0%)" if pct == 0 else (f"{pct}% MAX" if pct == 100 else f"{pct}%")
            btn = QtWidgets.QPushButton(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLOR_BG_SUB};
                    border: 1px solid {COLOR_BORDER};
                    color: {COLOR_TEXT_SECONDARY};
                    font-size: 10px;
                    font-family: 'DejaVu Sans Mono';
                    font-weight: bold;
                    padding: 4px 10px;
                }}
                QPushButton:hover {{
                    border-color: {COLOR_ACCENT};
                    color: {COLOR_ACCENT};
                }}
            """)
            btn.clicked.connect(lambda checked, p=pct: self._apply_slider_preset(p))
            r3.addWidget(btn)

        r3.addStretch()
        ctrl_layout.addLayout(r3)

        self.slider_cpu.valueChanged.connect(self._on_cpu_slider_changed)
        self.slider_gpu.valueChanged.connect(self._on_gpu_slider_changed)

        layout.addWidget(ctrl_frame)

        # 4. Telemetry Oscilloscope Timeline
        self.chart_widget = PrecisionTelemetryChart()
        layout.addWidget(self.chart_widget)

        return tab

    def _create_fan_curve_tab(self) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top_panel = QtWidgets.QFrame()
        top_panel.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER};")
        t_layout = QtWidgets.QHBoxLayout(top_panel)
        t_layout.setContentsMargins(10, 8, 10, 8)
        t_layout.setSpacing(10)

        lbl_curve = QtWidgets.QLabel("CURVE PRESET:")
        lbl_curve.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        t_layout.addWidget(lbl_curve)

        self.combo_presets = QtWidgets.QComboBox()
        self.combo_presets.setStyleSheet(f"""
            QComboBox {{
                background: {COLOR_BG_SUB};
                color: {COLOR_TEXT_PRIMARY};
                padding: 4px 10px;
                border: 1px solid {COLOR_BORDER};
                font-size: 11px;
                font-family: 'DejaVu Sans Mono';
                font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background: {COLOR_BG_PANEL};
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_BG_ACTIVE};
            }}
        """)
        for name in FanCurveEngine.PRESETS.keys():
            self.combo_presets.addItem(name)
        t_layout.addWidget(self.combo_presets)

        t_layout.addStretch()

        self.btn_toggle_curve = QtWidgets.QPushButton("ENABLE SMART CURVE")
        self.btn_toggle_curve.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; padding: 6px 16px; font-weight: bold; font-size: 11px; font-family: 'DejaVu Sans Mono';")
        self.btn_toggle_curve.setCheckable(True)
        self.btn_toggle_curve.clicked.connect(self._toggle_curve_engine)
        t_layout.addWidget(self.btn_toggle_curve)

        layout.addWidget(top_panel)

        # Transfer Function Graph
        self.curve_graph = PrecisionCurveGraph(self.curve_engine.curve_points)
        layout.addWidget(self.curve_graph)

        # Points Table
        self.curve_table = QtWidgets.QTableWidget(5, 2)
        self.curve_table.setHorizontalHeaderLabels(["TEMPERATURE THRESHOLD (°C)", "TARGET FAN DUTY (%)"])
        self.curve_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.curve_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.curve_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLOR_BG_PANEL};
                border: 1px solid {COLOR_BORDER};
                gridline-color: {COLOR_BORDER};
                color: {COLOR_TEXT_PRIMARY};
                font-family: 'DejaVu Sans Mono';
                font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_BG_SUB};
                color: {COLOR_TEXT_SECONDARY};
                font-weight: bold;
                font-family: 'DejaVu Sans Mono';
                font-size: 10px;
                border: 1px solid {COLOR_BORDER};
                padding: 6px;
            }}
        """)
        self._populate_curve_table()
        self.combo_presets.currentTextChanged.connect(self._on_preset_changed)
        layout.addWidget(self.curve_table)

        btn_save = QtWidgets.QPushButton("APPLY AND SAVE CUSTOM CURVE")
        btn_save.setStyleSheet(f"background: {COLOR_BG_PANEL}; color: {COLOR_ACCENT}; border: 1px solid {COLOR_BORDER}; padding: 6px 14px; font-size: 11px; font-family: 'DejaVu Sans Mono';")
        btn_save.clicked.connect(self._save_custom_curve_table)
        layout.addWidget(btn_save)

        return tab

    def _create_sensors_tab(self) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        self.sensor_tree = QtWidgets.QTreeWidget()
        self.sensor_tree.setHeaderLabels(["HARDWARE SUBSYSTEM", "SENSOR METRIC", "TELEMETRY VALUE"])
        self.sensor_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLOR_BG_PANEL};
                border: 1px solid {COLOR_BORDER};
                color: {COLOR_TEXT_PRIMARY};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_BG_SUB};
                color: {COLOR_TEXT_SECONDARY};
                font-weight: bold;
                font-family: 'DejaVu Sans Mono';
                font-size: 10px;
                border: 1px solid {COLOR_BORDER};
                padding: 6px;
            }}
        """)
        self.sensor_tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.sensor_tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.sensor_tree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.sensor_tree)

        return tab

    def _init_system_tray(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(COLOR_ACCENT)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(2, 2, 28, 28)
        painter.setPen(QPen(QColor(COLOR_BG_DARK), 2))
        painter.setFont(QFont("DejaVu Sans Mono", 14, QFont.Weight.Bold))
        painter.drawText(QRectF(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, "G")
        painter.end()

        icon = QIcon(pixmap)
        self.setWindowIcon(icon)
        self.tray_icon.setIcon(icon)

        # Context Menu
        tray_menu = QtWidgets.QMenu()
        tray_menu.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER};")

        act_show = tray_menu.addAction("Show Command Center")
        act_show.triggered.connect(self.showNormal)
        tray_menu.addSeparator()

        act_quiet = tray_menu.addAction("Quiet Mode")
        act_quiet.triggered.connect(lambda: self._set_mode("quiet"))

        act_balanced = tray_menu.addAction("Balanced Mode")
        act_balanced.triggered.connect(lambda: self._set_mode("balanced"))

        act_perf = tray_menu.addAction("Performance Mode")
        act_perf.triggered.connect(lambda: self._set_mode("balanced-performance"))

        act_gmode = tray_menu.addAction("G-Mode Turbo (100% Fans)")
        act_gmode.triggered.connect(lambda: self._set_mode("performance"))

        tray_menu.addSeparator()
        act_quit = tray_menu.addAction("Quit")
        act_quit.triggered.connect(QtWidgets.QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def refresh_telemetry(self):
        """Fetch live sensor data and update gauges, charts, and trees."""
        telem = self.backend.get_telemetry()
        perms = self.backend.has_write_permissions()

        # 1. Update Gauges
        c_temp = telem["cpu_temp"]
        g_temp = telem["gpu_temp"]
        peak_c = telem.get("peak_cpu_temp", c_temp)
        peak_g = telem.get("peak_gpu_temp", g_temp)

        f1_rpm = telem["fan1_rpm"]
        f1_pct = telem["fan1_pct"]
        f1_boost = telem["fan1_boost"]
        f2_rpm = telem["fan2_rpm"]
        f2_pct = telem["fan2_pct"]
        f2_boost = telem["fan2_boost"]

        sub_c = "NORMAL" if c_temp < 70 else ("ELEVATED" if c_temp < 85 else "HIGH LOAD")
        sub_g = "NORMAL" if g_temp < 65 else ("ELEVATED" if g_temp < 80 else "HIGH LOAD")

        sub_f1 = f"DUTY {f1_pct:.0f}%" + (f" • BOOST {int(f1_boost/255*100)}%" if f1_boost > 0 else "")
        sub_f2 = f"DUTY {f2_pct:.0f}%" + (f" • BOOST {int(f2_boost/255*100)}%" if f2_boost > 0 else "")

        self.gauge_cpu_temp.set_value(c_temp, peak_c, sub_c)
        self.gauge_gpu_temp.set_value(g_temp, peak_g, sub_g)
        self.gauge_cpu_fan.set_value(f1_rpm, 0.0, sub_f1)
        self.gauge_gpu_fan.set_value(f2_rpm, 0.0, sub_f2)

        # 2. Update Live Graph
        self.chart_widget.add_sample(c_temp, g_temp, f1_pct, f2_pct, f1_rpm, f2_rpm)

        # 3. Update Header Badges
        f_ghz = telem.get("cpu_freq_ghz", 0.0)
        c_load = telem.get("cpu_usage_pct", 0.0)
        self.badge_freq.setText(f"CPU {f_ghz:.2f} GHz [{c_load:.0f}%]" if f_ghz > 0 else f"LOAD {c_load:.0f}%")

        p_w = telem.get("cpu_power_w", 0.0)
        self.badge_power.setText(f"PKG {p_w:.1f} W" if p_w > 0 else "PKG -- W")

        bat = telem.get("battery_pct")
        ac_str = " [AC]" if telem.get("is_ac_online") else " [BAT]"
        self.badge_battery.setText(f"BAT {bat}%{ac_str}" if bat is not None else "AC MAIN")

        # Direct Permissions Button
        if perms["fan_boost"] and perms["platform_profile"]:
            self.btn_perms.setText("DIRECT CONTROL ACTIVE")
            self.btn_perms.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; font-size: 10px; font-family: 'DejaVu Sans Mono'; padding: 4px 10px;")
            self.btn_perms.setEnabled(False)
        else:
            self.btn_perms.setText("SETUP PERMISSIONS")
            self.btn_perms.setStyleSheet(f"background: #2b1118; color: {COLOR_ALERT}; border: 1px solid #571b29; font-size: 10px; font-family: 'DejaVu Sans Mono'; padding: 4px 10px;")
            self.btn_perms.setEnabled(True)

        # 4. Update Profile Buttons
        prof = telem["active_profile"].lower()
        is_gmode = telem["is_g_mode"]

        self.btn_mode_quiet.setChecked(prof in ["quiet", "low-power"])
        self.btn_mode_balanced.setChecked(prof == "balanced")
        self.btn_mode_perf.setChecked(prof == "balanced-performance")
        self.btn_mode_gmode.setChecked(is_gmode or prof == "performance")
        self.btn_mode_custom.setChecked(prof == "custom" or self.curve_engine.is_running)

        # 5. Tray Tooltip
        self.tray_icon.setToolTip(f"Dell G15 5520 | CPU: {c_temp}°C | GPU: {g_temp}°C | Fans: {f1_rpm}/{f2_rpm} RPM | {prof.upper()}")

        # 6. Sensor Tree
        self._refresh_sensor_tree(telem)

    def _refresh_sensor_tree(self, telem: dict):
        self.sensor_tree.clear()

        # Thermal Node
        t_root = QtWidgets.QTreeWidgetItem(self.sensor_tree, ["THERMAL ZONES", "Subsystem Overview", "All Active Thermal Zones"])
        QtWidgets.QTreeWidgetItem(t_root, ["", "CPU Package Temperature", f"{telem['cpu_temp']} °C (Peak: {telem['peak_cpu_temp']} °C)"])
        QtWidgets.QTreeWidgetItem(t_root, ["", "GPU Core Temperature", f"{telem['gpu_temp']} °C (Peak: {telem['peak_gpu_temp']} °C)"])
        if telem.get("ssd_temp") is not None:
            QtWidgets.QTreeWidgetItem(t_root, ["", "NVMe SSD Solid State Drive", f"{telem['ssd_temp']} °C"])
        if telem.get("ram_temp") is not None:
            QtWidgets.QTreeWidgetItem(t_root, ["", "DDR5 System RAM Module", f"{telem['ram_temp']} °C"])
        if telem.get("ambient_temp") is not None:
            QtWidgets.QTreeWidgetItem(t_root, ["", "Motherboard Ambient Sensor", f"{telem['ambient_temp']} °C"])
        if telem.get("wifi_temp") is not None:
            QtWidgets.QTreeWidgetItem(t_root, ["", "Intel Wi-Fi 6 Adapter", f"{telem['wifi_temp']} °C"])
        for i, ct in enumerate(telem.get("core_temps", [])):
            QtWidgets.QTreeWidgetItem(t_root, ["", f"CPU Core #{i} Temperature", f"{ct} °C"])

        # Fan Node
        f_root = QtWidgets.QTreeWidgetItem(self.sensor_tree, ["COOLING SUBSYSTEM", "Tachometers", "Active Dual Fan System"])
        QtWidgets.QTreeWidgetItem(f_root, ["", "CPU Fan Speed", f"{telem['fan1_rpm']} RPM ({telem['fan1_pct']}%)"])
        QtWidgets.QTreeWidgetItem(f_root, ["", "CPU Fan Maximum Limit", f"{telem['fan1_max']} RPM"])
        QtWidgets.QTreeWidgetItem(f_root, ["", "CPU Fan Boost Register", f"{telem['fan1_boost']} / 255"])
        QtWidgets.QTreeWidgetItem(f_root, ["", "GPU Fan Speed", f"{telem['fan2_rpm']} RPM ({telem['fan2_pct']}%)"])
        QtWidgets.QTreeWidgetItem(f_root, ["", "GPU Fan Maximum Limit", f"{telem['fan2_max']} RPM"])
        QtWidgets.QTreeWidgetItem(f_root, ["", "GPU Fan Boost Register", f"{telem['fan2_boost']} / 255"])

        # Power & Platform
        p_root = QtWidgets.QTreeWidgetItem(self.sensor_tree, ["POWER & PLATFORM", "Management Profile", "Dell ACPI / Alienware WMI"])
        QtWidgets.QTreeWidgetItem(p_root, ["", "Active Thermal Profile", telem["active_profile"].upper()])
        QtWidgets.QTreeWidgetItem(p_root, ["", "G-Mode Turbo Status", "ACTIVE (100% Fans)" if telem["is_g_mode"] else "INACTIVE"])
        QtWidgets.QTreeWidgetItem(p_root, ["", "CPU Core Clock Speed", f"{telem.get('cpu_freq_ghz', 0.0)} GHz"])
        QtWidgets.QTreeWidgetItem(p_root, ["", "CPU Total Utilization", f"{telem.get('cpu_usage_pct', 0.0)}%"])
        QtWidgets.QTreeWidgetItem(p_root, ["", "CPU Package Power Draw", f"{telem.get('cpu_power_w', 0.0)} Watts"])
        QtWidgets.QTreeWidgetItem(p_root, ["", "AC Power Adapter", "Connected" if telem.get("is_ac_online") else "Disconnected"])
        if telem.get("battery_pct") is not None:
            QtWidgets.QTreeWidgetItem(p_root, ["", "Battery State of Charge", f"{telem['battery_pct']}%"])
        if telem.get("battery_voltage_v") is not None:
            QtWidgets.QTreeWidgetItem(p_root, ["", "Battery Voltage", f"{telem['battery_voltage_v']} Volts"])
        if telem.get("battery_rate_w") is not None:
            QtWidgets.QTreeWidgetItem(p_root, ["", "Battery Power Flow", f"{telem['battery_rate_w']} Watts"])

        self.sensor_tree.expandAll()

    # -------------------------------------------------------------------------
    # Mode & Fan Actions
    # -------------------------------------------------------------------------
    def _set_mode(self, mode: str):
        if self.curve_engine.is_running:
            self.curve_engine.stop()
            self.btn_toggle_curve.setChecked(False)
            self.btn_toggle_curve.setText("ENABLE SMART CURVE")

        self.backend.set_thermal_profile(mode)
        self.status_bar_label.setText(f"PROFILE APPLIED: {mode.upper()}")
        self.refresh_telemetry()

    def _toggle_gmode(self):
        telem = self.backend.get_telemetry()
        new_state = not telem["is_g_mode"]
        self.backend.set_g_mode(new_state)
        self.status_bar_label.setText(f"G-MODE TURBO: {'ENGAGED (100% Fans)' if new_state else 'DISENGAGED (Balanced)'}")
        self.refresh_telemetry()

    def _apply_slider_preset(self, pct: int):
        self.slider_cpu.setValue(pct)
        if self.chk_sync_fans.isChecked():
            self.slider_gpu.setValue(pct)
        self.backend.set_fan_boost(pct, pct)
        self.status_bar_label.setText(f"FAN BOOST SET: {pct}%")

    def _on_cpu_slider_changed(self, val: int):
        self.lbl_cpu_val.setText(f"{val}%")
        if self.chk_sync_fans.isChecked():
            self.slider_gpu.blockSignals(True)
            self.slider_gpu.setValue(val)
            self.lbl_gpu_val.setText(f"{val}%")
            self.slider_gpu.blockSignals(False)
            self.backend.set_fan_boost(val, val)
        else:
            self.backend.set_fan_boost(val, self.slider_gpu.value())

    def _on_gpu_slider_changed(self, val: int):
        self.lbl_gpu_val.setText(f"{val}%")
        if self.chk_sync_fans.isChecked():
            self.slider_cpu.blockSignals(True)
            self.slider_cpu.setValue(val)
            self.lbl_cpu_val.setText(f"{val}%")
            self.slider_cpu.blockSignals(False)
            self.backend.set_fan_boost(val, val)
        else:
            self.backend.set_fan_boost(self.slider_cpu.value(), val)

    # -------------------------------------------------------------------------
    # Fan Curve Engine Actions
    # -------------------------------------------------------------------------
    def _toggle_curve_engine(self, checked: bool):
        if checked:
            self.curve_engine.start()
            self.btn_toggle_curve.setText("STOP SMART CURVE")
            self.btn_toggle_curve.setStyleSheet(f"background: #2b1118; color: {COLOR_ALERT}; border: 1px solid #571b29; padding: 6px 16px; font-weight: bold; font-size: 11px; font-family: 'DejaVu Sans Mono';")
            self.status_bar_label.setText("SMART FAN CURVE CONTROLLER ENGAGED")
        else:
            self.curve_engine.stop()
            self.btn_toggle_curve.setText("ENABLE SMART CURVE")
            self.btn_toggle_curve.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; padding: 6px 16px; font-weight: bold; font-size: 11px; font-family: 'DejaVu Sans Mono';")
            self.status_bar_label.setText("SMART FAN CURVE CONTROLLER STOPPED")

    def _populate_curve_table(self):
        pts = self.curve_engine.curve_points
        self.curve_table.setRowCount(len(pts))
        for row, (temp, fan) in enumerate(pts):
            t_item = QtWidgets.QTableWidgetItem(str(temp))
            f_item = QtWidgets.QTableWidgetItem(str(fan))
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            f_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.curve_table.setItem(row, 0, t_item)
            self.curve_table.setItem(row, 1, f_item)
        if hasattr(self, "curve_graph"):
            self.curve_graph.set_points(pts)

    def _on_preset_changed(self, name: str):
        if name in FanCurveEngine.PRESETS:
            self.curve_engine.set_preset(name)
            self._populate_curve_table()

    def _save_custom_curve_table(self):
        pts = []
        for r in range(self.curve_table.rowCount()):
            try:
                t = int(self.curve_table.item(r, 0).text().strip())
                f = int(self.curve_table.item(r, 1).text().strip())
                pts.append((t, f))
            except Exception:
                pass
        if pts:
            self.curve_engine.set_curve(pts, "Custom User Curve")
            self.curve_graph.set_points(pts)
            self.status_bar_label.setText("CUSTOM CURVE APPLIED")

    def _on_setup_permissions_clicked(self):
        from dell_g15_fan_cli import install_udev_rules
        install_udev_rules()
        self.refresh_telemetry()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Dell G15 Fan Command Center")
    
    backend = DellFanBackend()
    window = DellG15MainWindow(backend)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
