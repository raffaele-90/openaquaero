# AquaControl
# Copyright (C) 2026 Raffaele Schiavone
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QProgressBar, QFrame, QLayout, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon
from config_manager import global_config

def to_roman(num):
    if num == 0:
        return "N"  # N = Nulla/Nihil
    if not isinstance(num, int) or num < 0:
        return str(num)

    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1
    return roman_num

class AquaeroOSD(QWidget):
    """
    Widget OSD desktop flottante.
    Implementa il riposizionamento tramite trascinamento e l'aggiornamento dinamico della telemetria.
    """
    position_changed = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.scale = 1.0
        self.max_rows = 8
        self.bg_opacity = 220
        self.color_names = "#cdd6f4"
        self.color_values = "#00e5ff"
        self.color_badges = "#00e5ff"
        self.custom_font = None

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint |
                            Qt.Tool | Qt.BypassWindowManagerHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._emit_position)

        self.layout = QVBoxLayout(self)
        self.layout.setSizeConstraint(QLayout.SetFixedSize)

        self.bg_widget = QFrame(self)
        self.bg_widget.setObjectName("osd_bg")
        self.bg_layout = QVBoxLayout(self.bg_widget)
        self.bg_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.layout.addWidget(self.bg_widget)

        self.header_layout = QHBoxLayout()
        self.icon_lbl = QLabel() # Inizializzata vuota, il pixmap si calibra nello scaling
        is_la = global_config.get("lang") == "la"
        osd_title = "PRAECEPTA TABULAE FLUCTUANTIS" if is_la else "AQUACONTROL OSD"
        self.title_lbl = QLabel(osd_title)
        self.title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.header_layout.addWidget(self.icon_lbl)
        self.header_layout.addWidget(self.title_lbl)
        self.bg_layout.addLayout(self.header_layout)

        self.header_line = QFrame()
        self.header_line.setFrameShape(QFrame.HLine)
        self.bg_layout.addWidget(self.header_line)

        self.grid_layout = QGridLayout()
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.bg_layout.addLayout(self.grid_layout)

        self.sensor_ui = []
        self.apply_scaling()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.windowHandle():
                self.windowHandle().startSystemMove()
            event.accept()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.save_timer.start(500)

    def _emit_position(self):
        self.position_changed.emit(self.x(), self.y())

    def set_scale(self, new_scale):
        self.scale = new_scale
        self.apply_scaling()

    def set_customization(self, scale=None, opacity=None, c_names=None, c_values=None, c_badges=None, font=None, max_rows=None):
        if scale is not None: self.scale = scale
        if opacity is not None: self.bg_opacity = opacity
        if c_names is not None: self.color_names = c_names
        if c_values is not None: self.color_values = c_values
        if c_badges is not None: self.color_badges = c_badges
        if font is not None: self.custom_font = font
        if max_rows is not None: self.max_rows = max_rows

        self._force_rebuild = True
        self.apply_scaling()

    def apply_scaling(self):
        s = self.scale

        if self.custom_font:
            self.title_lbl.setFont(self.custom_font)

        self.layout.setContentsMargins(int(10*s), int(10*s), int(10*s), int(10*s))

        is_latin = global_config.get("lang") == "la"

        if is_latin:
            bg_color = f"rgba(45, 20, 20, {self.bg_opacity})"
            border_color = "rgba(255, 215, 0, 80)"           # Oro
        else:
            bg_color = f"rgba(35, 38, 41, {self.bg_opacity})"
            border_color = "rgba(255, 255, 255, 30)"

        self.bg_widget.setStyleSheet(
            f"#osd_bg {{ background-color: {bg_color}; "
            f"border-radius: {int(8*s)}px; "
            f"border: {max(1, int(1*s))}px solid {border_color}; }}"
        )

        self.bg_layout.setContentsMargins(int(15*s), int(12*s), int(15*s), int(12*s))
        self.bg_layout.setSpacing(int(10*s))

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "panoramic.svg")
        self.icon_lbl.setPixmap(QIcon(icon_path).pixmap(int(16*s), int(16*s)))
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")

        c_badge_title = "#FFD700" if is_latin else self.color_badges

        self.title_lbl.setStyleSheet(
            f"color: {c_badge_title}; font-weight: 900; "
            f"font-size: {int(14*s)}px; letter-spacing: {int(1.5*s)}px; "
            f"background: transparent; border: none;"
        )
        self.header_line.setStyleSheet(
            f"background-color: rgba(255, 255, 255, 20); "
            f"border: none; max-height: {max(1, int(1*s))}px; margin-bottom: {int(4*s)}px;"
        )

        self.grid_layout.setHorizontalSpacing(int(14*s))
        self.grid_layout.setVerticalSpacing(int(8*s))

        self._force_rebuild = True

    def update_data(self, hardware_data):
        s = self.scale

        if not hardware_data:
            self._clear_grid()
            return

        is_latin = global_config.get("lang") == "la"

        # Override Colori Imperium
        c_badge_bg = "#5C1A1A" if is_latin else self.color_badges
        c_badge_txt = "#FFD700" if is_latin else "#11111b"
        c_names = "#FFD700" if is_latin else self.color_names
        c_values = "#FFD700" if is_latin else self.color_values

        if not hasattr(self, 'sensor_ui') or len(self.sensor_ui) != len(hardware_data) or getattr(self, '_force_rebuild', False):
            self._force_rebuild = False
            self._clear_grid()
            self.sensor_ui = []

            for i, item in enumerate(hardware_data):
                row = i % self.max_rows
                base_col = (i // self.max_rows) * 5

                lbl_badge = QLabel()
                lbl_badge.setAlignment(Qt.AlignCenter)
                lbl_badge.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
                if self.custom_font: lbl_badge.setFont(self.custom_font)
                lbl_badge.setStyleSheet(
                    f"background-color: {c_badge_bg}; color: {c_badge_txt}; "
                    f"font-weight: 900; font-size: {int(10*s)}px; "
                    f"border-radius: {int(3*s)}px; "
                    f"padding: {int(2*s)}px {int(5*s)}px;"
                )
                self.grid_layout.addWidget(lbl_badge, row, base_col + 0)

                lbl_name = QLabel()
                lbl_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                lbl_name.setMinimumWidth(int(90*s))
                if self.custom_font: lbl_name.setFont(self.custom_font)
                lbl_name.setStyleSheet(f"color: {c_names}; font-weight: 700; font-size: {int(12*s)}px;")
                self.grid_layout.addWidget(lbl_name, row, base_col + 1)

                lbl_val = QLabel()
                lbl_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                lbl_val.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
                self.grid_layout.addWidget(lbl_val, row, base_col + 2)

                rpm_volt_container = QWidget()
                rpm_volt_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
                rpm_volt_layout = QVBoxLayout(rpm_volt_container)
                rpm_volt_layout.setContentsMargins(0, 0, 0, 0)
                rpm_volt_layout.setSpacing(0)

                lbl_rpm = QLabel()
                lbl_rpm.setAlignment(Qt.AlignRight | Qt.AlignBottom)
                lbl_volt = QLabel()
                lbl_volt.setAlignment(Qt.AlignRight | Qt.AlignTop)

                rpm_volt_layout.addWidget(lbl_rpm)
                rpm_volt_layout.addWidget(lbl_volt)
                self.grid_layout.addWidget(rpm_volt_container, row, base_col + 3)

                prog_bar = QProgressBar()
                prog_bar.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
                prog_bar.setRange(0, 100)
                prog_bar.setTextVisible(True)
                prog_bar.setFormat("%p%")
                prog_bar.setFixedHeight(int(16*s))
                prog_bar.setMinimumWidth(int(65*s))
                prog_bar.setStyleSheet(
                    f"QProgressBar {{ border: 1px solid #313244; border-radius: {int(3*s)}px; "
                    f"background-color: #181825; text-align: center; color: #cdd6f4; "
                    f"font-weight: 800; font-size: {int(10*s)}px; font-family: monospace; }} "
                    f"QProgressBar::chunk {{ background-color: {c_badge_bg}; border-radius: {int(2*s)}px; }}"
                )

                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)

                self.grid_layout.addWidget(prog_bar, row, base_col + 4)
                self.grid_layout.addWidget(spacer, row, base_col + 4)

                self.sensor_ui.append({
                    'badge': lbl_badge,
                    'name': lbl_name,
                    'val': lbl_val,
                    'volt': lbl_volt,
                    'rpm': lbl_rpm,
                    'prog': prog_bar,
                    'spacer': spacer
                })

        for i, item in enumerate(hardware_data):
            ui = self.sensor_ui[i]

            name_text = item.get('name', '').upper()
            display_name = name_text.replace(" VOLTS", "")
            rpm = item.get('rpm')
            pwm = item.get('pwm')
            temp = item.get('temp')
            volt = item.get('volt')
            flow = item.get('flow')

            if "VOLT" in name_text: badge_txt = "VLT"
            elif flow is not None: badge_txt = "FLW"
            elif rpm is not None: badge_txt = "FAN"
            elif pwm is not None: badge_txt = "PWR"
            elif temp is not None: badge_txt = "TMP"
            else: badge_txt = "SYS"

            if is_latin:
                if badge_txt == "FAN": badge_txt = "VEN"
                elif badge_txt == "TMP": badge_txt = "CAL"
                elif badge_txt == "PWR": badge_txt = "VIS"
                elif badge_txt == "VLT": badge_txt = "TEN"
                elif badge_txt == "FLW": badge_txt = "FLM"  # Flumen

            ui['badge'].setText(badge_txt)
            ui['name'].setText(display_name)

            if temp is not None:
                if is_latin and badge_txt != "VLT":
                    ui['val'].setText(f"{to_roman(int(temp))} °G")
                else:
                    unit = "V" if badge_txt == "VLT" else "°C"
                    ui['val'].setText(f"{temp:.1f} {unit}")
                ui['val'].setStyleSheet(f"color: {c_values}; font-family: monospace; font-weight: 800; font-size: {int(13*s)}px;")

            elif flow is not None:
                if is_latin:
                    ui['val'].setText(f"{to_roman(int(flow))} L/h")
                else:
                    ui['val'].setText(f"{flow:.1f} L/h")
                ui['val'].setStyleSheet(f"color: {c_values}; font-family: monospace; font-weight: 800; font-size: {int(13*s)}px;")
            else:
                ui['val'].setText("--")
                ui['val'].setStyleSheet(f"color: #45475a;")

            if volt is not None:
                if is_latin:
                    v_int = int(volt)
                    v_dec = int(round((volt - v_int) * 100))
                    ui['volt'].setText(f"{to_roman(v_int)},{to_roman(v_dec)} V")
                else:
                    ui['volt'].setText(f"{volt:.1f} V")

                col_volt = c_values if is_latin else "#f9e2af"
                ui['volt'].setStyleSheet(f"color: {col_volt}; font-family: monospace; font-weight: 800; font-size: {int(10*s)}px;")
                ui['volt'].show()
            else:
                ui['volt'].hide()

            if rpm is not None:
                if is_latin:
                    ui['rpm'].setText(f"{to_roman(int(rpm))} RPM")
                else:
                    ui['rpm'].setText(f"{rpm} RPM")

                col_rpm = c_values if is_latin else "#94e2d5"
                ui['rpm'].setStyleSheet(f"color: {col_rpm}; font-family: monospace; font-weight: 800; font-size: {int(10*s)}px;")
                ui['rpm'].show()
            else:
                ui['rpm'].hide()

            if pwm is not None:
                ui['prog'].show()
                ui['spacer'].hide()
                ui['prog'].setValue(int(pwm))
                if is_latin:
                    ui['prog'].setFormat(f"{to_roman(int(pwm))}")
                else:
                    ui['prog'].setFormat("%p%")
            else:
                ui['prog'].hide()
                ui['spacer'].show()

    def _clear_grid(self):
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
        self.sensor_ui = []

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
