"""
Dell G15 5520 Thermal & Fan Command Center
Engineered Industrial Hardware Interface for Linux.
Designed with high-legibility typography, clear contrast, and high-density telemetry.
"""

import sys
import os

# Enforce Fusion style to avoid GTK theme CSS bugs and ensure crisp dark UI rendering
os.environ["QT_STYLE_OVERRIDE"] = "Fusion"

import collections
from typing import List, Tuple, Optional, Dict, Any

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QLinearGradient, QPainterPath, QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from dell_fan_backend import DellFanBackend
from fan_curve_engine import FanCurveEngine


# -----------------------------------------------------------------------------
# Precision Industrial Design Tokens
# -----------------------------------------------------------------------------
COLOR_BG_DARK = "#0d1015"
COLOR_BG_PANEL = "#131720"
COLOR_BG_SUB = "#1a202c"
COLOR_BG_ACTIVE = "#222a3a"
COLOR_BG_HOVER = "#1e2533"

COLOR_BORDER = "#283142"
COLOR_BORDER_SUBTLE = "#1e2430"
COLOR_BORDER_FOCUS = "#00d2ff"

COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#cbd5e1"
COLOR_TEXT_MUTED = "#94a3b8"

# Deliberate, technical accent colors
COLOR_ACCENT = "#00d2ff"       # Dell Technical Cyan
COLOR_ACCENT_DIM = "#0084a8"
COLOR_ALERT = "#ef4444"        # Thermal High Load / G-Mode Trigger
COLOR_SUCCESS = "#10b981"      # Optimal / Active Green
COLOR_WARNING = "#f59e0b"      # Elevated Temp Amber


# -----------------------------------------------------------------------------
# Custom Widget: Precision Radial Thermal & Fan Meter (High Legibility)
# -----------------------------------------------------------------------------
class PrecisionRadialMeter(QtWidgets.QWidget):
    """Clean technical radial gauge for Thermal Zones and Fan Tachometers with balanced typography."""

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
        
        self.setMinimumSize(215, 235)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        
        if self.is_rpm:
            self.anim_timer = QTimer(self)
            self.anim_timer.timeout.connect(self._step_fan)
            self.anim_timer.start(35)

    def _step_fan(self):
        if self.current_val > 100:
            speed = max(1.5, (self.current_val / 60.0) * 1.6)
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
        cy = 94.0
        r = 54.0

        # 1. High-Contrast Category Header (11pt Bold, 12px clear margin above arc)
        painter.setPen(QColor("#f1f5f9"))
        painter.setFont(QFont("DejaVu Sans", 11, QFont.Weight.Bold))
        painter.drawText(QRectF(0, 6, w, 22), Qt.AlignmentFlag.AlignCenter, self.label.upper())

        # 2. Base Arc (230 deg)
        start_angle = 145 * 16
        span_angle = -230 * 16
        
        painter.setPen(QPen(QColor(COLOR_BORDER), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        arc_rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        painter.drawArc(arc_rect, start_angle, span_angle)

        # 3. Active Value Arc
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
            painter.setPen(QPen(accent, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(arc_rect, start_angle, active_span)

        if self.is_rpm:
            # Rotating Fan Turbine (Enlarged)
            inner_r = r * 0.52
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self.fan_angle)
            painter.setPen(Qt.PenStyle.NoPen)
            blade_col = QColor(COLOR_ACCENT_DIM)
            blade_col.setAlpha(180)
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

            # RPM Readout Below (15pt Bold)
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont("DejaVu Sans Mono", 15, QFont.Weight.Bold))
            painter.drawText(QRectF(0, cy + r + 6, w, 24), Qt.AlignmentFlag.AlignCenter, f"{int(self.current_val):,} RPM")
        else:
            # Temperature Readout with Proportional Unit inside Arc
            temp_num_str = f"{self.current_val:.1f}"
            font_num = QFont("DejaVu Sans Mono", 18, QFont.Weight.Bold)
            font_unit = QFont("DejaVu Sans", 11, QFont.Weight.Bold)
            
            fm_num = QtGui.QFontMetrics(font_num)
            fm_unit = QtGui.QFontMetrics(font_unit)
            
            num_w = fm_num.horizontalAdvance(temp_num_str)
            unit_w = fm_unit.horizontalAdvance(self.unit)
            
            total_w = num_w + 3 + unit_w
            start_x = cx - total_w / 2.0
            
            # Numeric value
            painter.setFont(font_num)
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.drawText(QRectF(start_x, cy - 14, num_w, 28), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, temp_num_str)
            
            # Unit indicator
            painter.setFont(font_unit)
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(start_x + num_w + 3, cy - 10, unit_w + 4, 24), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.unit)

            # Peak Readout Below (10pt)
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.setFont(QFont("DejaVu Sans", 9, QFont.Weight.DemiBold))
            peak_str = f"PEAK {self.peak_val:.1f}{self.unit}" if self.peak_val > 0 else ""
            painter.drawText(QRectF(0, cy + r + 6, w, 20), Qt.AlignmentFlag.AlignCenter, peak_str)

        # 4. Status Sub-badge (9pt Bold)
        if self.sub_text:
            font_badge = QFont("DejaVu Sans", 9, QFont.Weight.Bold)
            fm_badge = QtGui.QFontMetrics(font_badge)
            text_w = fm_badge.horizontalAdvance(self.sub_text.upper())
            badge_w = min(w - 10, max(110, text_w + 18))
            badge_rect = QRectF(cx - badge_w / 2.0, cy + r + 30, badge_w, 22)
            painter.setPen(QPen(QColor(COLOR_BORDER), 1))
            painter.setBrush(QBrush(QColor(COLOR_BG_SUB)))
            painter.drawRoundedRect(badge_rect, 3, 3)
            painter.setPen(QColor(COLOR_TEXT_SECONDARY))
            painter.setFont(font_badge)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self.sub_text.upper())


# -----------------------------------------------------------------------------
# Custom Widget: Enhanced Telemetry Oscilloscope Line Chart
# -----------------------------------------------------------------------------
class PrecisionTelemetryChart(QtWidgets.QWidget):
    """High-contrast technical oscilloscope chart with large live legends and shaded area fills."""

    def __init__(self, history_len: int = 60, parent=None):
        super().__init__(parent)
        self.history_len = history_len
        self.cpu_temps = collections.deque(maxlen=history_len)
        self.gpu_temps = collections.deque(maxlen=history_len)
        self.fan1_pcts = collections.deque(maxlen=history_len)
        self.fan2_pcts = collections.deque(maxlen=history_len)
        self.fan1_rpm = 0
        self.fan2_rpm = 0
        
        self.setMinimumHeight(180)
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
        pad_l, pad_r, pad_t, pad_b = 42, 20, 32, 24
        plot_w = max(10, w - pad_l - pad_r)
        plot_h = max(10, h - pad_t - pad_b)

        # Panel Background
        painter.fillRect(0, 0, w, h, QColor(COLOR_BG_PANEL))
        painter.setPen(QPen(QColor(COLOR_BORDER), 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        # Technical Grid Lines & Y-Axis Scale (10pt Font)
        for step in [25, 50, 75, 100]:
            y = pad_t + plot_h - (step / 100.0) * plot_h
            painter.setPen(QPen(QColor("#1b2230"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.setFont(QFont("DejaVu Sans Mono", 9, QFont.Weight.Bold))
            painter.drawText(QRectF(0, y - 7, pad_l - 6, 14), Qt.AlignmentFlag.AlignRight, f"{step}")

        # Baseline 0
        y0 = pad_t + plot_h
        painter.setPen(QPen(QColor(COLOR_BORDER), 1))
        painter.drawLine(int(pad_l), int(y0), int(w - pad_r), int(y0))
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        painter.setFont(QFont("DejaVu Sans Mono", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(0, y0 - 7, pad_l - 6, 14), Qt.AlignmentFlag.AlignRight, "0")

        # Telemetry Legend Header (11pt Bold with Large Swatches)
        cur_c = self.cpu_temps[-1] if self.cpu_temps else 0.0
        cur_g = self.gpu_temps[-1] if self.gpu_temps else 0.0
        cur_f1 = self.fan1_pcts[-1] if self.fan1_pcts else 0.0
        cur_f2 = self.fan2_pcts[-1] if self.fan2_pcts else 0.0

        legend_items = [
            (f"CPU: {cur_c:.1f}°C", COLOR_ACCENT, Qt.PenStyle.SolidLine),
            (f"GPU: {cur_g:.1f}°C", COLOR_TEXT_PRIMARY, Qt.PenStyle.DashLine),
            (f"Fan 1: {cur_f1:.0f}% ({self.fan1_rpm} RPM)", COLOR_SUCCESS, Qt.PenStyle.SolidLine),
            (f"Fan 2: {cur_f2:.0f}% ({self.fan2_rpm} RPM)", COLOR_WARNING, Qt.PenStyle.SolidLine)
        ]
        
        painter.setFont(QFont("DejaVu Sans Mono", 10, QFont.Weight.Bold))
        leg_x = pad_l + 6
        for text, color_code, pen_style in legend_items:
            painter.setPen(QPen(QColor(color_code), 3, pen_style))
            painter.drawLine(int(leg_x), 16, int(leg_x + 16), 16)
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.drawText(QRectF(leg_x + 22, 7, 210, 18), Qt.AlignmentFlag.AlignLeft, text)
            leg_x += 230

        if len(self.cpu_temps) < 2:
            return

        # Plot Series
        n = len(self.cpu_temps)
        dx = plot_w / float(self.history_len - 1)
        start_x = pad_l + (self.history_len - n) * dx

        def draw_series(data, color, pen_style=Qt.PenStyle.SolidLine, max_val=100.0, fill=False):
            path = QPainterPath()
            for i, val in enumerate(data):
                x = start_x + i * dx
                ratio = max(0.0, min(1.0, val / max_val))
                y = pad_t + plot_h - (ratio * plot_h)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            if fill:
                fill_path = QPainterPath(path)
                fill_path.lineTo(start_x + (len(data) - 1) * dx, pad_t + plot_h)
                fill_path.lineTo(start_x, pad_t + plot_h)
                fill_path.closeSubpath()
                grad = QLinearGradient(0, pad_t, 0, pad_t + plot_h)
                grad_col = QColor(color)
                grad_col.setAlpha(35)
                grad.setColorAt(0, grad_col)
                grad.setColorAt(1, QColor(0, 0, 0, 0))
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPath(fill_path)

            pen = QPen(QColor(color), 2.2, pen_style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        draw_series(self.cpu_temps, COLOR_ACCENT, fill=True)
        draw_series(self.gpu_temps, COLOR_TEXT_PRIMARY, Qt.PenStyle.DashLine)
        draw_series(self.fan1_pcts, COLOR_SUCCESS)
        draw_series(self.fan2_pcts, COLOR_WARNING)


# -----------------------------------------------------------------------------
# Custom Widget: Precision Thermal Transfer Function Graph
# -----------------------------------------------------------------------------
class PrecisionCurveGraph(QtWidgets.QWidget):
    """Oscilloscope-style curve plot for Fan Curve Engine with large markers and readable text."""

    def __init__(self, points: List[Tuple[int, int]], parent=None):
        super().__init__(parent)
        self.points = points
        self.setMinimumHeight(160)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

    def set_points(self, points: List[Tuple[int, int]]):
        self.points = sorted(points, key=lambda x: x[0])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 42, 20, 18, 28
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
            painter.setFont(QFont("DejaVu Sans Mono", 9, QFont.Weight.Bold))
            painter.drawText(QRectF(0, y - 7, pad_l - 6, 14), Qt.AlignmentFlag.AlignRight, f"{pct}%")

        min_t, max_t = 30.0, 100.0
        for t_mark in [40, 60, 80, 100]:
            x = pad_l + ((t_mark - min_t) / (max_t - min_t)) * plot_w
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.setFont(QFont("DejaVu Sans Mono", 9, QFont.Weight.Bold))
            painter.drawText(QRectF(x - 25, pad_t + plot_h + 6, 50, 16), Qt.AlignmentFlag.AlignCenter, f"{t_mark}°C")

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

        pen = QPen(QColor(COLOR_ACCENT), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Step Handles
        for x, y in point_coords:
            painter.setPen(QPen(QColor(COLOR_BG_DARK), 1.5))
            painter.setBrush(QBrush(QColor(COLOR_ACCENT)))
            painter.drawRect(QRectF(x - 4.5, y - 4.5, 9, 9))


# -----------------------------------------------------------------------------
# Main Application Window
# -----------------------------------------------------------------------------
class DellG15MainWindow(QtWidgets.QMainWindow):
    """Main Application Window with High-Legibility Typography and Clear Visibility."""

    def __init__(self, backend: DellFanBackend):
        super().__init__()
        self.backend = backend
        self.curve_engine = FanCurveEngine(backend)
        
        self.setWindowTitle("Dell G15 5520 Thermal Command Center")
        self.setMinimumSize(1000, 800)
        self.resize(1040, 840)
        
        self._init_ui()
        self._init_system_tray()
        
        # Periodic Telemetry Update (1.5s interval)
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self.refresh_telemetry)
        self.telemetry_timer.start(1500)
        
        self.refresh_telemetry()

    def _init_ui(self):
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
                padding: 10px 32px;
                font-weight: bold;
                font-size: 13px;
                letter-spacing: 0.5px;
                border: 1px solid {COLOR_BORDER};
                border-bottom: none;
                margin-right: 3px;
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
                height: 8px;
                background: {COLOR_BG_SUB};
                border-radius: 4px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLOR_ACCENT};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {COLOR_TEXT_PRIMARY};
                border: 2px solid {COLOR_ACCENT};
                width: 20px;
                margin-top: -7px;
                margin-bottom: -7px;
                border-radius: 10px;
            }}
            QPushButton {{
                background-color: {COLOR_BG_PANEL};
                border: 1px solid {COLOR_BORDER};
                padding: 8px 18px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
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
                spacing: 8px;
                font-size: 12px;
                font-weight: bold;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {COLOR_BORDER};
                background: {COLOR_BG_SUB};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background: {COLOR_ACCENT};
                border-color: {COLOR_ACCENT};
            }}
        """)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

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
        self.status_bar_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-family: 'DejaVu Sans Mono'; padding: 2px 4px; font-weight: bold;")
        main_layout.addWidget(self.status_bar_label)

    def _create_header(self) -> QtWidgets.QWidget:
        header_bar = QtWidgets.QFrame()
        header_bar.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        layout = QtWidgets.QHBoxLayout(header_bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # Brand Signature (Large 18pt font)
        brand_layout = QtWidgets.QVBoxLayout()
        brand_layout.setSpacing(2)
        
        brand_title = QtWidgets.QLabel("DELL G15 5520")
        brand_title.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 18px; font-weight: 900; letter-spacing: 1.5px; font-family: 'DejaVu Sans Mono';")
        
        brand_sub = QtWidgets.QLabel("Intel Core i5-12500H • NVIDIA GeForce RTX 3050")
        brand_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold;")
        
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_sub)
        layout.addLayout(brand_layout)
        
        layout.addStretch()

        # Telemetry Status Readouts (13pt Bold)
        self.badge_freq = QtWidgets.QLabel("CPU -- GHz")
        self.badge_freq.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_TEXT_PRIMARY}; padding: 6px 12px; font-size: 13px; font-weight: bold; font-family: 'DejaVu Sans Mono'; border: 1px solid {COLOR_BORDER}; border-radius: 4px;")
        self.badge_freq.setToolTip("Average CPU Core Clock Frequency and Total Processor Utilization")
        
        self.badge_power = QtWidgets.QLabel("CPU PKG -- W")
        self.badge_power.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_TEXT_PRIMARY}; padding: 6px 12px; font-size: 13px; font-weight: bold; font-family: 'DejaVu Sans Mono'; border: 1px solid {COLOR_BORDER}; border-radius: 4px;")
        self.badge_power.setToolTip("Intel RAPL CPU Package Power (Electrical wattage consumed by CPU cores & uncore)")
        
        self.badge_battery = QtWidgets.QLabel("BAT --%")
        self.badge_battery.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_TEXT_PRIMARY}; padding: 6px 12px; font-size: 13px; font-weight: bold; font-family: 'DejaVu Sans Mono'; border: 1px solid {COLOR_BORDER}; border-radius: 4px;")
        self.badge_battery.setToolTip("Battery State of Charge and AC Power Adapter Status")

        self.btn_perms = QtWidgets.QPushButton("DIRECT CONTROL ACTIVE")
        self.btn_perms.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; font-size: 12px; font-weight: bold; font-family: 'DejaVu Sans Mono'; padding: 6px 14px; border-radius: 4px;")
        self.btn_perms.clicked.connect(self._on_setup_permissions_clicked)

        layout.addWidget(self.badge_freq)
        layout.addWidget(self.badge_power)
        layout.addWidget(self.badge_battery)
        layout.addWidget(self.btn_perms)

        return header_bar

    def _create_dashboard_tab(self) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Profile Controller Strip (38px height, 12pt Bold font)
        prof_bar = QtWidgets.QFrame()
        prof_bar.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        prof_layout = QtWidgets.QHBoxLayout(prof_bar)
        prof_layout.setContentsMargins(12, 8, 12, 8)
        prof_layout.setSpacing(8)

        lbl_prof = QtWidgets.QLabel("OPERATING PROFILE:")
        lbl_prof.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        prof_layout.addWidget(lbl_prof)

        self.btn_mode_quiet = QtWidgets.QPushButton("QUIET")
        self.btn_mode_balanced = QtWidgets.QPushButton("BALANCED")
        self.btn_mode_perf = QtWidgets.QPushButton("PERFORMANCE")
        self.btn_mode_custom = QtWidgets.QPushButton("CUSTOM")
        self.btn_mode_gmode = QtWidgets.QPushButton("G-MODE TURBO")

        for btn in [self.btn_mode_quiet, self.btn_mode_balanced, self.btn_mode_perf, self.btn_mode_custom]:
            btn.setCheckable(True)
            btn.setMinimumHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLOR_BG_SUB};
                    border: 1px solid {COLOR_BORDER};
                    color: {COLOR_TEXT_SECONDARY};
                    font-size: 12px;
                    font-weight: bold;
                    padding: 6px 16px;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border-color: {COLOR_ACCENT};
                    color: {COLOR_TEXT_PRIMARY};
                }}
                QPushButton:checked {{
                    background: {COLOR_BG_ACTIVE};
                    border: 2px solid {COLOR_ACCENT};
                    color: {COLOR_ACCENT};
                }}
            """)

        # Tactile Crimson G-Mode Turbo Button
        self.btn_mode_gmode.setCheckable(True)
        self.btn_mode_gmode.setMinimumHeight(38)
        self.btn_mode_gmode.setStyleSheet(f"""
            QPushButton {{
                background: #2b1118;
                border: 1px solid #571b29;
                color: #ff6685;
                font-size: 12px;
                font-weight: 900;
                padding: 6px 18px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: #3d1420;
                border-color: {COLOR_ALERT};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background: {COLOR_ALERT};
                border: 2px solid #ffffff;
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
        wb_frame.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        wb_layout = QtWidgets.QHBoxLayout(wb_frame)
        wb_layout.setContentsMargins(12, 10, 12, 10)
        wb_layout.setSpacing(14)

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
        ctrl_frame.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        ctrl_layout = QtWidgets.QVBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(14, 10, 14, 10)
        ctrl_layout.setSpacing(8)

        c_top = QtWidgets.QHBoxLayout()
        c_title = QtWidgets.QLabel("MANUAL FAN BOOST CONTROL")
        c_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        
        self.chk_auto_power = QtWidgets.QCheckBox("AUTO AC/BATTERY")
        self.chk_auto_power.setChecked(True)
        self.chk_auto_power.setToolTip("Automatically switch to Quiet on Battery and Balanced on AC Main")
        self.chk_auto_power.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-family: 'DejaVu Sans Mono'; font-weight: bold;")
        self.chk_auto_power.toggled.connect(self._on_auto_power_toggled)

        self.chk_sync_fans = QtWidgets.QCheckBox("SYNCHRONIZE CHANNELS")
        self.chk_sync_fans.setChecked(True)
        self.chk_sync_fans.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-family: 'DejaVu Sans Mono'; font-weight: bold;")
        
        c_top.addWidget(c_title)
        c_top.addStretch()
        c_top.addWidget(self.chk_auto_power)
        c_top.addWidget(self.chk_sync_fans)
        ctrl_layout.addLayout(c_top)

        # CPU Row
        r1 = QtWidgets.QHBoxLayout()
        lbl1 = QtWidgets.QLabel("CPU FAN BOOST:")
        lbl1.setFixedWidth(140)
        lbl1.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        
        self.slider_cpu = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_cpu.setRange(0, 100)
        self.slider_cpu.setValue(0)
        
        self.lbl_cpu_val = QtWidgets.QLabel("0%")
        self.lbl_cpu_val.setFixedWidth(58)
        self.lbl_cpu_val.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_ACCENT}; font-family: 'DejaVu Sans Mono'; font-weight: bold; font-size: 13px; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 3px 6px;")
        self.lbl_cpu_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        r1.addWidget(lbl1)
        r1.addWidget(self.slider_cpu)
        r1.addWidget(self.lbl_cpu_val)
        ctrl_layout.addLayout(r1)

        # GPU Row
        r2 = QtWidgets.QHBoxLayout()
        lbl2 = QtWidgets.QLabel("GPU FAN BOOST:")
        lbl2.setFixedWidth(140)
        lbl2.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        
        self.slider_gpu = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.slider_gpu.setRange(0, 100)
        self.slider_gpu.setValue(0)
        
        self.lbl_gpu_val = QtWidgets.QLabel("0%")
        self.lbl_gpu_val.setFixedWidth(58)
        self.lbl_gpu_val.setStyleSheet(f"background: {COLOR_BG_SUB}; color: {COLOR_TEXT_PRIMARY}; font-family: 'DejaVu Sans Mono'; font-weight: bold; font-size: 13px; border: 1px solid {COLOR_BORDER}; border-radius: 4px; padding: 3px 6px;")
        self.lbl_gpu_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        r2.addWidget(lbl2)
        r2.addWidget(self.slider_gpu)
        r2.addWidget(self.lbl_gpu_val)
        ctrl_layout.addLayout(r2)

        # Presets Bar
        r3 = QtWidgets.QHBoxLayout()
        lbl_p = QtWidgets.QLabel("PRESETS:")
        lbl_p.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        r3.addWidget(lbl_p)

        for pct in [0, 25, 50, 75, 100]:
            name = "AUTO (0%)" if pct == 0 else (f"{pct}% MAX" if pct == 100 else f"{pct}% BOOST")
            btn = QtWidgets.QPushButton(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLOR_BG_SUB};
                    border: 1px solid {COLOR_BORDER};
                    color: {COLOR_TEXT_SECONDARY};
                    font-size: 11px;
                    font-family: 'DejaVu Sans Mono';
                    font-weight: bold;
                    padding: 5px 14px;
                    border-radius: 4px;
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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_panel = QtWidgets.QFrame()
        top_panel.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")
        t_layout = QtWidgets.QHBoxLayout(top_panel)
        t_layout.setContentsMargins(14, 10, 14, 10)
        t_layout.setSpacing(12)

        lbl_curve = QtWidgets.QLabel("CURVE PRESET:")
        lbl_curve.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold; font-family: 'DejaVu Sans Mono';")
        t_layout.addWidget(lbl_curve)

        self.combo_presets = QtWidgets.QComboBox()
        self.combo_presets.setStyleSheet(f"""
            QComboBox {{
                background: {COLOR_BG_SUB};
                color: {COLOR_TEXT_PRIMARY};
                padding: 6px 14px;
                border: 1px solid {COLOR_BORDER};
                font-size: 12px;
                font-family: 'DejaVu Sans Mono';
                font-weight: bold;
                border-radius: 4px;
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
        self.btn_toggle_curve.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; padding: 8px 20px; font-weight: bold; font-size: 12px; font-family: 'DejaVu Sans Mono'; border-radius: 4px;")
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
                font-size: 13px;
                border-radius: 4px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_BG_SUB};
                color: {COLOR_TEXT_SECONDARY};
                font-weight: bold;
                font-family: 'DejaVu Sans Mono';
                font-size: 11px;
                border: 1px solid {COLOR_BORDER};
                padding: 8px;
            }}
        """)
        self._populate_curve_table()
        self.combo_presets.currentTextChanged.connect(self._on_preset_changed)
        layout.addWidget(self.curve_table)

        btn_save = QtWidgets.QPushButton("APPLY AND SAVE CUSTOM CURVE")
        btn_save.setStyleSheet(f"background: {COLOR_BG_PANEL}; color: {COLOR_ACCENT}; border: 1px solid {COLOR_BORDER}; padding: 8px 18px; font-size: 12px; font-family: 'DejaVu Sans Mono'; border-radius: 4px;")
        btn_save.clicked.connect(self._save_custom_curve_table)
        layout.addWidget(btn_save)

        return tab

    def _create_sensors_tab(self) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)

        self.sensor_tree = QtWidgets.QTreeWidget()
        self.sensor_tree.setHeaderLabels(["HARDWARE SUBSYSTEM", "SENSOR METRIC", "TELEMETRY VALUE"])
        self.sensor_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLOR_BG_PANEL};
                border: 1px solid {COLOR_BORDER};
                color: {COLOR_TEXT_PRIMARY};
                font-size: 13px;
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_BG_SUB};
                color: {COLOR_TEXT_SECONDARY};
                font-weight: bold;
                font-family: 'DejaVu Sans Mono';
                font-size: 11px;
                border: 1px solid {COLOR_BORDER};
                padding: 8px;
            }}
            QTreeWidget::item {{
                padding: 4px;
            }}
        """)
        self.sensor_tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.sensor_tree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.sensor_tree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)

        # Build initial items once to prevent scroll jump and collapse bugs
        self.sensor_items = {}
        
        # Thermal
        t_root = QtWidgets.QTreeWidgetItem(self.sensor_tree, ["THERMAL ZONES", "Subsystem Overview", "All Active Thermal Zones"])
        self.sensor_items["cpu_temp"] = QtWidgets.QTreeWidgetItem(t_root, ["", "CPU Package Temperature", "--"])
        self.sensor_items["gpu_temp"] = QtWidgets.QTreeWidgetItem(t_root, ["", "GPU Core Temperature", "--"])
        self.sensor_items["ssd_temp"] = QtWidgets.QTreeWidgetItem(t_root, ["", "NVMe SSD Solid State Drive", "--"])
        self.sensor_items["ram_temp"] = QtWidgets.QTreeWidgetItem(t_root, ["", "DDR5 System RAM Module", "--"])
        self.sensor_items["ambient_temp"] = QtWidgets.QTreeWidgetItem(t_root, ["", "Motherboard Ambient Sensor", "--"])
        self.sensor_items["wifi_temp"] = QtWidgets.QTreeWidgetItem(t_root, ["", "Intel Wi-Fi 6 Adapter", "--"])
        
        self.core_temp_items = []
        for i in range(16):
            c_item = QtWidgets.QTreeWidgetItem(t_root, ["", f"CPU Core #{i} Temperature", "--"])
            c_item.setHidden(True)
            self.core_temp_items.append(c_item)

        # Cooling
        f_root = QtWidgets.QTreeWidgetItem(self.sensor_tree, ["COOLING SUBSYSTEM", "Tachometers", "Active Dual Fan System"])
        self.sensor_items["fan1_rpm"] = QtWidgets.QTreeWidgetItem(f_root, ["", "CPU Fan Speed", "--"])
        self.sensor_items["fan1_max"] = QtWidgets.QTreeWidgetItem(f_root, ["", "CPU Fan Maximum Limit", "--"])
        self.sensor_items["fan1_boost"] = QtWidgets.QTreeWidgetItem(f_root, ["", "CPU Fan Boost Register", "--"])
        self.sensor_items["fan2_rpm"] = QtWidgets.QTreeWidgetItem(f_root, ["", "GPU Fan Speed", "--"])
        self.sensor_items["fan2_max"] = QtWidgets.QTreeWidgetItem(f_root, ["", "GPU Fan Maximum Limit", "--"])
        self.sensor_items["fan2_boost"] = QtWidgets.QTreeWidgetItem(f_root, ["", "GPU Fan Boost Register", "--"])

        # Power & Platform
        p_root = QtWidgets.QTreeWidgetItem(self.sensor_tree, ["POWER & PLATFORM", "Management Profile", "Dell ACPI / Alienware WMI"])
        self.sensor_items["active_profile"] = QtWidgets.QTreeWidgetItem(p_root, ["", "Active Thermal Profile", "--"])
        self.sensor_items["is_g_mode"] = QtWidgets.QTreeWidgetItem(p_root, ["", "G-Mode Turbo Status", "--"])
        self.sensor_items["cpu_freq"] = QtWidgets.QTreeWidgetItem(p_root, ["", "CPU Core Clock Speed", "--"])
        self.sensor_items["cpu_load"] = QtWidgets.QTreeWidgetItem(p_root, ["", "CPU Total Utilization", "--"])
        self.sensor_items["cpu_power"] = QtWidgets.QTreeWidgetItem(p_root, ["", "CPU Package Power Draw", "--"])
        self.sensor_items["ac_status"] = QtWidgets.QTreeWidgetItem(p_root, ["", "AC Power Adapter", "--"])
        self.sensor_items["battery_pct"] = QtWidgets.QTreeWidgetItem(p_root, ["", "Battery State of Charge", "--"])
        self.sensor_items["battery_volt"] = QtWidgets.QTreeWidgetItem(p_root, ["", "Battery Voltage", "--"])
        self.sensor_items["battery_rate"] = QtWidgets.QTreeWidgetItem(p_root, ["", "Battery Power Flow", "--"])

        self.sensor_tree.expandAll()
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
        tray_menu.setStyleSheet(f"background-color: {COLOR_BG_PANEL}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; font-size: 12px;")

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

        b1_pct = int(f1_boost)
        b2_pct = int(f2_boost)

        sub_c = "NORMAL" if c_temp < 70 else ("ELEVATED" if c_temp < 85 else "HIGH LOAD")
        sub_g = "NORMAL" if g_temp < 65 else ("ELEVATED" if g_temp < 80 else "HIGH LOAD")

        sub_f1 = f"MANUAL {b1_pct}%" if f1_boost > 0 else f"AUTO {f1_pct:.0f}%"
        sub_f2 = f"MANUAL {b2_pct}%" if f2_boost > 0 else f"AUTO {f2_pct:.0f}%"

        self.gauge_cpu_temp.set_value(c_temp, peak_c, sub_c)
        self.gauge_gpu_temp.set_value(g_temp, peak_g, sub_g)
        self.gauge_cpu_fan.set_value(f1_rpm, 0.0, sub_f1)
        self.gauge_gpu_fan.set_value(f2_rpm, 0.0, sub_f2)

        # Sync sliders with hardware state if user is not actively dragging
        if not self.slider_cpu.isSliderDown() and not self.slider_gpu.isSliderDown():
            self.slider_cpu.blockSignals(True)
            self.slider_cpu.setValue(b1_pct)
            self.lbl_cpu_val.setText(f"{b1_pct}%")
            self.slider_cpu.blockSignals(False)

            self.slider_gpu.blockSignals(True)
            self.slider_gpu.setValue(b2_pct)
            self.lbl_gpu_val.setText(f"{b2_pct}%")
            self.slider_gpu.blockSignals(False)

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
            self.btn_perms.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; font-size: 11px; font-weight: bold; font-family: 'DejaVu Sans Mono'; padding: 6px 14px; border-radius: 4px;")
            self.btn_perms.setEnabled(False)
        else:
            self.btn_perms.setText("SETUP PERMISSIONS")
            self.btn_perms.setStyleSheet(f"background: #2b1118; color: {COLOR_ALERT}; border: 1px solid #571b29; font-size: 11px; font-weight: bold; font-family: 'DejaVu Sans Mono'; padding: 6px 14px; border-radius: 4px;")
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

        # 6. Sensor Tree (In-place update)
        self._refresh_sensor_tree(telem)

    def _refresh_sensor_tree(self, telem: dict):
        if not hasattr(self, "sensor_items"):
            return

        self.sensor_items["cpu_temp"].setText(2, f"{telem['cpu_temp']} °C (Peak: {telem['peak_cpu_temp']} °C)")
        self.sensor_items["gpu_temp"].setText(2, f"{telem['gpu_temp']} °C (Peak: {telem['peak_gpu_temp']} °C)")
        
        if telem.get("ssd_temp") is not None:
            self.sensor_items["ssd_temp"].setText(2, f"{telem['ssd_temp']} °C")
            self.sensor_items["ssd_temp"].setHidden(False)
        else:
            self.sensor_items["ssd_temp"].setHidden(True)

        if telem.get("ram_temp") is not None:
            self.sensor_items["ram_temp"].setText(2, f"{telem['ram_temp']} °C")
            self.sensor_items["ram_temp"].setHidden(False)
        else:
            self.sensor_items["ram_temp"].setHidden(True)

        if telem.get("ambient_temp") is not None:
            self.sensor_items["ambient_temp"].setText(2, f"{telem['ambient_temp']} °C")
            self.sensor_items["ambient_temp"].setHidden(False)
        else:
            self.sensor_items["ambient_temp"].setHidden(True)

        if telem.get("wifi_temp") is not None:
            self.sensor_items["wifi_temp"].setText(2, f"{telem['wifi_temp']} °C")
            self.sensor_items["wifi_temp"].setHidden(False)
        else:
            self.sensor_items["wifi_temp"].setHidden(True)

        core_temps = telem.get("core_temps", [])
        for i, c_item in enumerate(self.core_temp_items):
            if i < len(core_temps):
                c_item.setText(2, f"{core_temps[i]} °C")
                c_item.setHidden(False)
            else:
                c_item.setHidden(True)

        self.sensor_items["fan1_rpm"].setText(2, f"{telem['fan1_rpm']} RPM ({telem['fan1_pct']}%)")
        self.sensor_items["fan1_max"].setText(2, f"{telem['fan1_max']} RPM")
        self.sensor_items["fan1_boost"].setText(2, f"{telem['fan1_boost']}%")

        self.sensor_items["fan2_rpm"].setText(2, f"{telem['fan2_rpm']} RPM ({telem['fan2_pct']}%)")
        self.sensor_items["fan2_max"].setText(2, f"{telem['fan2_max']} RPM")
        self.sensor_items["fan2_boost"].setText(2, f"{telem['fan2_boost']}%")

        self.sensor_items["active_profile"].setText(2, telem["active_profile"].upper())
        self.sensor_items["is_g_mode"].setText(2, "ACTIVE (100% Fans)" if telem["is_g_mode"] else "INACTIVE")
        self.sensor_items["cpu_freq"].setText(2, f"{telem.get('cpu_freq_ghz', 0.0)} GHz")
        self.sensor_items["cpu_load"].setText(2, f"{telem.get('cpu_usage_pct', 0.0)}%")
        self.sensor_items["cpu_power"].setText(2, f"{telem.get('cpu_power_w', 0.0)} Watts")
        self.sensor_items["ac_status"].setText(2, "Connected" if telem.get("is_ac_online") else "Disconnected")

        if telem.get("battery_pct") is not None:
            self.sensor_items["battery_pct"].setText(2, f"{telem['battery_pct']}%")
            self.sensor_items["battery_pct"].setHidden(False)
        else:
            self.sensor_items["battery_pct"].setHidden(True)

        if telem.get("battery_voltage_v") is not None:
            self.sensor_items["battery_volt"].setText(2, f"{telem['battery_voltage_v']} Volts")
            self.sensor_items["battery_volt"].setHidden(False)
        else:
            self.sensor_items["battery_volt"].setHidden(True)

        if telem.get("battery_rate_w") is not None:
            self.sensor_items["battery_rate"].setText(2, f"{telem['battery_rate_w']} Watts")
            self.sensor_items["battery_rate"].setHidden(False)
        else:
            self.sensor_items["battery_rate"].setHidden(True)

    # -------------------------------------------------------------------------
    # Mode & Fan Actions
    # -------------------------------------------------------------------------
    def _on_auto_power_toggled(self, checked: bool):
        self.backend.auto_power_switch_enabled = checked
        self.status_bar_label.setText(f"AUTO POWER-SOURCE ADAPTATION: {'ACTIVE' if checked else 'DISABLED'}")

    def _set_mode(self, mode: str):
        if self.curve_engine.is_running:
            self.curve_engine.stop()
            self.btn_toggle_curve.setChecked(False)
            self.btn_toggle_curve.setText("ENABLE SMART CURVE")

        self.backend.set_thermal_profile(mode)
        self.status_bar_label.setText(f"PROFILE APPLIED: {mode.upper()}")
        DellFanBackend.send_osd_notification("Dell G15 Thermal Profile", f"Switched to {mode.upper()} mode", "normal")
        self.refresh_telemetry()

    def _toggle_gmode(self):
        telem = self.backend.get_telemetry()
        new_state = not telem["is_g_mode"]
        self.backend.set_g_mode(new_state)
        msg = "G-MODE TURBO: ENGAGED (100% Max Fans)" if new_state else "G-MODE TURBO: DISENGAGED (Balanced)"
        self.status_bar_label.setText(msg)
        DellFanBackend.send_osd_notification("Dell G15: Game Shift (G-Key)", msg, "critical" if new_state else "normal")
        self.refresh_telemetry()

    def _apply_slider_preset(self, pct: int):
        if self.curve_engine.is_running:
            self.curve_engine.stop()
            self.btn_toggle_curve.setChecked(False)
            self.btn_toggle_curve.setText("ENABLE SMART CURVE")
            self.btn_toggle_curve.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; padding: 8px 20px; font-weight: bold; font-size: 12px; font-family: 'DejaVu Sans Mono'; border-radius: 4px;")

        self.slider_cpu.setValue(pct)
        if self.chk_sync_fans.isChecked():
            self.slider_gpu.setValue(pct)
        self.backend.set_fan_boost(pct, pct)
        self.status_bar_label.setText(f"MANUAL FAN BOOST APPLIED: {pct}%" if pct > 0 else "FAN CONTROL: AUTOMATIC FIRMWARE")
        self.refresh_telemetry()

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
        self.status_bar_label.setText(f"MANUAL FAN BOOST: CPU {val}%" if val > 0 else "FAN CONTROL: AUTOMATIC FIRMWARE")

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
        self.status_bar_label.setText(f"MANUAL FAN BOOST: GPU {val}%" if val > 0 else "FAN CONTROL: AUTOMATIC FIRMWARE")

    # -------------------------------------------------------------------------
    # Fan Curve Engine Actions
    # -------------------------------------------------------------------------
    def _toggle_curve_engine(self, checked: bool):
        if checked:
            self.curve_engine.start()
            self.btn_toggle_curve.setText("STOP SMART CURVE")
            self.btn_toggle_curve.setStyleSheet(f"background: #2b1118; color: {COLOR_ALERT}; border: 1px solid #571b29; padding: 8px 20px; font-weight: bold; font-size: 12px; font-family: 'DejaVu Sans Mono'; border-radius: 4px;")
            self.status_bar_label.setText("SMART FAN CURVE CONTROLLER ENGAGED")
        else:
            self.curve_engine.stop()
            self.btn_toggle_curve.setText("ENABLE SMART CURVE")
            self.btn_toggle_curve.setStyleSheet(f"background: #0f241d; color: {COLOR_SUCCESS}; border: 1px solid #1c523d; padding: 8px 20px; font-weight: bold; font-size: 12px; font-family: 'DejaVu Sans Mono'; border-radius: 4px;")
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


def create_qapplication():
    """Create QApplication while cleanly suppressing external GTK CSS theme parser warnings."""
    try:
        stderr_fd = sys.stderr.fileno()
        saved_stderr = os.dup(stderr_fd)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, stderr_fd)
        os.close(devnull)
        
        app = QtWidgets.QApplication(sys.argv)
        
        os.dup2(saved_stderr, stderr_fd)
        os.close(saved_stderr)
        return app
    except Exception:
        return QtWidgets.QApplication(sys.argv)


def main():
    app = create_qapplication()
    app.setApplicationName("Dell G15 Fan Command Center")

    # Single-instance enforcement to prevent duplicate tray icons and duplicate polling loops
    socket_name = "DellG15FanControllerSingleInstanceSocket"
    socket = QLocalSocket()
    socket.connectToServer(socket_name)
    if socket.waitForConnected(300):
        # Existing instance found! Send message to bring its window to the front
        socket.write(b"SHOW\n")
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        sys.exit(0)

    # Primary instance: create server
    local_server = QLocalServer()
    local_server.removeServer(socket_name)
    local_server.listen(socket_name)

    backend = DellFanBackend()
    window = DellG15MainWindow(backend)

    def handle_new_instance():
        sock = local_server.nextPendingConnection()
        if sock:
            def on_read():
                data = sock.readAll().data().decode().strip()
                if "SHOW" in data:
                    window.showNormal()
                    window.raise_()
                    window.activateWindow()
            sock.readyRead.connect(on_read)

    local_server.newConnection.connect(handle_new_instance)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
