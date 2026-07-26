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
import math
import colorsys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                               QScrollArea, QGridLayout, QFrame, QGroupBox,
                               QComboBox, QCheckBox, QPushButton, QFormLayout,
                               QSpinBox, QDoubleSpinBox, QLineEdit, QColorDialog,
                               QFontDialog, QMessageBox, QDialog, QDialogButtonBox,
                               QSizePolicy)
from PySide6.QtCore import Qt, QTimer, Signal, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QCursor, QIcon, QPainter, QConicalGradient, QRadialGradient, QBrush, QPen

from config_manager import global_config, save_config
from i18n import T
from farbwerk360_effects import EFFECTS, Farbwerk360EffectsEngine
from ui_widgets import format_temp, SparklineWidget, PWMFillBar, to_roman, RomanSpinBox, RomanDoubleSpinBox
from guide_texts import get_guide_text

def get_accent():
    return "#FFD700" if global_config.get("lang") == "la" else "#00e5ff"

FLOW_PRESETS = {
    "User defined": {},
    "Digmesa 5.6 mm (53061)": {
        "Water": {"N/A": 256},
        "DP Ultra": {"N/A": 262}
    },
    "Digmesa 3.3 mm (53024)": {
        "Water": {"N/A": 509},
        "DP Ultra": {"N/A": 522}
    },
    "Aqua Computer high flow (53068)": {
        "Water": {"Inner diameter <= 7mm": 159, "Inner diameter > 7mm": 153},
        "DP Ultra": {"Inner diameter <= 7mm": 163, "Inner diameter > 7mm": 157}
    },
    "Aqua Computer high flow LT (53291)": {
        "Water": {"Inner diameter <= 7mm": 173, "Inner diameter > 7mm": 164},
        "DP Ultra": {"Inner diameter <= 7mm": 177, "Inner diameter > 7mm": 167}
    },
    "Aqua Computer high flow 2 (53292)": {
        "Water": {"Inner diameter <= 7mm": 148, "Inner diameter > 7mm": 144},
        "DP Ultra": {"Inner diameter <= 7mm": 151, "Inner diameter > 7mm": 147}
    }
}

def _create_section_header(icon_filename, text, text_color="#cdd6f4", icon_color=None):
    """Crea una riga orizzontale con Icona SVG e Testo, gestendo i colori in modo indipendente."""
    # Se non specifichiamo un colore per l'icona, usa quello del testo
    if icon_color is None:
        icon_color = text_color

    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 15, 0, 5)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    icon_lbl = QLabel()
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", icon_filename)

    # Verniciamo l'icona con il suo colore dedicato
    icon_lbl.setPixmap(get_colored_pixmap(icon_path, 20, icon_color))

    text_lbl = QLabel(text)
    text_lbl.setStyleSheet(f"font-size: 16px; color: {text_color}; font-weight: bold;")

    layout.addWidget(icon_lbl)
    layout.addWidget(text_lbl)
    layout.addStretch()
    return widget

def get_colored_pixmap(icon_path, size, color_hex):
    """Carica un SVG vettoriale (monocromatico) e lo colora dinamicamente."""
    pixmap = QIcon(icon_path).pixmap(size, size)
    painter = QPainter(pixmap)
    # SourceIn dice al pennello: colora solo i pixel non trasparenti dell'icona
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color_hex))
    painter.end()
    return pixmap

class DashboardTabWidget(QWidget):
    """Tab visuale informativo avanzato: Storico, Delta T e Carichi PWM. Layout Responsivo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Header layout: Icona, Titolo, Selettore Profilo, Pulsante Ripristino
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignVCenter)

        # 1. Etichetta per l'icona SVG
        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "panoramic.svg")
        # Genera un rettangolo pixel (Pixmap) dall'icona vettoriale, specificando le dimensioni
        lbl_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        header_layout.addWidget(lbl_icon)

        # 2. Etichetta per il testo
        lbl_title = QLabel(T('tab_dash'))
        lbl_title.setStyleSheet(f"font-size: 24px; color: {get_accent()}; font-weight: bold;")
        header_layout.addWidget(lbl_title)

        header_layout.addSpacing(20)

        lbl_prof = QLabel(f"{T('dash_profile')}:")
        lbl_prof.setStyleSheet("color: #a6adc8; font-size: 13px; font-weight: bold;")
        header_layout.addWidget(lbl_prof)

        self.combo_profile = QComboBox()
        self.combo_profile.setCursor(QCursor(Qt.PointingHandCursor))
        self.combo_profile.setStyleSheet("""
            QComboBox { background-color: #313244; color: #cdd6f4; border-radius: 4px; padding: 4px 10px; font-weight: bold; }
            QComboBox::drop-down { border: none; }
        """)
        profiles = global_config.get("profiles", {"Default": {}})
        self.combo_profile.addItems(profiles.keys())
        active_prof = global_config.get("active_profile", "Default")
        if active_prof in profiles:
            self.combo_profile.setCurrentText(active_prof)
        self.combo_profile.currentTextChanged.connect(self.change_active_profile)
        header_layout.addWidget(self.combo_profile)

        header_layout.addStretch()

        self.btn_restore = QPushButton(f" {T('dash_manage_hidden')}")
        icon_path_eye = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "eye.svg")
        self.btn_restore.setIcon(QIcon(get_colored_pixmap(icon_path_eye, 16, "#cdd6f4")))

        self.btn_restore.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_restore.setStyleSheet("""
            QPushButton { background-color: #313244; color: #cdd6f4; border-radius: 4px; padding: 4px 10px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #45475a; }
        """)
        self.btn_restore.clicked.connect(self.show_restore_dialog)
        header_layout.addWidget(self.btn_restore)

        layout.addLayout(header_layout)
        layout.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        scroll.setWidget(container)
        self.main_layout = QVBoxLayout(container)

        # ------------------------------
        # COSTRUZIONE SEZIONI DINAMICHE
        # ------------------------------

        # Sensori Virtuali
        self.lbl_virt = _create_section_header("virtual.svg", T('dash_virt_sensors'), "#cdd6f4")
        self.grp_virt = QWidget()
        self.lay_virt = QGridLayout(self.grp_virt)
        self.lay_virt.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_virt.hide()
        self.grp_virt.hide()

        # Sensori di Sistema
        self.lbl_sys = _create_section_header("system.svg", T('dash_sys_sensors'), "#cdd6f4")
        self.grp_sys = QWidget()
        self.lay_sys = QGridLayout(self.grp_sys)
        self.lay_sys.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Sensori di Flusso
        self.lbl_flow = _create_section_header("flow.svg", T('hw_flow_sensors_title'), text_color="#00e5ff", icon_color="#3f59ce")
        self.grp_flow = QWidget()
        self.lay_flow = QGridLayout(self.grp_flow)
        self.lay_flow.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_flow.hide()
        self.grp_flow.hide()

        # Uscite 12V
        self.lbl_fans = _create_section_header("power.svg", T('dash_12v_out'), text_color="#f9e2af", icon_color="#ffc107")
        self.grp_fans = QWidget()
        self.lay_fans = QGridLayout(self.grp_fans)
        self.lay_fans.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Sensori Aquaero
        self.lbl_aqua = _create_section_header("temp.svg", T('dash_aqua_sensors'), text_color="#f38ba8", icon_color="#ff3333")
        self.grp_aqua = QWidget()
        self.lay_aqua = QGridLayout(self.grp_aqua)
        self.lay_aqua.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.main_layout.addWidget(self.lbl_virt)
        self.main_layout.addWidget(self.grp_virt)
        self.main_layout.addWidget(self.lbl_sys)
        self.main_layout.addWidget(self.grp_sys)
        self.main_layout.addWidget(self.lbl_flow)
        self.main_layout.addWidget(self.grp_flow)
        self.main_layout.addWidget(self.lbl_fans)
        self.main_layout.addWidget(self.grp_fans)
        self.main_layout.addWidget(self.lbl_aqua)
        self.main_layout.addWidget(self.grp_aqua)
        self.main_layout.addStretch()

        layout.addWidget(scroll)

    def change_active_profile(self, profile_name):
        global_config["active_profile"] = profile_name
        save_config(global_config)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def update_telemetry(self, data):
        self._clear_layout(self.lay_virt)
        self._clear_layout(self.lay_sys)
        self._clear_layout(self.lay_flow)
        self._clear_layout(self.lay_fans)
        self._clear_layout(self.lay_aqua)

        # Calcolo Dinamico delle colonne in base alla larghezza della finestra
        # Considerando una card larga in media ~300px + i margini
        available_width = self.width()
        num_cols = max(1, available_width // 310)

        col_virt, row_virt = 0, 0
        col_sys, row_sys = 0, 0
        col_flow, row_flow = 0, 0
        col_fans, row_fans = 0, 0
        col_aqua, row_aqua = 0, 0

        hidden = global_config.get("hidden_sensors", [])
        histories = data.get("history", {})

        # 1. Sensori Virtuali (Delta T)
        virt_data = data.get('virtuals', {})
        if virt_data:
            self.lbl_virt.show()
            self.grp_virt.show()
            for v_id, val in virt_data.items():
                if v_id in hidden: continue
                name = global_config.get("sensors", {}).get(v_id, v_id)
                hist = histories.get(v_id, [])
                self._add_dash_card(self.lay_virt, name, format_temp(val), "virtual.svg", row_virt, col_virt, v_id, history_data=hist)
                col_virt += 1
                if col_virt >= num_cols: col_virt = 0; row_virt += 1
        else:
            self.lbl_virt.hide()
            self.grp_virt.hide()

        # 2. Sistema
        sys_data = data.get('system', {})
        for s_id, val in sys_data.items():
            if s_id in hidden: continue
            name = global_config["sensors"].get(s_id, s_id)
            hist = histories.get(s_id, [])

            if "load" in s_id.lower() or "busy" in s_id.lower():
                if global_config.get("lang") == "la":
                    val_str = f"{to_roman(int(val))} %"
                else:
                    val_str = f"{int(val)} %"
                self._add_dash_card(self.lay_sys, name, val_str, "power.svg", row_sys, col_sys, s_id, history_data=hist)

            elif "_in" in s_id.lower() or "volt" in s_id.lower():
                if global_config.get("lang") == "la":
                    val_str = f"{to_roman(val)} V"
                else:
                    val_str = f"{val:.2f} V"
                self._add_dash_card(self.lay_sys, name, val_str, "plug.svg", row_sys, col_sys, s_id, history_data=hist)

            else:
                self._add_dash_card(self.lay_sys, name, format_temp(val), "system.svg", row_sys, col_sys, s_id, history_data=hist)

            # Incremento delle colonne e delle righe della griglia
            col_sys += 1
            if col_sys >= num_cols:
                col_sys = 0
                row_sys += 1

        # 3. Sensori di Flusso
        flow_data = data.get('flows', {})
        flow_config = global_config.get("flow_sensors", {})

        has_active_flows = False
        for flow_id, val in flow_data.items():
            conf = flow_config.get(str(flow_id), {})
            if not conf.get("enabled", False):
                continue

            has_active_flows = True
            s_id = f"flow_rate_{flow_id}"

            if s_id in hidden: continue

            hist = histories.get(s_id, [])
            if global_config.get("lang") == "la":
                flow_val_str = f"{to_roman(int(val))} L/h"
            else:
                flow_val_str = f"{val:.1f} L/h"

            is_la = global_config.get("lang") == "la"
            flow_title_num = to_roman(flow_id) if is_la else str(flow_id)
            self._add_dash_card(self.lay_flow, T("hw_flow_sensor_num").format(i=flow_title_num), flow_val_str, "flow.svg", row_flow, col_flow, s_id, history_data=hist)

            col_flow += 1
            if col_flow >= num_cols: col_flow = 0; row_flow += 1

        self.lbl_flow.setVisible(has_active_flows)
        self.grp_flow.setVisible(has_active_flows)

        # 4. Uscite Hardware (12V)
        pwm_loads = data.get('pwm_loads', {})
        volts = data.get('volts', {})
        hw_config = global_config.get("hardware_channels", {})
        for ch_id, rpm in data.get('rpms', {}).items():
            ch_conf = hw_config.get(str(ch_id), {})
            if not ch_conf.get("enabled", True): continue

            s_id = f"ch_rpm_{ch_id}"
            if s_id in hidden: continue
            ch_name = global_config["channels_names"].get(str(ch_id), f"{T('channel')} {ch_id}")
            hist = histories.get(s_id, [])
            pwm_load = pwm_loads.get(ch_id, 0)
            volt_val = volts.get(ch_id, 0.0)

            if global_config.get("lang") == "la":
                rpm_val_str = f"{to_roman(int(rpm))} RPM"
                volt_str = f"{to_roman(volt_val)} V"
            else:
                rpm_val_str = f"{rpm} RPM"
                volt_str = f"{volt_val:.2f} V"

            self._add_dash_card(self.lay_fans, ch_name, rpm_val_str, "power.svg", row_fans, col_fans, s_id, history_data=hist, pwm_load=pwm_load, sub_value=volt_str)

            col_fans += 1
            if col_fans >= num_cols: col_fans = 0; row_fans += 1

        # 5. Aquaero (Temperature hardware)
        for s_id, temp in data.get('temps', {}).items():
            if s_id in hidden: continue
            name = global_config["sensors"].get(s_id, s_id)
            hist = histories.get(s_id, [])

            self._add_dash_card(self.lay_aqua, name, format_temp(temp), "temp.svg", row_aqua, col_aqua, s_id, history_data=hist)

            col_aqua += 1
            if col_aqua >= num_cols: col_aqua = 0; row_aqua += 1

    def _add_dash_card(self, target_layout, title, value, icon_filename, row, col, sensor_id, history_data=None, pwm_load=None, sub_value=None):
        card = QFrame()
        card.setMinimumWidth(260)
        card.setMaximumWidth(450)
        card.setStyleSheet("QFrame { background-color: rgba(30, 30, 30, 160); border-radius: 8px; border: 1px solid #333333; }")

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(6)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Determina il colore dell'icona in base al tipo di icona usata
        icon_color = "#cdd6f4" # Default chiaro
        if icon_filename == "temp.svg": icon_color = "#ff3333"        # Rosso
        elif icon_filename == "power.svg": icon_color = "#ffc107"     # Giallo
        elif icon_filename == "flow.svg": icon_color = "#00e5ff"      # Turchese
        elif icon_filename == "plug.svg": icon_color = "#94e2d5"      # Verde acqua

        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", icon_filename)
        lbl_icon.setPixmap(get_colored_pixmap(icon_path, 16, icon_color))
        lbl_icon.setStyleSheet("background: transparent; border: none;")

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #a6adc8; font-size: 12px; font-weight: bold; background: transparent; border: none;")

        btn_hide = QPushButton()
        btn_hide.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "close.svg")))
        btn_hide.setFixedSize(16, 16)
        btn_hide.setCursor(QCursor(Qt.PointingHandCursor))
        btn_hide.setToolTip(T("dash_hide_tooltip"))
        btn_hide.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: rgba(255, 51, 51, 40); border-radius: 4px; }
        """)
        btn_hide.clicked.connect(lambda _, s=sensor_id: self.hide_sensor(s))

        top_layout.addWidget(lbl_icon)
        top_layout.addWidget(lbl_title)
        top_layout.addStretch()
        top_layout.addWidget(btn_hide)
        c_layout.addLayout(top_layout)

        # Valore centrale
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {get_accent()}; font-size: 20px; font-weight: bold; background: transparent; border: none;")
        c_layout.addWidget(lbl_val)

        if sub_value:
            lbl_sub = QLabel(sub_value)
            lbl_sub.setStyleSheet("color: #f9e2af; font-size: 14px; font-weight: bold; background: transparent; border: none;")
            c_layout.addWidget(lbl_sub)

        # Storico grafico
        if history_data and len(history_data) > 1:
            sparkline = SparklineWidget()
            sparkline.update_data(history_data)
            c_layout.addWidget(sparkline)

        # Carico ventole
        if pwm_load is not None:
            fill_bar = PWMFillBar()
            fill_bar.update_value(pwm_load)
            c_layout.addWidget(fill_bar)

        target_layout.addWidget(card, row, col)

    def hide_sensor(self, sensor_id):
        hidden = global_config.get("hidden_sensors", [])
        if sensor_id not in hidden:
            hidden.append(sensor_id)
            global_config["hidden_sensors"] = hidden
            save_config(global_config)

    def show_restore_dialog(self):
        hidden = global_config.get("hidden_sensors", [])
        if not hidden:
            QMessageBox.information(self, "Info", T("dash_no_hidden"))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(T("dash_manage_hidden"))
        dialog.setMinimumWidth(300)
        dialog.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")

        layout = QVBoxLayout(dialog)
        lbl_info = QLabel(T("dash_restore_info"))
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: 1px solid #313244; background-color: #11111b; border-radius: 4px;")
        container = QWidget()
        scroll.setWidget(container)
        list_layout = QVBoxLayout(container)

        checkboxes = {}
        for s_id in hidden:
            nice_name = global_config.get("sensors", {}).get(s_id, s_id)
            chk = QCheckBox(f"{nice_name} ({s_id})")
            chk.setStyleSheet("font-size: 13px;")
            list_layout.addWidget(chk)
            checkboxes[s_id] = chk

        list_layout.addStretch()
        layout.addWidget(scroll)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.setStyleSheet("QPushButton { background-color: #313244; color: #cdd6f4; padding: 5px; border-radius: 4px; } QPushButton:hover { background-color: #45475a; }")
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec() == QDialog.Accepted:
            sensors_to_restore = [s_id for s_id, chk in checkboxes.items() if chk.isChecked()]
            if sensors_to_restore:
                for s in sensors_to_restore:
                    hidden.remove(s)
                global_config["hidden_sensors"] = hidden
                save_config(global_config)


class SecurityTabWidget(QWidget):
    """Componente per l'interfaccia degli allarmi hardware di sistema (Fail-Safe)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "security.svg")
        lbl_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        header_layout.addWidget(lbl_icon)

        lbl_title = QLabel(T('sec_title'))
        lbl_title.setStyleSheet("font-size: 24px; color: #ff3333; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        layout.addLayout(header_layout)
        layout.addSpacing(10)

        info_txt = QLabel(T("sec_info"))
        info_txt.setWordWrap(True)
        info_txt.setStyleSheet("color: #a6adc8; margin-bottom: 15px; font-size: 15px;")
        layout.addWidget(info_txt)

        self.sec_channels = {}
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        sec_layout = QVBoxLayout(container)
        layout.addWidget(scroll)

        # ---------------------------------------------------------
        # 1. TITOLO SEZIONE 12V
        # ---------------------------------------------------------
        self.lbl_12v = _create_section_header("power.svg", T('dash_12v_out'), text_color="#cdd6f4", icon_color="#ffc107")
        sec_layout.addWidget(self.lbl_12v)

        for i in range(1, 5):
            ch_name = global_config["channels_names"].get(str(i), f"{T('channel')} {i}")

            lbl_ch = QLabel(ch_name)
            lbl_ch.setStyleSheet("font-size: 14px; color: #a6adc8; font-weight: bold; margin-top: 10px;")
            sec_layout.addWidget(lbl_ch)

            group = QGroupBox()
            group.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")
            glayout = QFormLayout(group)

            box_delay_alarm = QHBoxLayout()
            lbl_delay_alarm = QLabel(T("sec_delay_alarm"))
            spin_delay_alarm = RomanSpinBox()
            spin_delay_alarm.setRange(0, 60)
            spin_delay_alarm.setSuffix(" s")
            box_delay_alarm.addWidget(lbl_delay_alarm)
            box_delay_alarm.addWidget(spin_delay_alarm)
            box_delay_alarm.addStretch()
            glayout.addRow("", box_delay_alarm)

            box_rpm = QHBoxLayout()
            chk_rpm = QCheckBox(T("sec_rpm"))
            spin_rpm = RomanSpinBox()
            spin_rpm.setRange(0, 5000)
            spin_rpm.setSuffix(" RPM")
            box_rpm.addWidget(chk_rpm)
            box_rpm.addWidget(spin_rpm)
            box_rpm.addStretch()
            glayout.addRow("", box_rpm)

            box_temp = QHBoxLayout()
            chk_temp = QCheckBox(T("sec_temp"))
            spin_temp = RomanSpinBox()
            spin_temp.setRange(20, 110)
            spin_temp.setSuffix(" °C")
            box_temp.addWidget(chk_temp)
            box_temp.addWidget(spin_temp)
            box_temp.addStretch()
            glayout.addRow("", box_temp)

            box_power = QHBoxLayout()
            chk_power = QCheckBox(T("sec_pwm"))
            spin_power = RomanSpinBox()
            spin_power.setRange(0, 100)
            spin_power.setSuffix(" %")
            box_power.addWidget(chk_power)
            box_power.addWidget(spin_power)
            box_power.addStretch()
            glayout.addRow("", box_power)

            box_volt = QHBoxLayout()
            chk_volt = QCheckBox(T("sec_volt"))
            spin_volt = RomanDoubleSpinBox()
            spin_volt.setRange(0.0, 12.0)
            spin_volt.setSingleStep(0.1)
            spin_volt.setDecimals(1)
            spin_volt.setSuffix(" V")
            box_volt.addWidget(chk_volt)
            box_volt.addWidget(spin_volt)
            box_volt.addStretch()
            glayout.addRow("", box_volt)

            # Segnali
            chk_rpm.toggled.connect(self.set_dirty)
            spin_rpm.valueChanged.connect(self.set_dirty)
            chk_temp.toggled.connect(self.set_dirty)
            spin_temp.valueChanged.connect(self.set_dirty)
            chk_power.toggled.connect(self.set_dirty)
            spin_power.valueChanged.connect(self.set_dirty)
            chk_volt.toggled.connect(self.set_dirty)
            spin_volt.valueChanged.connect(self.set_dirty)
            spin_delay_alarm.valueChanged.connect(self.set_dirty)

            self.sec_channels[str(i)] = {
                "chk_rpm": chk_rpm, "spin_rpm": spin_rpm,
                "chk_temp": chk_temp, "spin_temp": spin_temp,
                "chk_power": chk_power, "spin_power": spin_power,
                "chk_volt": chk_volt, "spin_volt": spin_volt,
                "spin_delay_alarm": spin_delay_alarm
            }
            sec_layout.addWidget(group)

        # ---------------------------------------------------------
        # 2. TITOLO SEZIONE FLUSSI
        # ---------------------------------------------------------
        self.lbl_flow = _create_section_header("flow.svg", T('hw_flow_sensors_title'), text_color="#cdd6f4", icon_color="#3f59ce")
        sec_layout.addWidget(self.lbl_flow)

        self.sec_flows = {}
        for i in range(1, 3):
            is_la = global_config.get("lang") == "la"
            num_str = to_roman(i) if is_la else str(i)
            lbl_fl = QLabel(T("hw_flow_sensor_num").format(i=num_str))
            lbl_fl.setStyleSheet("font-size: 14px; color: #a6adc8; font-weight: bold; margin-top: 10px;")
            sec_layout.addWidget(lbl_fl)

            group_flow = QGroupBox()
            group_flow.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")
            flayout = QFormLayout(group_flow)

            box_delay_flow = QHBoxLayout()
            lbl_delay_flow = QLabel(T("sec_delay_alarm"))
            spin_delay_flow = RomanSpinBox()
            spin_delay_flow.setRange(0, 60)
            spin_delay_flow.setSuffix(" s")
            box_delay_flow.addWidget(lbl_delay_flow)
            box_delay_flow.addWidget(spin_delay_flow)
            box_delay_flow.addStretch()
            flayout.addRow("", box_delay_flow)

            box_flow_alarm = QHBoxLayout()
            chk_flow_alarm = QCheckBox(T("sec_flow_alarm"))
            spin_flow_alarm = RomanDoubleSpinBox()
            spin_flow_alarm.setRange(0.0, 500.0)
            spin_flow_alarm.setDecimals(1)
            spin_flow_alarm.setSuffix(" L/h")
            box_flow_alarm.addWidget(chk_flow_alarm)
            box_flow_alarm.addWidget(spin_flow_alarm)
            box_flow_alarm.addStretch()
            flayout.addRow("", box_flow_alarm)

            chk_flow_alarm.toggled.connect(self.set_dirty)
            spin_flow_alarm.valueChanged.connect(self.set_dirty)
            spin_delay_flow.valueChanged.connect(self.set_dirty)

            self.sec_flows[str(i)] = {
                "chk_flow": chk_flow_alarm,
                "spin_flow": spin_flow_alarm,
                "spin_delay_flow": spin_delay_flow
            }
            sec_layout.addWidget(group_flow)

        # ---------------------------------------------------------
        # 3. AZIONI GLOBALI
        # ---------------------------------------------------------
        lbl_global = QLabel(T("sec_global"))
        lbl_global.setStyleSheet("font-size: 16px; color: #ff3333; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        layout.addWidget(lbl_global)

        action_group = QGroupBox()
        action_group.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")
        alayout = QVBoxLayout(action_group)

        self.chk_sound = QCheckBox(f" {T('sec_sound')}")
        icon_sound = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "sound.svg")
        self.chk_sound.setIcon(QIcon(get_colored_pixmap(icon_sound, 16, "#cdd6f4")))

        self.chk_osd_alert = QCheckBox(f" {T('sec_osd_flash')}")
        icon_osd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "osd.svg")
        self.chk_osd_alert.setIcon(QIcon(get_colored_pixmap(icon_osd, 16, "#ff3333")))
        self.chk_osd_alert.setChecked(True)

        box_cmd = QHBoxLayout()
        self.chk_cmd = QCheckBox(f" {T('sec_cmd_custom')}")
        icon_warn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "warning.svg")
        self.chk_cmd.setIcon(QIcon(get_colored_pixmap(icon_warn, 16, "#ffc107")))
        self.txt_cmd = QLineEdit()
        self.txt_cmd.setPlaceholderText("/home/user/allarme.sh")
        box_cmd.addWidget(self.chk_cmd)
        box_cmd.addWidget(self.txt_cmd)

        self.chk_shutdown = QCheckBox(T("sec_shutdown"))
        self.chk_shutdown.setStyleSheet("color: #ff3333; font-weight: bold;")

        self.box_delay = QHBoxLayout()
        self.lbl_delay = QLabel(T("sec_delay"))
        self.lbl_delay.setStyleSheet("color: #6c7086;")
        self.spin_delay = RomanSpinBox()
        self.spin_delay.setRange(0, 60)
        self.spin_delay.setSuffix(" sec")
        self.spin_delay.setEnabled(False)

        self.box_delay.addSpacing(25)
        self.box_delay.addWidget(self.lbl_delay)
        self.box_delay.addWidget(self.spin_delay)
        self.box_delay.addStretch()

        self.chk_sound.toggled.connect(self.set_dirty)
        self.chk_osd_alert.toggled.connect(self.set_dirty)
        self.chk_cmd.toggled.connect(self.set_dirty)
        self.chk_cmd.toggled.connect(self.update_delay_visibility)
        self.txt_cmd.textChanged.connect(self.set_dirty)
        self.txt_cmd.textChanged.connect(self.update_delay_visibility)
        self.chk_shutdown.toggled.connect(self.set_dirty)
        self.chk_shutdown.toggled.connect(self.update_delay_visibility)
        self.spin_delay.valueChanged.connect(self.set_dirty)

        alayout.addWidget(self.chk_sound)
        alayout.addWidget(self.chk_osd_alert)
        alayout.addLayout(box_cmd)
        alayout.addWidget(self.chk_shutdown)
        alayout.addLayout(self.box_delay)

        self.btn_save_sec = QPushButton(f" {T('sec_save')}")
        self.icon_save = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "save.svg")
        self.icon_check = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "check.svg")
        self.btn_save_sec.setIcon(QIcon(get_colored_pixmap(self.icon_save, 16, "#11111b")))
        self.btn_save_sec.setObjectName("SecurityBtn")
        self.btn_save_sec.setEnabled(False)
        self.btn_save_sec.clicked.connect(self.save_security)
        alayout.addWidget(self.btn_save_sec)

        layout.addWidget(action_group)
        self.load_security()

    def update_delay_visibility(self):
        cmd_active = self.chk_cmd.isChecked() and bool(self.txt_cmd.text().strip())
        shutdown_active = self.chk_shutdown.isChecked()

        should_enable = cmd_active and shutdown_active

        self.spin_delay.setEnabled(should_enable)
        if should_enable:
            self.lbl_delay.setStyleSheet("color: #cdd6f4;")
        else:
            self.lbl_delay.setStyleSheet("color: #6c7086;")

    def set_dirty(self):
        self.btn_save_sec.setEnabled(True)

    def save_security(self):
        sec_config = {"channels": {}, "flows": {}, "actions": {}}

        for ch_id, widgets in self.sec_channels.items():
            sec_config["channels"][ch_id] = {
                "rpm_en": widgets["chk_rpm"].isChecked(),
                "rpm_val": widgets["spin_rpm"].value(),
                "temp_en": widgets["chk_temp"].isChecked(),
                "temp_val": widgets["spin_temp"].value(),
                "power_en": widgets["chk_power"].isChecked(),
                "power_val": widgets["spin_power"].value(),
                "volt_en": widgets["chk_volt"].isChecked(),
                "volt_val": widgets["spin_volt"].value(),
                "delay_val": widgets["spin_delay_alarm"].value()
            }

        for f_id, widgets in self.sec_flows.items():
            sec_config["flows"][f_id] = {
                "flow_en": widgets["chk_flow"].isChecked(),
                "flow_val": widgets["spin_flow"].value(),
                "delay_val": widgets["spin_delay_flow"].value()
            }

        sec_config["actions"] = {
            "sound_en": self.chk_sound.isChecked(),
            "osd_en": self.chk_osd_alert.isChecked(),
            "cmd_en": self.chk_cmd.isChecked(),
            "cmd_val": self.txt_cmd.text(),
            "shutdown_en": self.chk_shutdown.isChecked(),
            "delay_val": self.spin_delay.value()
        }

        global_config["security"] = sec_config
        save_config(global_config)
        self.btn_save_sec.setEnabled(False)

        self.btn_save_sec.setText(f" {T('saved_success')}")
        self.btn_save_sec.setIcon(QIcon(get_colored_pixmap(self.icon_check, 16, "#11111b")))
        self.btn_save_sec.setStyleSheet("background-color: #00e676 !important; color: #11111b !important; font-weight: bold;")
        QTimer.singleShot(2000, self.reset_save_btn_sec)

    def reset_save_btn_sec(self):
        self.btn_save_sec.setText(f" {T('sec_save')}")
        self.btn_save_sec.setIcon(QIcon(get_colored_pixmap(self.icon_save, 16, "#11111b")))
        self.btn_save_sec.setStyleSheet("")


    def load_security(self):
        sec_config = global_config.get("security", {})

        ch_config = sec_config.get("channels", {})
        for ch_id, widgets in self.sec_channels.items():
            saved = ch_config.get(ch_id, {})
            widgets["chk_rpm"].blockSignals(True); widgets["chk_rpm"].setChecked(saved.get("rpm_en", False)); widgets["chk_rpm"].blockSignals(False)
            widgets["spin_rpm"].blockSignals(True); widgets["spin_rpm"].setValue(saved.get("rpm_val", 500)); widgets["spin_rpm"].blockSignals(False)
            widgets["chk_temp"].blockSignals(True); widgets["chk_temp"].setChecked(saved.get("temp_en", False)); widgets["chk_temp"].blockSignals(False)
            widgets["spin_temp"].blockSignals(True); widgets["spin_temp"].setValue(saved.get("temp_val", 55)); widgets["spin_temp"].blockSignals(False)
            widgets["chk_power"].blockSignals(True); widgets["chk_power"].setChecked(saved.get("power_en", False)); widgets["chk_power"].blockSignals(False)
            widgets["spin_power"].blockSignals(True); widgets["spin_power"].setValue(saved.get("power_val", 20)); widgets["spin_power"].blockSignals(False)
            widgets["spin_delay_alarm"].blockSignals(True); widgets["spin_delay_alarm"].setValue(saved.get("delay_val", 3)); widgets["spin_delay_alarm"].blockSignals(False)
            widgets["chk_volt"].blockSignals(True); widgets["chk_volt"].setChecked(saved.get("volt_en", False)); widgets["chk_volt"].blockSignals(False)
            widgets["spin_volt"].blockSignals(True); widgets["spin_volt"].setValue(saved.get("volt_val", 0.0)); widgets["spin_volt"].blockSignals(False)

        flows_config = sec_config.get("flows", {})
        for f_id, widgets in self.sec_flows.items():
            saved_f = flows_config.get(f_id, {})
            widgets["chk_flow"].blockSignals(True); widgets["chk_flow"].setChecked(saved_f.get("flow_en", False)); widgets["chk_flow"].blockSignals(False)
            widgets["spin_flow"].blockSignals(True); widgets["spin_flow"].setValue(saved_f.get("flow_val", 40.0)); widgets["spin_flow"].blockSignals(False)
            widgets["spin_delay_flow"].blockSignals(True); widgets["spin_delay_flow"].setValue(saved_f.get("delay_val", 5)); widgets["spin_delay_flow"].blockSignals(False)

        actions = sec_config.get("actions", {})
        self.chk_sound.blockSignals(True); self.chk_sound.setChecked(actions.get("sound_en", False)); self.chk_sound.blockSignals(False)
        self.chk_osd_alert.blockSignals(True); self.chk_osd_alert.setChecked(actions.get("osd_en", True)); self.chk_osd_alert.blockSignals(False)
        self.chk_cmd.blockSignals(True); self.chk_cmd.setChecked(actions.get("cmd_en", False)); self.chk_cmd.blockSignals(False)
        self.txt_cmd.blockSignals(True); self.txt_cmd.setText(actions.get("cmd_val", "")); self.txt_cmd.blockSignals(False)
        self.chk_shutdown.blockSignals(True); self.chk_shutdown.setChecked(actions.get("shutdown_en", False)); self.chk_shutdown.blockSignals(False)
        self.spin_delay.blockSignals(True); self.spin_delay.setValue(actions.get("delay_val", 0)); self.spin_delay.blockSignals(False)

        self.update_delay_visibility()
        self.btn_save_sec.setEnabled(False)


class OSDConfigTabWidget(QWidget):
    """Componente per l'interfaccia di personalizzazione e configurazione dell'overlay OSD."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "osd.svg")
        lbl_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        header_layout.addWidget(lbl_icon)

        lbl_title = QLabel(T('osd_title'))
        lbl_title.setStyleSheet(f"font-size: 24px; color: {get_accent()}; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        layout.addLayout(header_layout)
        layout.addSpacing(10)

        info_txt = QLabel(T("osd_info"))
        info_txt.setWordWrap(True)
        info_txt.setStyleSheet("color: #a6adc8; margin-bottom: 15px; font-size: 15px;")
        layout.addWidget(info_txt)

        global_group = QGroupBox()
        global_group.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")
        g_layout = QHBoxLayout(global_group)

        self.main_window.chk_osd = QCheckBox(T("osd_show"))
        self.main_window.chk_osd.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {get_accent()};")
        self.main_window.chk_osd.setChecked(global_config.get("osd_export", False))
        self.main_window.chk_osd.toggled.connect(self.main_window.toggle_osd)

        self.main_window.combo_osd_scale = QComboBox()
        scales = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        is_la = global_config.get("lang") == "la"
        for s in scales:
            perc = int(s * 100)
            txt = f"{to_roman(perc)}%" if is_la else f"{perc}%"
            self.main_window.combo_osd_scale.addItem(txt, s)
        self.main_window.combo_osd_scale.setFixedWidth(80)

        current_scale = global_config.get("osd_scale", 1.0)
        idx = self.main_window.combo_osd_scale.findData(current_scale)
        if idx >= 0:
            self.main_window.combo_osd_scale.setCurrentIndex(idx)

        self.main_window.combo_osd_scale.currentIndexChanged.connect(
            lambda i: self.main_window.change_osd_scale(self.main_window.combo_osd_scale.itemData(i))
        )

        g_layout.addWidget(self.main_window.chk_osd)
        g_layout.addWidget(QLabel(T("osd_scale")))
        g_layout.addWidget(self.main_window.combo_osd_scale)
        g_layout.addStretch()
        layout.addWidget(global_group)

        lbl_aesthetic = QLabel(T("osd_aesthetic"))
        lbl_aesthetic.setStyleSheet("font-size: 16px; color: #cdd6f4; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        layout.addWidget(lbl_aesthetic)

        aesthetic_group = QGroupBox()
        aesthetic_group.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")
        a_layout = QFormLayout(aesthetic_group)

        opacity_layout = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setFixedWidth(180)
        self.lbl_opacity_val = QLabel()
        opacity_layout.addWidget(self.slider_opacity)
        opacity_layout.addWidget(self.lbl_opacity_val)
        opacity_layout.addStretch()
        self.slider_opacity.valueChanged.connect(self.update_aesthetic)

        self.spin_max_rows = RomanSpinBox()
        self.spin_max_rows.setRange(3, 15)
        self.spin_max_rows.setFixedWidth(60)
        self.spin_max_rows.valueChanged.connect(self.update_aesthetic)

        row_names = QHBoxLayout()
        self.btn_color_names = QPushButton(T("osd_btn_color"))
        self.lbl_preview_names = QLabel()
        self.lbl_preview_names.setFixedSize(24, 24)
        row_names.addWidget(self.btn_color_names)
        row_names.addWidget(self.lbl_preview_names)
        row_names.addStretch()

        row_values = QHBoxLayout()
        self.btn_color_values = QPushButton(T("osd_btn_color"))
        self.lbl_preview_values = QLabel()
        self.lbl_preview_values.setFixedSize(24, 24)
        row_values.addWidget(self.btn_color_values)
        row_values.addWidget(self.lbl_preview_values)
        row_values.addStretch()

        row_badges = QHBoxLayout()
        self.btn_color_badges = QPushButton(T("osd_btn_color"))
        self.lbl_preview_badges = QLabel()
        self.lbl_preview_badges.setFixedSize(24, 24)
        row_badges.addWidget(self.btn_color_badges)
        row_badges.addWidget(self.lbl_preview_badges)
        row_badges.addStretch()

        self.btn_color_names.clicked.connect(lambda: self.pick_color("c_names"))
        self.btn_color_values.clicked.connect(lambda: self.pick_color("c_values"))
        self.btn_color_badges.clicked.connect(lambda: self.pick_color("c_badges"))

        font_layout = QHBoxLayout()
        self.btn_font = QPushButton(T("osd_btn_font"))
        self.btn_font.clicked.connect(self.pick_font)
        self.lbl_current_font = QLabel(T("font_default"))
        self.lbl_current_font.setStyleSheet("color: #a6adc8; font-style: italic;")
        font_layout.addWidget(self.btn_font)
        font_layout.addWidget(self.lbl_current_font)
        font_layout.addStretch()

        a_layout.addRow(QLabel(T("osd_opacity")), opacity_layout)
        a_layout.addRow(QLabel(T("osd_max_rows")), self.spin_max_rows)
        a_layout.addRow(QLabel(T("osd_col_names")), row_names)
        a_layout.addRow(QLabel(T("osd_col_values")), row_values)
        a_layout.addRow(QLabel(T("osd_col_badges")), row_badges)
        a_layout.addRow(QLabel(T("osd_font_style")), font_layout)
        layout.addWidget(aesthetic_group)

        lbl_sensors = QLabel(T("osd_sensors_group"))
        lbl_sensors.setStyleSheet("font-size: 16px; color: #cdd6f4; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        layout.addWidget(lbl_sensors)

        sensors_group = QGroupBox()
        sensors_group.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")
        s_layout = QVBoxLayout(sensors_group)
        s_layout.setContentsMargins(0, 5, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        list_layout = QVBoxLayout(container)

        self.osd_items = {}

        # Canali 12V
        for i in range(1, 5):
            comp_id = f"ch_{i}"
            desc = f"Aquaero: {T('channel')} {i}"
            placeholder = f"{T('channel')} {i}"
            self._add_sensor_row(list_layout, comp_id, desc, placeholder)

        for i in range(1, 3):
            comp_id = f"flow_{i}"
            is_la = global_config.get("lang") == "la"
            num_str = to_roman(i) if is_la else str(i)
            desc = f"Aquaero: {T('hw_flow_sensor_num').format(i=num_str)}"
            placeholder = T('hw_flow_sensor_num').format(i=num_str)
            self._add_sensor_row(list_layout, comp_id, desc, placeholder)

        sys_sensors = self.main_window.engine.get_available_system_sensors()
        for comp_id, label in sys_sensors.items():
            self._add_sensor_row(list_layout, comp_id, label, f"Es. {label}")

        s_layout.addWidget(scroll)

        self.btn_save = QPushButton(f" {T('osd_save')}")
        self.icon_save = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "save.svg")
        self.icon_check = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "check.svg")
        self.btn_save.setIcon(QIcon(get_colored_pixmap(self.icon_save, 16, "#11111b")))
        self.btn_save.setObjectName("ActionBtn")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_osd_config)
        s_layout.addWidget(self.btn_save)

        layout.addWidget(sensors_group)
        self.load_osd_config()

    def _add_sensor_row(self, layout, comp_id, desc, placeholder):
        row = QHBoxLayout()
        chk = QCheckBox(desc)
        chk.setToolTip(comp_id)
        txt_name = QLineEdit()
        txt_name.setPlaceholderText(placeholder)

        chk.toggled.connect(self.set_dirty)
        txt_name.textChanged.connect(self.set_dirty)

        row.addWidget(chk, stretch=2)
        row.addWidget(txt_name, stretch=3)
        layout.addLayout(row)

        self.osd_items[comp_id] = {"chk": chk, "txt": txt_name}

    def set_dirty(self):
        self.btn_save.setEnabled(True)

    def update_aesthetic(self):
        self.set_dirty()
        opacity_percent = self.slider_opacity.value()
        real_opacity = int(opacity_percent * 2.55)
        max_rows = self.spin_max_rows.value()
        if global_config.get("lang") == "la":
            self.lbl_opacity_val.setText(f"{to_roman(opacity_percent)} %")
        else:
            self.lbl_opacity_val.setText(f"{opacity_percent} %")
        self.main_window.osd_window.set_customization(opacity=real_opacity, max_rows=max_rows)

        conf = global_config.get("osd_config", {})
        conf["opacity"] = real_opacity
        conf["max_rows"] = max_rows
        global_config["osd_config"] = conf

    def pick_color(self, target):
        color = QColorDialog.getColor(Qt.white, None, T("select_color"))
        if color.isValid():
            self.set_dirty()
            hex_c = color.name()
            conf = global_config.get("osd_config", {})
            style_preview = f"background-color: {hex_c}; border: 1px solid #45475a; border-radius: 4px;"

            if target == "c_names":
                self.lbl_preview_names.setStyleSheet(style_preview)
                self.main_window.osd_window.set_customization(c_names=hex_c)
                conf["color_names"] = hex_c
            elif target == "c_values":
                self.lbl_preview_values.setStyleSheet(style_preview)
                self.main_window.osd_window.set_customization(c_values=hex_c)
                conf["color_values"] = hex_c
            elif target == "c_badges":
                self.lbl_preview_badges.setStyleSheet(style_preview)
                self.main_window.osd_window.set_customization(c_badges=hex_c)
                conf["color_badges"] = hex_c
            global_config["osd_config"] = conf

    def pick_font(self):
        current_font = self.main_window.osd_window.custom_font or QFont()
        ok, font = QFontDialog.getFont(current_font, self)
        if ok:
            self.set_dirty()
            self.main_window.osd_window.set_customization(font=font)
            self.lbl_current_font.setText(f"Font: {font.family()}")

            conf = global_config.get("osd_config", {})
            conf["font_family"] = font.family()
            conf["font_size"] = font.pointSize()
            conf["font_bold"] = font.bold()
            conf["font_italic"] = font.italic()
            global_config["osd_config"] = conf

    def save_osd_config(self):
        conf = global_config.get("osd_config", {})
        for comp_id, widgets in self.osd_items.items():
            conf[comp_id] = {
                "enabled": widgets["chk"].isChecked(),
                "custom_name": widgets["txt"].text().strip()
            }
        global_config["osd_config"] = conf
        save_config(global_config)
        self.btn_save.setEnabled(False)

        self.btn_save.setText(f" {T('saved_success')}")
        self.btn_save.setIcon(QIcon(get_colored_pixmap(self.icon_check, 16, "#11111b")))
        self.btn_save.setStyleSheet("background-color: #00e676 !important; color: #11111b !important; font-weight: bold")
        QTimer.singleShot(2000, self.reset_save_btn)

    def reset_save_btn(self):
        self.btn_save.setText(f" {T('osd_save')}")
        self.btn_save.setIcon(QIcon(get_colored_pixmap(self.icon_save, 16, "#11111b")))
        self.btn_save.setStyleSheet("")

    def load_osd_config(self):
        conf = global_config.get("osd_config", {})

        for comp_id, widgets in self.osd_items.items():
            saved = conf.get(comp_id, {})
            default_state = True if comp_id.startswith("ch_") else False
            widgets["chk"].blockSignals(True); widgets["chk"].setChecked(saved.get("enabled", default_state)); widgets["chk"].blockSignals(False)
            widgets["txt"].blockSignals(True); widgets["txt"].setText(saved.get("custom_name", "")); widgets["txt"].blockSignals(False)

        opacity = conf.get("opacity", 220)
        opacity_percent = int(opacity / 2.55)
        self.slider_opacity.blockSignals(True); self.slider_opacity.setValue(opacity_percent); self.slider_opacity.blockSignals(False)

        is_la = global_config.get("lang") == "la"
        self.lbl_opacity_val.setText(f"{to_roman(opacity_percent)} %" if is_la else f"{opacity_percent} %")

        max_rows = conf.get("max_rows", 8)
        self.spin_max_rows.blockSignals(True); self.spin_max_rows.setValue(max_rows); self.spin_max_rows.blockSignals(False)

        c_names = conf.get("color_names", "#cdd6f4")
        self.lbl_preview_names.setStyleSheet(f"background-color: {c_names}; border: 1px solid #45475a; border-radius: 4px;")

        c_values = conf.get("color_values", "#00e5ff")
        self.lbl_preview_values.setStyleSheet(f"background-color: {c_values}; border: 1px solid #45475a; border-radius: 4px;")

        c_badges = conf.get("color_badges", "#00e5ff")
        self.lbl_preview_badges.setStyleSheet(f"background-color: {c_badges}; border: 1px solid #45475a; border-radius: 4px;")

        font_family = conf.get("font_family")
        custom_font = None
        if font_family:
            self.lbl_current_font.setText(f"Font: {font_family}")
            custom_font = QFont(font_family)
            if "font_size" in conf: custom_font.setPointSize(conf["font_size"])
            if "font_bold" in conf: custom_font.setBold(conf["font_bold"])
            if "font_italic" in conf: custom_font.setItalic(conf["font_italic"])

        self.main_window.osd_window.set_customization(
            opacity=opacity, c_names=c_names, c_values=c_values,
            c_badges=c_badges, font=custom_font, max_rows=max_rows
        )

class SettingsTabWidget(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        layout = QVBoxLayout(self)

        # Titolo Principale
        header_layout = QHBoxLayout()
        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "settings.svg")
        lbl_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        header_layout.addWidget(lbl_icon)

        lbl_title = QLabel(T('tab_settings'))
        lbl_title.setStyleSheet(f"font-size: 24px; color: {get_accent()}; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        layout.addLayout(header_layout)
        layout.addSpacing(10)

        # 1. GRUPPO AUTO-SWITCH (Solo il box nero muto, la scritta è nella checkbox)
        group_auto = QGroupBox()
        group_auto.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")
        auto_layout = QHBoxLayout(group_auto)
        auto_layout.addWidget(self.main_window.chk_autoswitch)
        auto_layout.addWidget(self.main_window.btn_autoswitch_settings)
        auto_layout.addStretch()
        layout.addWidget(group_auto)

        # 2. ETICHETTA "PREFERENZE" (Staccata dal box, bianca, 16px, come "Profili")
        lbl_sys_pref = QLabel(T("set_sys_pref"))
        lbl_sys_pref.setStyleSheet("font-size: 16px; color: #cdd6f4; font-weight: bold; margin-top: 15px;")
        layout.addWidget(lbl_sys_pref)

        # 3. GRUPPO PREFERENZE (Box nero muto che contiene le opzioni)
        group_sys = QGroupBox()
        group_sys.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")
        sys_layout = QVBoxLayout(group_sys)
        sys_layout.setSpacing(10)

        # Lingua
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(T("set_lang")))
        self.combo_lang = QComboBox()

        # Mappatura: (Testo mostrato all'utente, Codice interno usato dal programma)
        lang_options = [
            ("it", "it"),
            ("en", "en"),
            ("de", "de"),
            ("fr", "fr"),
            ("es", "es"),
            ("ru", "ru"),
            ("zh", "zh"),
            ("la (imperium romanum)", "la")
        ]

        for visible_text, internal_code in lang_options:
            self.combo_lang.addItem(visible_text, internal_code)

        current_lang = global_config.get("lang", "en")
        index = self.combo_lang.findData(current_lang)
        if index >= 0:
            self.combo_lang.setCurrentIndex(index)

        self.combo_lang.currentIndexChanged.connect(
            lambda i: self.main_window.change_language(self.combo_lang.itemData(i))
        )

        lang_row.addWidget(self.combo_lang)
        lang_row.addStretch()
        sys_layout.addLayout(lang_row)

        # Opacità Interfaccia
        sys_layout.addSpacing(10)
        opac_row = QHBoxLayout()
        lbl_opac = QLabel(T("ui_opacity"))
        lbl_opac.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.slider_window_opac = QSlider(Qt.Horizontal)
        self.slider_window_opac.setRange(0, 100)
        saved_opac = global_config.get("window_opacity", 180)
        saved_opac_percent = int(saved_opac / 2.55)
        self.slider_window_opac.setValue(saved_opac_percent)
        self.lbl_window_opac_val = QLabel()

        is_la = global_config.get("lang") == "la"
        self.lbl_window_opac_val.setText(f"{to_roman(saved_opac_percent)} %" if is_la else f"{saved_opac_percent} %")
        self.lbl_window_opac_val.setStyleSheet("color: #a6adc8; font-weight: bold;")

        self.slider_window_opac.valueChanged.connect(self.change_ui_opacity)
        opac_row.addWidget(lbl_opac); opac_row.addWidget(self.slider_window_opac); opac_row.addWidget(self.lbl_window_opac_val)
        sys_layout.addLayout(opac_row)

        # Checkbox varie
        sys_layout.addSpacing(5)
        self.chk_close_tray = QCheckBox(T("close_to_tray"))
        self.chk_close_tray.setChecked(global_config.get("close_to_tray", True))
        self.chk_close_tray.toggled.connect(self.toggle_close_tray)

        sys_layout.addWidget(self.main_window.chk_autostart)
        sys_layout.addWidget(self.main_window.chk_minimized)
        sys_layout.addWidget(self.chk_close_tray)

        layout.addWidget(group_sys)
        layout.addStretch()

    def toggle_units(self, checked):
        global_config["use_fahrenheit"] = checked
        save_config(global_config)

    def change_ui_opacity(self, value):
        # Chiediamo la lingua una sola volta all'inizio
        is_imperium = global_config.get("lang") == "la"

        if is_imperium:
            self.lbl_window_opac_val.setText(f"{to_roman(value)} %")
        else:
            self.lbl_window_opac_val.setText(f"{value} %")

        real_opacity = int(value * 2.55)
        global_config["window_opacity"] = real_opacity
        save_config(global_config)

        # L'import DEVE restare qui dentro per evitare il circular import
        from main import get_dynamic_style
        self.main_window.setStyleSheet(get_dynamic_style(real_opacity, is_imperium))

    def toggle_close_tray(self, checked):
        global_config["close_to_tray"] = checked
        save_config(global_config)


class GuideTabWidget(QWidget):
    """Manuale tecnico integrato per le funzioni avanzate."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "manual.svg")
        lbl_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        header_layout.addWidget(lbl_icon)

        lbl_title = QLabel(T('tab_guide'))
        lbl_title.setStyleSheet(f"font-size: 24px; color: {get_accent()}; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        layout.addLayout(header_layout)
        layout.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QLabel()
        content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        content.setWordWrap(True)
        content.setTextFormat(Qt.RichText)

        content.setText(get_guide_text())

        is_imperium = global_config.get("lang") == "la"
        bg_color = "rgba(70, 15, 20, 225)" if is_imperium else "rgba(35, 38, 41, 225)"

        content.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 8px;
                padding: 25px;
                font-size: 14px;
                line-height: 1.6;
                color: #e0e0e0;
            }}
        """)

        scroll.setWidget(content)
        layout.addWidget(scroll)

class HardwareTabWidget(QWidget):
    """Tab per la configurazione fisica dei canali: Potenza Minima e Avvio Rapido."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "hardware.svg")
        lbl_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        header_layout.addWidget(lbl_icon)

        lbl_title = QLabel(T('tab_hw_channels'))
        lbl_title.setStyleSheet(f"font-size: 24px; color: {get_accent()}; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        layout.addLayout(header_layout)
        layout.addSpacing(10)

        info_txt = QLabel(T("hw_channels_info"))
        info_txt.setWordWrap(True)
        info_txt.setStyleSheet("color: #a6adc8; margin-bottom: 15px; font-size: 15px;")
        layout.addWidget(info_txt)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        scroll.setWidget(container)
        self.channels_layout = QVBoxLayout(container)

        self.hw_widgets = {}

        # --- TITOLO SEZIONE 12V ---
        self.lbl_12v = _create_section_header("power.svg", T('dash_12v_out'), text_color="#cdd6f4", icon_color="#ffc107")
        self.channels_layout.addWidget(self.lbl_12v)

        self.hw_widgets = {}

        for i in range(1, 5):
            ch_name = global_config["channels_names"].get(str(i), f"{T('channel')} {i}")

            group = QGroupBox()
            group.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")

            glayout = QFormLayout(group)
            glayout.setContentsMargins(15, 10, 15, 15)
            glayout.setSpacing(15)

            # --- 0. Abilitazione Canale ---
            box_enable = QHBoxLayout()
            chk_enable = QCheckBox(ch_name)
            chk_enable.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 15px;")
            box_enable.addWidget(chk_enable)
            box_enable.addStretch()

            # --- 1. Segnale di Controllo ---
            box_mode = QHBoxLayout()
            combo_dc_pwm = QComboBox()
            combo_dc_pwm.addItems(["PWM", "DC"])
            combo_dc_pwm.setFixedWidth(80)
            combo_dc_pwm.setCursor(Qt.PointingHandCursor)
            box_mode.addWidget(QLabel(T("hw_ctrl_mode")))
            box_mode.addWidget(combo_dc_pwm)
            box_mode.addStretch()

            # --- 2. Slider Potenza Minima ---
            box_min_power = QHBoxLayout()
            slider_min_power = QSlider(Qt.Horizontal)
            slider_min_power.setRange(0, 50)
            val_min_power = QLabel()
            val_min_power.setFixedWidth(40)
            val_min_power.setStyleSheet("font-weight: bold; color: #00e5ff;")

            def update_min_power_lbl(v, lbl=val_min_power):
                is_la = global_config.get("lang") == "la"
                lbl.setText(f"{to_roman(v)} %" if is_la else f"{v} %")

            slider_min_power.valueChanged.connect(update_min_power_lbl)
            update_min_power_lbl(0) # Inizializza subito l'etichetta

            box_min_power.addWidget(slider_min_power)
            box_min_power.addWidget(val_min_power)

            # --- 3. Start Boost ---
            box_boost = QHBoxLayout()
            chk_boost = QCheckBox(T("hw_start_boost"))
            chk_boost.setToolTip(T("hw_boost_tooltip"))
            chk_boost.setStyleSheet("font-size: 13px;")

            spin_boost_time = RomanDoubleSpinBox()
            spin_boost_time.setRange(0.1, 5.0)
            spin_boost_time.setSingleStep(0.1)
            spin_boost_time.setDecimals(1)
            spin_boost_time.setSuffix(" s")
            spin_boost_time.setEnabled(False)

            chk_boost.toggled.connect(spin_boost_time.setEnabled)
            box_boost.addWidget(chk_boost)
            box_boost.addSpacing(15)
            box_boost.addWidget(QLabel(T("hw_boost_time")))
            box_boost.addWidget(spin_boost_time)
            box_boost.addStretch()

            # Assemblaggio in ordine esatto
            glayout.addRow(box_enable)
            glayout.addRow("", box_mode)
            glayout.addRow(T("hw_min_power"), box_min_power)
            glayout.addRow("", box_boost)

            # Segnali
            chk_enable.toggled.connect(self.set_dirty)
            combo_dc_pwm.currentTextChanged.connect(self.set_dirty)
            slider_min_power.valueChanged.connect(self.set_dirty)
            chk_boost.toggled.connect(self.set_dirty)
            spin_boost_time.valueChanged.connect(self.set_dirty)

            self.hw_widgets[str(i)] = {
                "chk_enable": chk_enable,
                "combo_dc_pwm": combo_dc_pwm,
                "slider_min_power": slider_min_power,
                "val_min_power": val_min_power,
                "chk_boost": chk_boost,
                "spin_boost_time": spin_boost_time
            }

            self.channels_layout.addWidget(group)

        # --- TITOLO SEZIONE FLUSSI ---
        self.lbl_flow = _create_section_header("flow.svg", T('hw_flow_sensors_title'), text_color="#cdd6f4", icon_color="#3f59ce")
        self.channels_layout.addWidget(self.lbl_flow)

        self.flow_widgets = {}
        for i in range(1, 3):
            group_flow = QGroupBox()
            group_flow.setStyleSheet("QGroupBox { margin-top: 5px; padding-top: 5px; }")

            flayout = QFormLayout(group_flow)
            flayout.setContentsMargins(15, 10, 15, 15)
            flayout.setSpacing(10)

            # Riga 1: Spunta abilitazione
            box_flow_en = QHBoxLayout()

            is_la = global_config.get("lang") == "la"
            num_str = to_roman(i) if is_la else str(i)
            chk_flow_en = QCheckBox(T("hw_flow_sensor_num").format(i=num_str))

            chk_flow_en.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 15px;")
            box_flow_en.addWidget(chk_flow_en)
            box_flow_en.addStretch()

            # Variabili Interfaccia
            combo_type = QComboBox()
            combo_type.addItems(list(FLOW_PRESETS.keys()))
            combo_type.setEnabled(False)

            combo_fluid = QComboBox()
            combo_fluid.addItems(["Water", "DP Ultra"])
            combo_fluid.setEnabled(False)

            combo_fitting = QComboBox()
            combo_fitting.setEnabled(False)

            spin_calib = RomanSpinBox()
            spin_calib.setRange(1, 3000)
            spin_calib.setSuffix(" imp/l")
            spin_calib.setEnabled(False)

            def update_ui_logic(c_type=combo_type, c_fluid=combo_fluid, c_fit=combo_fitting, spin=spin_calib):
                sensor = c_type.currentText()
                if sensor == "User defined":
                    c_fluid.setEnabled(False)
                    c_fit.setEnabled(False)
                    spin.setEnabled(True)
                else:
                    spin.setEnabled(False)
                    c_fluid.setEnabled(True)
                    fluid = c_fluid.currentText()

                    fittings = list(FLOW_PRESETS[sensor].get(fluid, {}).keys())
                    if "N/A" in fittings or not fittings:
                        c_fit.setEnabled(False)
                        c_fit.blockSignals(True)
                        c_fit.clear()
                        c_fit.addItem("N/A")
                        c_fit.blockSignals(False)
                        val = FLOW_PRESETS[sensor][fluid].get("N/A", 150)
                    else:
                        c_fit.setEnabled(True)
                        current_fit = c_fit.currentText()
                        c_fit.blockSignals(True)
                        c_fit.clear()
                        c_fit.addItems(fittings)
                        if current_fit in fittings:
                            c_fit.setCurrentText(current_fit)
                        c_fit.blockSignals(False)
                        val = FLOW_PRESETS[sensor][fluid].get(c_fit.currentText(), 150)

                    spin.setValue(val)

            combo_type.currentTextChanged.connect(lambda text, func=update_ui_logic: func())
            combo_fluid.currentTextChanged.connect(lambda text, func=update_ui_logic: func())
            combo_fitting.currentTextChanged.connect(lambda text, func=update_ui_logic: func())

            chk_flow_en.toggled.connect(combo_type.setEnabled)
            chk_flow_en.toggled.connect(lambda checked, func=update_ui_logic: func() if checked else None)

            chk_flow_en.toggled.connect(self.set_dirty)
            combo_type.currentTextChanged.connect(self.set_dirty)
            combo_fluid.currentTextChanged.connect(self.set_dirty)
            combo_fitting.currentTextChanged.connect(self.set_dirty)
            spin_calib.valueChanged.connect(self.set_dirty)

            flayout.addRow(box_flow_en)
            flayout.addRow(T("hw_flow_type"), combo_type)
            flayout.addRow(T("hw_flow_fluid"), combo_fluid)
            flayout.addRow(T("hw_flow_fitting"), combo_fitting)
            flayout.addRow(T("hw_flow_calib"), spin_calib)

            self.flow_widgets[str(i)] = {
                "chk_enable": chk_flow_en,
                "combo_type": combo_type,
                "combo_fluid": combo_fluid,
                "combo_fitting": combo_fitting,
                "spin_calib": spin_calib,
                "update_logic": update_ui_logic
            }
            self.channels_layout.addWidget(group_flow)

        self.channels_layout.addStretch()
        layout.addWidget(scroll)

        self.btn_save_hw = QPushButton(f" {T('hw_save_btn')}")
        self.icon_save = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "save.svg")
        self.icon_check = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "check.svg")
        self.btn_save_hw.setIcon(QIcon(get_colored_pixmap(self.icon_save, 16, "#11111b")))
        self.btn_save_hw.setObjectName("ActionBtn")
        self.btn_save_hw.setEnabled(False)
        self.btn_save_hw.clicked.connect(self.save_hardware_config)
        layout.addWidget(self.btn_save_hw)

        self.load_hardware_config()

    def set_dirty(self):
        self.btn_save_hw.setEnabled(True)

    def save_hardware_config(self):
        hw_config = {}
        for ch_id, widgets in self.hw_widgets.items():
            selected_mode = widgets["combo_dc_pwm"].currentText()
            hw_config[ch_id] = {
                "enabled": widgets["chk_enable"].isChecked(),
                "ctrl_mode": selected_mode,
                "min_power": widgets["slider_min_power"].value(),
                "boost_en": widgets["chk_boost"].isChecked(),
                "boost_time": widgets["spin_boost_time"].value()
            }

            # La scrittura HID sull'Aquaero spetta al demone (root), non alla GUI.
            self.main_window.send_daemon_command(
                {"action": "set_mode", "channel": int(ch_id), "mode": selected_mode}
            )

        global_config["hardware_channels"] = hw_config

        flow_config = global_config.get("flow_sensors", {})
        for flow_id, widgets in self.flow_widgets.items():
            calib_val = widgets["spin_calib"].value()
            flow_config[flow_id] = {
                "enabled": widgets["chk_enable"].isChecked(),
                "sensor_type": widgets["combo_type"].currentText(),
                "fluid": widgets["combo_fluid"].currentText(),
                "fitting": widgets["combo_fitting"].currentText(),
                "impulses": calib_val
            }
            if widgets["chk_enable"].isChecked():
                self.main_window.send_daemon_command(
                    {"action": "set_flow_cal", "flow": int(flow_id), "impulses": calib_val}
                )

        global_config["flow_sensors"] = flow_config
        save_config(global_config)

        self.btn_save_hw.setEnabled(False)

        self.btn_save_hw.setText(f" {T('saved_success')}")
        self.btn_save_hw.setIcon(QIcon(get_colored_pixmap(self.icon_check, 16, "#11111b")))
        self.btn_save_hw.setStyleSheet("background-color: #00e676 !important; color: #11111b !important; font-weight: bold;")
        QTimer.singleShot(2000, self.reset_save_btn_hw)

    def reset_save_btn_hw(self):
        self.btn_save_hw.setText(f" {T('hw_save_btn')}")
        self.btn_save_hw.setIcon(QIcon(get_colored_pixmap(self.icon_save, 16, "#11111b")))
        self.btn_save_hw.setStyleSheet("")

    def load_hardware_config(self):
        hw_config = global_config.get("hardware_channels", {})
        for ch_id, widgets in self.hw_widgets.items():
            saved = hw_config.get(ch_id, {})

            en = saved.get("enabled", True)
            widgets["chk_enable"].blockSignals(True)
            widgets["chk_enable"].setChecked(en)
            widgets["chk_enable"].blockSignals(False)

            mode = saved.get("ctrl_mode", "PWM")
            widgets["combo_dc_pwm"].blockSignals(True)
            widgets["combo_dc_pwm"].setCurrentText(mode)
            widgets["combo_dc_pwm"].blockSignals(False)

            val = saved.get("min_power", 0)
            widgets["slider_min_power"].blockSignals(True)
            widgets["slider_min_power"].setValue(val)
            widgets["slider_min_power"].blockSignals(False)

            is_la = global_config.get("lang") == "la"
            widgets["val_min_power"].setText(f"{to_roman(val)} %" if is_la else f"{val} %")

            boost = saved.get("boost_en", False)
            widgets["chk_boost"].blockSignals(True)
            widgets["chk_boost"].setChecked(boost)
            widgets["chk_boost"].blockSignals(False)

            b_time = saved.get("boost_time", 1.0)
            widgets["spin_boost_time"].blockSignals(True)
            widgets["spin_boost_time"].setValue(b_time)
            widgets["spin_boost_time"].setEnabled(boost)
            widgets["spin_boost_time"].blockSignals(False)

        flow_config = global_config.get("flow_sensors", {})
        for flow_id, widgets in self.flow_widgets.items():
            saved_flow = flow_config.get(flow_id, {})

            en = saved_flow.get("enabled", False)
            widgets["chk_enable"].blockSignals(True)
            widgets["chk_enable"].setChecked(en)
            widgets["chk_enable"].blockSignals(False)

            s_type = saved_flow.get("sensor_type", "User defined")
            widgets["combo_type"].blockSignals(True)
            widgets["combo_type"].setCurrentText(s_type)
            widgets["combo_type"].blockSignals(False)

            fluid = saved_flow.get("fluid", "Water")
            widgets["combo_fluid"].blockSignals(True)
            widgets["combo_fluid"].setCurrentText(fluid)
            widgets["combo_fluid"].blockSignals(False)

            fit = saved_flow.get("fitting", "N/A")
            if fit != "N/A":
                widgets["combo_fitting"].blockSignals(True)
                widgets["combo_fitting"].addItem(fit)
                widgets["combo_fitting"].setCurrentText(fit)
                widgets["combo_fitting"].blockSignals(False)

            calib = saved_flow.get("impulses", 150)
            widgets["spin_calib"].blockSignals(True)
            widgets["spin_calib"].setValue(calib)
            widgets["spin_calib"].blockSignals(False)

            widgets["combo_type"].setEnabled(en)
            if en:
                widgets["update_logic"]()

# ---------------------------------------------------------------------------
#  Ruota dei colori (Tonalita' = angolo, Saturazione = distanza dal centro)
# ---------------------------------------------------------------------------
class ColorWheel(QWidget):
    changed = Signal()  # emesso quando l'utente trascina/clicca sulla ruota

    def __init__(self, diameter=170, parent=None):
        super().__init__(parent)
        self._d = diameter
        self.setFixedSize(diameter, diameter)
        self.setCursor(QCursor(Qt.CrossCursor))
        self._h = 0.0   # tonalita' 0..1
        self._s = 0.0   # saturazione 0..1

    def hue(self):
        return self._h

    def sat(self):
        return self._s

    def set_hs(self, h, s):
        """Posiziona il selettore senza emettere segnali."""
        self._h = max(0.0, min(0.9999, float(h)))
        self._s = max(0.0, min(1.0, float(s)))
        self.update()

    def _radius(self):
        return self._d / 2.0 - 6

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        cx = cy = self._d / 2.0
        R = self._radius()

        # corona delle tonalita'
        cone = QConicalGradient(cx, cy, 0.0)
        steps = 36
        for i in range(steps + 1):
            pos = i / steps
            cone.setColorAt(pos, QColor.fromHsvF(min(0.9999, pos), 1.0, 1.0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(cone))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # sfumatura bianca al centro = saturazione
        rad = QRadialGradient(cx, cy, R)
        rad.setColorAt(0.0, QColor(255, 255, 255, 255))
        rad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(rad))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # bordo
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#45475a"), 2))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # selettore
        ang = self._h * 2 * math.pi
        rr = self._s * R
        x = cx + rr * math.cos(ang)
        y = cy - rr * math.sin(ang)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.setPen(QPen(QColor("#11111b"), 2))
        p.drawEllipse(QPointF(x, y), 7, 7)

    def _update_from_point(self, pos):
        cx = cy = self._d / 2.0
        R = self._radius()
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.hypot(dx, dy)
        ang = math.atan2(-dy, dx)
        if ang < 0:
            ang += 2 * math.pi
        self._h = min(0.9999, ang / (2 * math.pi))
        self._s = min(1.0, dist / R)
        self.update()
        self.changed.emit()

    def mousePressEvent(self, event):
        self._update_from_point(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_from_point(event.position())

# ---------------------------------------------------------------------------
#  Riquadro cliccabile (riga di canale): emette 'clicked' quando premuto
# ---------------------------------------------------------------------------
class ClickableFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class LedStripBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._color = QColor(0, 0, 0)
        self._enabled = False
        self._refresh()

    def set_color(self, qcolor, enabled):
        self._color = qcolor
        self._enabled = enabled
        self._refresh()

    def _refresh(self):
        if self._enabled:
            c = self._color
            self.setStyleSheet(
                "border-radius: 5px; border: 1px solid #45475a;"
                f"background-color: rgb({c.red()},{c.green()},{c.blue()});")
        else:
            self.setStyleSheet(
                "border-radius: 5px; border: 1px solid #313244;"
                "background-color: #1e1e2e;")


# ---------------------------------------------------------------------------
#  Sezione comprimibile con triangolino (per nascondere i pannelli)
# ---------------------------------------------------------------------------
class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._open = True
        self._title = title
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.header = QPushButton()
        self.header.setCursor(QCursor(Qt.PointingHandCursor))
        self.header.setStyleSheet(
            "QPushButton { text-align: left; padding: 6px 8px; border: none;"
            " font-size: 16px; color: #ffffff; font-weight: bold;"
            " background-color: #181825; border-radius: 6px; }"
            "QPushButton:hover { background-color: #313244; }")
        self.header.clicked.connect(self.toggle)
        v.addWidget(self.header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(8, 8, 8, 8)
        v.addWidget(self.body)
        self._sync()

    def set_title(self, title):
        self._title = title
        self._sync()

    def add_widget(self, w):
        self.body_layout.addWidget(w)

    def add_layout(self, lay):
        self.body_layout.addLayout(lay)

    def toggle(self):
        self._open = not self._open
        self.body.setVisible(self._open)
        self._sync()

    def _sync(self):
        icon_name = "chevron_down.svg" if self._open else "chevron_right.svg"
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", icon_name)
        self.header.setIcon(QIcon(get_colored_pixmap(icon_path, 16, "#ffffff")))
        self.header.setText(f"  {self._title}")


class StripTimeline(QFrame):
    """
    Rappresentazione hardware-like di un canale LED (90 diodi) con editor multilinea.
    - Il righello superiore mostra l'output visivo finale simulato.
    - Le corsie inferiori permettono la gestione isolata delle strisce sovrapposte.
    """
    stripSelected = Signal(int)
    stripMoved    = Signal(int, int)
    stripDeleted  = Signal(int)
    stripAdded    = Signal(int, int)

    MAX_LED = 90
    WIDTH   = 15
    PAD_X   = 15
    PAD_TOP = 25
    PAD_BOT = 15
    RULER_H = 14
    LANE_H  = 22
    LANE_GAP= 6

    def __init__(self, channel, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.setMouseTracking(True)
        self._strips = []
        self._selected_id = None
        self._drag_id = None
        self._drag_offset = 0
        self._recompute_height()

    def set_strips(self, strips, selected_id):
        self._strips = list(strips)
        self._selected_id = selected_id
        self._recompute_height()
        self.update()

    def _recompute_height(self):
        """Espande dinamicamente l'altezza del widget in base al numero di strisce."""
        lanes = max(1, len(self._strips))
        h = self.PAD_TOP + self.RULER_H + 12 + (lanes * (self.LANE_H + self.LANE_GAP)) + self.PAD_BOT
        self.setFixedHeight(int(h))

    def _led_width(self):
        return (self.width() - 2 * self.PAD_X) / self.MAX_LED

    def _led_rect(self, index_0_based):
        lw = self._led_width()
        x = self.PAD_X + index_0_based * lw
        return QRectF(x, self.PAD_TOP, lw - 1.5, self.RULER_H)

    def _lane_top(self, lane_idx):
        return self.PAD_TOP + self.RULER_H + 12 + lane_idx * (self.LANE_H + self.LANE_GAP)

    def _bar_rect(self, lane_idx, start):
        lw = self._led_width()
        x = self.PAD_X + (start - 1) * lw
        w = self.WIDTH * lw - 1.5
        return QRectF(x, self._lane_top(lane_idx), w, self.LANE_H)

    def _get_led_at_x(self, x):
        if x < self.PAD_X: return 1
        if x > self.width() - self.PAD_X: return self.MAX_LED
        lw = self._led_width()
        if lw <= 0: return 1
        led = int((x - self.PAD_X) / lw) + 1
        return max(1, min(self.MAX_LED - self.WIDTH + 1, led))

    def _hit(self, pos):
        """Controlla se il mouse ha cliccato su una striscia all'interno della sua corsia."""
        for lane_idx, s in enumerate(self._strips):
            if self._bar_rect(lane_idx, s["start"]).contains(pos):
                return s
        return None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Sfondo del canale
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1e1e2e"))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 8, 8)

        # --- 1. RENDERING RIGHELLO DIODI (Output Finale Simulato) ---
        colors = [QColor("#313244")] * self.MAX_LED

        # Le strisce create prima (indice inferiore nell'array) hanno priorità visiva.
        # Stampandole al contrario, le prime sovrascrivono visivamente le ultime.
        for s in reversed(self._strips):
            c = QColor(s["r"], s["g"], s["b"])
            st = s["start"] - 1
            for i in range(st, min(self.MAX_LED, st + self.WIDTH)):
                if 0 <= i < self.MAX_LED:
                    colors[i] = c

        p.setFont(QFont("system-ui", 7, QFont.Bold))
        for led in range(1, self.MAX_LED + 1):
            # Testo e tacche (stampati ogni 10 LED o sul primo)
            if led == 1 or led % 10 == 0:
                rect = self._led_rect(led - 1)
                center_x = rect.center().x()
                p.setPen(QPen(QColor("#45475a"), 1))
                p.drawLine(int(center_x), int(self.PAD_TOP - 3), int(center_x), int(self.PAD_TOP - 8))
                p.setPen(QColor("#6c7086"))
                p.drawText(QRectF(center_x - 10, self.PAD_TOP - 22, 20, 12), Qt.AlignCenter, str(led))

            # Disegno dei singoli diodi
            p.setPen(Qt.NoPen)
            p.setBrush(colors[led - 1])
            # Disattiviamo l'antialiasing per ottenere quadrati netti e nitidi
            p.setRenderHint(QPainter.Antialiasing, False)
            p.drawRoundedRect(self._led_rect(led - 1), 2, 2)
            p.setRenderHint(QPainter.Antialiasing, True)

        # --- Testo Placeholder (Se vuoto) ---
        if not self._strips:
            p.setPen(QColor("#6c7086"))
            p.setFont(QFont("system-ui", 9))
            p.drawText(QRectF(self.PAD_X, self._lane_top(0), self.width() - 2 * self.PAD_X, self.LANE_H),
                       Qt.AlignCenter, T("fw360_no_strips_hint"))
            return

        # --- 2. RENDERING CORSIE (Editor Strisce) ---
        for lane_idx, s in enumerate(self._strips):
            r = self._bar_rect(lane_idx, s["start"])
            sel = (s["id"] == self._selected_id)

            p.setBrush(QBrush(QColor(s["r"], s["g"], s["b"])))
            p.setPen(QPen(QColor("#00e5ff") if sel else QColor("#45475a"), 2 if sel else 1))
            p.drawRoundedRect(r, 4, 4)

            # Testo all'interno della striscia (Numerazione LED occupati)
            lum = 0.299 * s["r"] + 0.587 * s["g"] + 0.114 * s["b"]
            p.setPen(QColor("#11111b") if lum > 140 else QColor("#ffffff"))
            p.setFont(QFont("system-ui", 8, QFont.Bold))
            end_led = min(s["start"] + self.WIDTH - 1, self.MAX_LED)
            p.drawText(r, Qt.AlignCenter, f"{s['start']}\u2013{end_led}")

    def mousePressEvent(self, event):
        pos = event.position()
        s = self._hit(pos)

        if event.button() == Qt.LeftButton:
            if s is not None:
                self._drag_id = s["id"]
                led_clicked = self._get_led_at_x(pos.x())
                self._drag_offset = led_clicked - s["start"]
                self.stripSelected.emit(s["id"])
        elif event.button() == Qt.RightButton:
            if s is not None:
                self.stripDeleted.emit(s["id"])

    def mouseMoveEvent(self, event):
        if self._drag_id is None:
            return
        led = self._get_led_at_x(event.position().x())
        new_start = led - self._drag_offset
        new_start = max(1, min(self.MAX_LED - self.WIDTH + 1, new_start))
        self.stripMoved.emit(self._drag_id, int(new_start))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_id = None

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        # Il doppio clic ora funziona ovunque sul widget, non solo sulla barra LED
        if self._hit(event.position()) is not None:
            return
        new_start = self._get_led_at_x(event.position().x())
        self.stripAdded.emit(self.channel, new_start)


# ---------------------------------------------------------------------------
#  TAB Farbwerk 360
# ---------------------------------------------------------------------------
# ------------------------------------------------------------------------- #
#  EDITOR DINAMICO DEGLI EFFETTI  (Blocco B1)
#  Costruisce da solo i controlli di ogni effetto leggendo la spec da EFFECTS:
#    spec.words  -> cursori numerici      spec.flags  -> checkbox
#    spec.colors -> selettori colore (singolo / sfondo+colori / lista / point+strip)
#  Le etichette usano le traduzioni (chiavi "fw360_fx_*"); finché non le aggiungiamo
#  in i18n (Blocco C) si usa una tabella inglese di riserva.
# ------------------------------------------------------------------------- #

# Ordine con cui gli effetti compaiono nel menu a tendina (Static per primo).
_FX_ORDER = [
    "static", "rotating_rainbow", "swiping_rainbow", "breathing", "color_shift",
    "color_change", "blinking", "color_sequence", "sequence", "scanner", "laser",
    "wave", "flame", "rain", "snowfall", "stardust",
]

# Parametri da NON mostrare (non ancora chiariti dal reverse engineering).
_FX_HIDE_PARAMS = {}

# Flag attivi di default (per rispecchiare i default di Aquasuite).
_FX_DEFAULT_FLAGS = {"blinking": {"fade_in", "fade_out"}}

# Etichette di riserva (inglese), usate finché le chiavi i18n non esistono.
_FX_LABELS = {
    "mode": "Mode",
    "static": "Single color", "breathing": "Breathing", "rotating_rainbow": "Rotating rainbow",
    "blinking": "Blinking", "color_change": "Color change", "sequence": "Sequence",
    "scanner": "Scanner", "laser": "Laser", "wave": "Wave", "color_sequence": "Color sequence",
    "color_shift": "Color shift", "flame": "Flame", "rain": "Rain", "snowfall": "Snowfall",
    "stardust": "Stardust", "swiping_rainbow": "Swiping rainbow",
    "speed": "Speed", "intensity": "Intensity", "delay_max": "Delay max. brightness",
    "delay_min": "Delay min. brightness", "color_range": "Color range", "smoothness": "Smoothness",
    "width": "Width", "start_delay": "Start delay", "interval_min": "Delay (min)",
    "interval_max": "Delay (max)", "delay_after": "Delay after sequence",
    "delay_before": "Delay before sequence", "total_area": "Total area",
    "drop_speed": "Drop speed", "drop_items": "Drop items", "drop_size": "Drop size",
    "drop_smoothness": "Drop smoothness", "runtime": "Runtime", "point_speed": "Point speed",
    "point_smoothness": "Point smoothness", "point_size": "Point size",
    "color_change_speed": "Color change speed",
    "reverse": "Reverse direction", "fade": "Fade", "fade_in": "Fade in", "fade_out": "Fade out",
    "random_color": "Random color", "slide_colors": "Slide colors", "color_mode2": "Color mode 2",
    "color_change": "Color change", "circular": "Circular", "snow": "Snow",
    "background": "Background", "color": "Color", "color1": "Color 1", "color2": "Color 2",
    "point_color": "Point color", "strip_color": "Strip color", "colors": "Colors",
}


def _fxlabel(key):
    """Etichetta tradotta se la chiave i18n esiste, altrimenti riserva inglese."""
    k = "fw360_fx_" + key
    s = T(k)
    if s != k:
        return s
    return _FX_LABELS.get(key, key.replace("_", " ").capitalize())


def _default_role_color(idx):
    return [(255, 0, 0), (0, 255, 0), (0, 0, 255)][idx % 3]


def _color_plan(spec):
    """Dalla spec dei colori ricava i selettori da mostrare.
    Voci: (kind, key, label) con kind in {'single','fixed','bg','list'}."""
    kind = spec.colors[0]
    if kind == 'single':
        return [('single', 'color', 'color')]
    if kind == 'point_strip':
        return [('fixed', 'point_color', 'point_color'),
                ('fixed', 'strip_color', 'strip_color')]
    if kind == 'roles':
        plan = []
        for role in spec.colors[1]:
            plan.append(('bg', 'background', 'background') if role == 'background'
                        else ('fixed', role, role))
        return plan
    if kind == 'list':
        plan = []
        if spec.colors[2]:            # has_bg
            plan.append(('bg', 'background', 'background'))
        plan.append(('list', 'colors', 'colors'))
        return plan
    return []                          # 'rainbow' o sconosciuto: nessun colore utente


class _FxColorButton(QPushButton):
    """Piccolo pulsante-campione che apre il selettore colore."""
    picked = Signal()

    def __init__(self, rgb=(255, 0, 0), parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 24)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._rgb = tuple(int(x) & 255 for x in rgb)
        self._refresh()
        self.clicked.connect(self._choose)

    def rgb(self):
        return self._rgb

    def set_rgb(self, rgb):
        self._rgb = tuple(int(x) & 255 for x in rgb)
        self._refresh()

    def _refresh(self):
        r, g, b = self._rgb
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border:1px solid #45475a; border-radius:4px;")

    def _choose(self):
        r, g, b = self._rgb
        c = QColorDialog.getColor(QColor(r, g, b), None, T("select_color"))
        if c.isValid():
            self._rgb = (c.red(), c.green(), c.blue())
            self._refresh()
            self.picked.emit()


class _FxColorList(QWidget):
    """Lista di colori con "+" (aggiungi) e "−" (togli l'ultimo)."""
    changed = Signal()

    def __init__(self, colors=None, max_colors=6, parent=None):
        super().__init__(parent)
        self._max = int(max_colors)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self._chips_host = QWidget()
        self._chips = QHBoxLayout(self._chips_host)
        self._chips.setContentsMargins(0, 0, 0, 0)
        self._chips.setSpacing(4)
        row.addWidget(self._chips_host)
        self._add = QPushButton("+"); self._add.setFixedSize(24, 24)
        self._add.setCursor(QCursor(Qt.PointingHandCursor)); self._add.clicked.connect(self._on_add)
        self._del = QPushButton("\u2212"); self._del.setFixedSize(24, 24)
        self._del.setCursor(QCursor(Qt.PointingHandCursor)); self._del.clicked.connect(self._on_del)
        for b in (self._add, self._del):
            b.setStyleSheet("QPushButton{background:#313244;color:#cdd6f4;border:1px solid #45475a;"
                            "border-radius:4px;font-weight:bold;}QPushButton:hover{background:#45475a;}")
        row.addWidget(self._add); row.addWidget(self._del); row.addStretch()
        self._buttons = []
        self.set_colors(colors or [(255, 0, 0)])

    def colors(self):
        return [b.rgb() for b in self._buttons]

    def set_colors(self, colors):
        while self._buttons:
            self._buttons.pop().setParent(None)
        for rgb in (colors or [(255, 0, 0)]):
            self._append(tuple(rgb))
        self._sync()

    def _append(self, rgb):
        if len(self._buttons) >= self._max:
            return
        b = _FxColorButton(rgb)
        b.picked.connect(self._bubble)
        self._chips.addWidget(b)
        self._buttons.append(b)

    def _bubble(self):
        self.changed.emit()

    def _on_add(self):
        self._append((255, 0, 0)); self._sync(); self.changed.emit()

    def _on_del(self):
        if len(self._buttons) > 1:
            self._buttons.pop().setParent(None); self._sync(); self.changed.emit()

    def _sync(self):
        self._add.setEnabled(len(self._buttons) < self._max)
        self._del.setEnabled(len(self._buttons) > 1)


class EffectEditor(QWidget):
    """Pannello parametri che si ricostruisce in base all'effetto scelto."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._spec = None
        self._loading = False
        self._color_widgets = {}     # ruolo -> _FxColorButton
        self._color_list = None      # _FxColorList (effetti a lista)
        self._param_sliders = {}     # nome -> (QSlider, QLabel valore)
        self._flag_checks = {}       # nome -> QCheckBox
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(0, 6, 0, 0)
        self._v.setSpacing(6)

    def set_effect(self, mode, fx=None):
        self._spec = EFFECTS.get(mode)
        self._clear()
        if self._spec is None:
            return
        self._loading = True
        fx = fx or {}
        params_in = fx.get("params", {}) or {}
        flags_in = fx.get("flags", {}) or {}
        colors_in = [tuple(c) for c in (fx.get("colors") or [])]
        bg_in = fx.get("background")

        # --- colori ---
        idx = 0
        for kind, key, label in _color_plan(self._spec):
            if kind == 'list':
                self._color_list = _FxColorList(colors_in or [(255, 0, 0)], max_colors=6)
                self._color_list.changed.connect(self._emit)
                self._v.addWidget(self._labeled(_fxlabel(label), self._color_list))
            else:
                if key == 'background':
                    rgb = tuple(bg_in) if bg_in is not None else (10, 10, 10)
                else:
                    rgb = colors_in[idx] if idx < len(colors_in) else _default_role_color(idx)
                    idx += 1
                btn = _FxColorButton(rgb)
                btn.picked.connect(self._emit)
                self._color_widgets[key] = btn
                self._v.addWidget(self._labeled(_fxlabel(label), btn))

        # --- parametri numerici ---
        hide = _FX_HIDE_PARAMS.get(mode, set())
        for name, k in self._spec.words.items():
            if name == 'count' or name in hide:
                continue
            default = self._spec.default_words[k] if k < len(self._spec.default_words) else 0
            val = max(0, min(100, int(params_in.get(name, default))))
            lo = 1 if name == 'width' else 0
            row, slider, vlab = self._slider_row(_fxlabel(name), lo, 100, val)
            self._param_sliders[name] = (slider, vlab)
            self._v.addWidget(row)

        # --- flag ---
        defon = _FX_DEFAULT_FLAGS.get(mode, set())
        for name in self._spec.flags:
            ck = QCheckBox(_fxlabel(name)); ck.setStyleSheet("color:#cdd6f4;")
            ck.setChecked(bool(flags_in.get(name, name in defon)))
            ck.toggled.connect(self._emit)
            self._flag_checks[name] = ck
            self._v.addWidget(ck)

        self._loading = False

    def export(self):
        fx = {"params": {}, "flags": {}, "colors": [], "background": None}
        for name, (sl, _) in self._param_sliders.items():
            fx["params"][name] = int(sl.value())
        for name, ck in self._flag_checks.items():
            fx["flags"][name] = bool(ck.isChecked())
        for key, w in self._color_widgets.items():
            if key == 'background':
                fx["background"] = w.rgb()
            else:
                fx["colors"].append(w.rgb())
        if self._color_list is not None:
            fx["colors"] = self._color_list.colors()
        return fx

    def display_color(self):
        fx = self.export()
        if fx["colors"]:
            return tuple(fx["colors"][0])
        if fx["background"] is not None:
            return tuple(fx["background"])
        return (0, 229, 255)

    # -- helper interni --
    def _emit(self, *a):
        if not self._loading:
            self.changed.emit()

    def _labeled(self, text, widget):
        host = QWidget(); row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(text); lab.setFixedWidth(150); lab.setStyleSheet("color:#cdd6f4;")
        row.addWidget(lab); row.addWidget(widget); row.addStretch()
        return host

    def _slider_row(self, text, lo, hi, val):
        host = QWidget(); row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(text); lab.setFixedWidth(150); lab.setStyleSheet("color:#cdd6f4;")
        sl = QSlider(Qt.Horizontal); sl.setRange(lo, hi); sl.setValue(val)
        vlab = QLabel(str(val)); vlab.setFixedWidth(32); vlab.setStyleSheet("color:#cdd6f4;")
        sl.valueChanged.connect(lambda v, L=vlab: L.setText(str(v)))
        sl.valueChanged.connect(self._emit)
        row.addWidget(lab); row.addWidget(sl, 1); row.addWidget(vlab)
        return host, sl, vlab

    def _clear(self):
        self._color_widgets = {}; self._color_list = None
        self._param_sliders = {}; self._flag_checks = {}
        while self._v.count():
            it = self._v.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)

class Farbwerk360TabWidget(QWidget):
    PRESETS = [
        # Scala di grigi
        ("#FFFFFF", "#EEEEEE", "#DDDDDD", "#CCCCCC", "#BBBBBB", "#AAAAAA", "#999999", "#888888", "#777777", "#666666", "#555555", "#444444", "#333333", "#222222", "#111111", "#000000"),
        # Rossi, Arancioni e Marroni
        ("#FFEBEB", "#FFC2C2", "#FF9999", "#FF7070", "#FF4747", "#FF1F1F", "#F00000", "#C20000", "#940000", "#660000", "#FFDAB9", "#FFA07A", "#FF7F50", "#FF4500", "#D2691E", "#8B4513"),
        # Gialli e Verdi
        ("#FFFFE0", "#FFFACD", "#FFD700", "#FFC100", "#FFA500", "#ADFF2F", "#7FFF00", "#32CD32", "#00FF00", "#228B22", "#008000", "#006400", "#9ACD32", "#6B8E23", "#808000", "#556B2F"),
        # Ciani, Acqua e Azzurri
        ("#E0FFFF", "#AFEEEE", "#7FFFD4", "#40E0D0", "#48D1CC", "#00CED1", "#00FFFF", "#00BFFF", "#1E90FF", "#4169E1", "#0000FF", "#0000CD", "#00008B", "#008080", "#008B8B", "#2F4F4F"),
        # Viola, Magenta e Rosa
        ("#E6E6FA", "#D8BFD8", "#DDA0DD", "#EE82EE", "#FF00FF", "#BA55D3", "#9932CC", "#9400D3", "#8A2BE2", "#4B0082", "#800080", "#8B008B", "#FFB6C1", "#FF69B4", "#FF1493", "#C71585"),
    ]
    NUM_CHANNELS = 4
    MAX_STRIPS   = 20
    STRIP_WIDTH  = 15
    MAX_LED      = 90

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._updating = False
        self.global_brightness = int(global_config.get("fw360_brightness", 100))

        self.strips = []
        self._next_id = 1
        self.selected_id = None
        self._h, self._s, self._v = 0.0, 1.0, 1.0

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(250)
        self._save_timer.timeout.connect(self._save_now)

        self._load_from_config()

        root = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "farbwerk360.svg")
        lbl_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        header_layout.addWidget(lbl_icon)

        lbl_title = QLabel(T('tab_farbwerk360'))
        lbl_title.setStyleSheet(f"font-size: 24px; color: {get_accent()}; font-weight: bold;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        root.addLayout(header_layout)
        root.addSpacing(4)

        lbl_sub = QLabel(T("fw360_subtitle"))
        lbl_sub.setStyleSheet("color: #a6adc8; margin-bottom: 15px; font-size: 14px;")
        lbl_sub.setWordWrap(True)
        root.addWidget(lbl_sub)

        lbl_help = QLabel(T("fw360_timeline_help"))
        lbl_help.setStyleSheet("color: #a6adc8; font-size: 13px; font-style: italic; margin-bottom: 12px;")
        lbl_help.setWordWrap(True)
        root.addWidget(lbl_help)

        # ===================== LAYOUT A COLONNA SINGOLA =====================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        scroll.setWidget(container)
        self.main_scroll_layout = QVBoxLayout(container)
        self.main_scroll_layout.setSpacing(15)

        self.timelines = {}
        self.channel_sections = {}

        for ch in range(1, self.NUM_CHANNELS + 1):
            is_la = global_config.get("lang") == "la"
            num_str = to_roman(ch) if is_la else str(ch)
            sec = CollapsibleSection(T("fw360_ch").format(i=num_str))
            self.channel_sections[ch] = sec

            bar = QHBoxLayout()
            btn_add = QPushButton(f" {T('fw360_add_strip')}")
            icon_add = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "add.svg")
            btn_add.setIcon(QIcon(get_colored_pixmap(icon_add, 16, "#cdd6f4")))
            btn_add.setCursor(QCursor(Qt.PointingHandCursor))
            btn_add.setStyleSheet(
                "QPushButton { background-color: #313244; color: #cdd6f4;"
                " border: 1px solid #45475a; border-radius: 6px; padding: 5px 12px; font-weight: bold; }"
                "QPushButton:hover { background-color: #45475a; }")
            btn_add.clicked.connect(lambda _=None, c=ch: self._add_strip(c, 1))

            btn_clear = QPushButton(f" {T('fw360_clear_channel')}")
            icon_trash = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "trash.svg")
            btn_clear.setIcon(QIcon(get_colored_pixmap(icon_trash, 16, "#a6adc8")))
            btn_clear.setCursor(QCursor(Qt.PointingHandCursor))
            btn_clear.setStyleSheet(
                "QPushButton { background-color: #181825; color: #a6adc8;"
                " border: 1px solid #45475a; border-radius: 6px; padding: 5px 12px; }"
                "QPushButton:hover { background-color: #45475a; color: #f38ba8; }")
            btn_clear.clicked.connect(lambda _=None, c=ch: self._clear_channel(c))

            bar.addWidget(btn_add)
            bar.addWidget(btn_clear)
            bar.addStretch()
            sec.add_layout(bar)

            tl = StripTimeline(ch)
            tl.stripSelected.connect(self._on_strip_selected)
            tl.stripMoved.connect(self._on_strip_moved)
            tl.stripDeleted.connect(self._remove_strip)
            tl.stripAdded.connect(self._on_strip_added)
            self.timelines[ch] = tl
            sec.add_widget(tl)
            self.main_scroll_layout.addWidget(sec)

        # ---- LUMINOSITÀ GLOBALE (Libera e sempre visibile) ----
        g_row = QHBoxLayout()
        lbl_gb = QLabel(T("fw360_brightness"))
        lbl_gb.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        lbl_gb.setFixedWidth(170)
        self.slider_gb = QSlider(Qt.Horizontal)
        self.slider_gb.setRange(0, 100)
        self.slider_gb.setValue(self.global_brightness)
        self.lbl_gb_val = QLabel(f"{self.global_brightness} %")
        self.lbl_gb_val.setFixedWidth(48)
        self.lbl_gb_val.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.slider_gb.valueChanged.connect(self._global_brightness_changed)
        g_row.addWidget(lbl_gb)
        g_row.addWidget(self.slider_gb, 1)
        g_row.addWidget(self.lbl_gb_val)

        # Aggiungiamo la riga della luminosità direttamente al layout principale
        self.main_scroll_layout.addLayout(g_row)
        self.main_scroll_layout.addSpacing(15)

        # ---- PREFERENZE (Sezione comprimibile per le spunte) ----
        sec_pref = CollapsibleSection(T("fw360_general"))
        lbl_pref_desc = QLabel(T("fw360_pref_desc"))
        lbl_pref_desc.setStyleSheet("color: #ffc107; font-size: 13px; font-style: italic; margin-bottom: 12px;")
        lbl_pref_desc.setWordWrap(True)
        sec_pref.add_widget(lbl_pref_desc)

        self.chk_apply_on_start = QCheckBox(T("fw360_apply_on_start"))
        self.chk_apply_on_start.setStyleSheet("color: #cdd6f4;")
        self.chk_apply_on_start.setChecked(global_config.get("fw360_apply_on_start", False))
        self.chk_apply_on_start.toggled.connect(self._general_settings_changed)

        self.chk_apply_on_resume = QCheckBox(T("fw360_apply_on_resume"))
        self.chk_apply_on_resume.setStyleSheet("color: #cdd6f4;")
        self.chk_apply_on_resume.setChecked(global_config.get("fw360_apply_on_resume", False))
        self.chk_apply_on_resume.toggled.connect(self._general_settings_changed)

        sec_pref.add_widget(self.chk_apply_on_start)
        sec_pref.add_widget(self.chk_apply_on_resume)

        self.main_scroll_layout.addWidget(sec_pref)
        self.main_scroll_layout.addStretch()

        root.addWidget(scroll)

        # ---- TASTO SALVATAGGIO ----
        self.btn_save = QPushButton(f" {T('fw360_save_device')}")
        icon_save = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "save.svg")
        self.btn_save.setIcon(QIcon(get_colored_pixmap(icon_save, 16, "#11111b")))
        self.btn_save.setObjectName("ActionBtn")
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.setToolTip(T("fw360_flash_tip"))
        self.btn_save.clicked.connect(self.save_to_flash)
        root.addWidget(self.btn_save)

        # COSTRUZIONE DEL PANNELLO EDITOR DINAMICO
        self._build_dynamic_editor()

        self._refresh_all_timelines()
        self._refresh_editor()

        # Al primo avvio dopo un aggiornamento la config può avere le strisce ma non il
        # payload: lo popoliamo qui (senza inviare nulla) così il demone può applicare
        # all'avvio del sistema anche prima che l'utente riapra questa scheda.
        if "fw360_payload" not in global_config and self.strips:
            self._persist_to_config()

    def _make_spin(self, color):
        sp = RomanSpinBox(); sp.setRange(0, 255)
        sp.setStyleSheet(f"color: {color}; font-weight: bold;")
        sp.valueChanged.connect(self._rgb_changed)
        return sp

    def _general_settings_changed(self):
        """Salva lo stato delle spunte per l'avvio e la sospensione."""
        global_config["fw360_apply_on_start"] = self.chk_apply_on_start.isChecked()
        global_config["fw360_apply_on_resume"] = self.chk_apply_on_resume.isChecked()
        save_config(global_config)

    def _load_from_config(self):
        for item in global_config.get("fw360_strips", []):
            try:
                ch = int(item["channel"]); st = int(item["start"])
                r, g, b = int(item["r"]), int(item["g"]), int(item["b"])
            except (KeyError, ValueError, TypeError):
                continue
            ch = max(1, min(self.NUM_CHANNELS, ch))
            st = max(1, min(self.MAX_LED - self.STRIP_WIDTH + 1, st))
            strip = {"id": self._next_id, "channel": ch, "start": st,
                     "r": r & 255, "g": g & 255, "b": b & 255,
                     "mode": item.get("mode", "static")}
            fx = item.get("fx")
            if isinstance(fx, dict) and strip["mode"] != "static":
                strip["fx"] = fx
            self.strips.append(strip)
            self._next_id += 1
        if self.strips and self.selected_id is None:
            self.selected_id = self.strips[0]["id"]

    def _schedule_save(self):
        self._save_timer.start()

    def _persist_to_config(self):
        """Serializza strisce, luminosità e il payload GIA' COSTRUITO nella config.
        Il payload lo costruisce la GUI (qui), l'invio alla scheda lo fa il demone."""
        out = []
        for s in self.strips:
            d = {"channel": s["channel"], "start": s["start"],
                 "r": s["r"], "g": s["g"], "b": s["b"],
                 "mode": s.get("mode", "static")}
            if s.get("mode", "static") != "static" and "fx" in s:
                d["fx"] = s["fx"]
            out.append(d)
        global_config["fw360_strips"] = out
        global_config["fw360_brightness"] = self.global_brightness
        global_config["fw360_payload"] = self._build_payload_hex()
        try:
            save_config(global_config)
        except Exception:
            pass

    def _build_payload_hex(self):
        """Costruisce il payload della Farbwerk dalle strisce correnti SENZA toccare
        l'USB (nessun commit): serve solo a ricavare i byte che il demone invierà."""
        eng = Farbwerk360EffectsEngine()
        eng.all_off()
        eng.clear_strips()
        for s in self.strips:
            mode = s.get("mode", "static")
            if mode == "static":
                eng.add_strip(s["channel"], s["start"], s["r"], s["g"], s["b"])
            else:
                try:
                    eng.add_effect(s["channel"], s["start"], mode, **self._effect_kwargs(s))
                except Exception:
                    eng.add_strip(s["channel"], s["start"], s["r"], s["g"], s["b"])
        eng.set_brightness_percent(self.global_brightness)
        return eng.build_hex()

    def _save_now(self):
        self._persist_to_config()
        # Anteprima live: il demone applica adesso (il debounce di 250 ms è già a monte
        # su _save_timer). La GUI non tocca più l'USB della Farbwerk.
        self.main_window.send_daemon_command({"action": "apply_rgb"})

    def _build_dynamic_editor(self):
        """Costruisce l'editor dinamico, spostato via layout."""
        self.dynamic_editor_host = QFrame()
        self.dynamic_editor_host.setVisible(False)
        self.dynamic_editor_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum) # FIX: Permette al frame di espandersi
        self.dynamic_editor_host.setStyleSheet(
            "QFrame#DynEditor { background-color: rgba(30, 30, 46, 120); "
            "border: 1px solid rgba(255, 255, 255, 15); border-radius: 8px; }"
        )
        self.dynamic_editor_host.setObjectName("DynEditor")

        dyn_layout = QVBoxLayout(self.dynamic_editor_host)
        dyn_layout.setContentsMargins(15, 15, 15, 15)
        dyn_layout.setSpacing(15)

        # 1. Toolbar (Mode + duplicate + remove + hide)
        toolbar_row = QHBoxLayout()
        lab_mode = QLabel(_fxlabel("mode"))
        lab_mode.setStyleSheet("color: #cdd6f4; font-weight: bold; border: none; background: transparent;")
        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet("QComboBox { background: #313244; color: #cdd6f4; border-radius: 4px; padding: 4px 10px; font-weight: bold; }")
        for name in _FX_ORDER:
            self.mode_combo.addItem(_fxlabel(name), name)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        toolbar_row.addWidget(lab_mode)
        toolbar_row.addWidget(self.mode_combo)

        toolbar_row.addStretch()

        self.btn_toggle_settings = QPushButton()
        self.btn_toggle_settings.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "settings.svg")))
        self.btn_toggle_settings.setFixedSize(32, 32)
        self.btn_toggle_settings.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_toggle_settings.setStyleSheet("QPushButton { background-color: #313244; border-radius: 6px; } QPushButton:hover { background-color: #45475a; }")
        self.btn_toggle_settings.clicked.connect(self._toggle_settings_panel)

        self.btn_dup = QPushButton()
        self.btn_dup.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "duplicate.svg")))
        self.btn_dup.setFixedSize(32, 32)
        self.btn_dup.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_dup.setStyleSheet("QPushButton { background-color: #313244; border-radius: 6px; } QPushButton:hover { background-color: #45475a; }")
        self.btn_dup.clicked.connect(self._duplicate_selected)

        self.btn_remove = QPushButton()
        self.btn_remove.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "close.svg")))
        self.btn_remove.setFixedSize(32, 32)
        self.btn_remove.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_remove.setStyleSheet("QPushButton { background-color: #313244; border-radius: 6px; } QPushButton:hover { background-color: #f38ba8; }")
        self.btn_remove.clicked.connect(self._remove_selected)

        toolbar_row.addWidget(self.btn_toggle_settings)
        toolbar_row.addWidget(self.btn_dup)
        toolbar_row.addWidget(self.btn_remove)

        dyn_layout.addLayout(toolbar_row)

        # 2. Settings Panel
        self.settings_panel = QWidget()
        self.settings_panel.setVisible(False) # Chiuso di default, come Aquasuite
        self.settings_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum) # FIX: Permette al pannello setting di spingere in basso
        self.settings_panel.setStyleSheet("border: none; background: transparent;")
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        # A) Effect Editor Dinamico
        self.effect_editor = EffectEditor()
        self.effect_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum) # FIX
        self.effect_editor.changed.connect(self._on_effect_changed)
        settings_layout.addWidget(self.effect_editor)

        # B) Static Editor
        self.editor_host = QWidget()
        self.editor_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum) # FIX
        self.editor_host.setMinimumHeight(220) # Forza un'altezza minima per ruota colori e palette

        editor = QHBoxLayout(self.editor_host)
        editor.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        self.wheel = ColorWheel(170)
        self.wheel.changed.connect(self._wheel_changed)
        left.addWidget(self.wheel, alignment=Qt.AlignHCenter)
        val_row = QHBoxLayout()
        lbl_v = QLabel(T("fw360_value")); lbl_v.setStyleSheet("color: #cdd6f4;")
        self.slider_v = QSlider(Qt.Horizontal)
        self.slider_v.setRange(0, 100); self.slider_v.setValue(100)
        self.slider_v.valueChanged.connect(self._value_changed)
        self.lbl_v_val = QLabel("100%"); self.lbl_v_val.setFixedWidth(42)
        self.lbl_v_val.setStyleSheet("color: #cdd6f4;")
        val_row.addWidget(lbl_v); val_row.addWidget(self.slider_v, 1); val_row.addWidget(self.lbl_v_val)
        left.addLayout(val_row)
        editor.addLayout(left)
        editor.addSpacing(18)

        mid = QVBoxLayout()
        self.swatch = QFrame()
        self.swatch.setFixedSize(60, 60)
        self.swatch.setStyleSheet("border-radius: 6px; border: 1px solid #45475a; background:#00e5ff;")
        mid.addWidget(self.swatch)
        self.spin_r = self._make_spin("#ff5555")
        self.spin_g = self._make_spin("#50fa7b")
        self.spin_b = self._make_spin("#00e5ff")

        for lblkey, sp in (("fw360_r", self.spin_r), ("fw360_g", self.spin_g), ("fw360_b", self.spin_b)):
            rr = QHBoxLayout()
            lab = QLabel(T(lblkey))
            lab.setMinimumWidth(45)
            lab.setStyleSheet("color: #cdd6f4; font-weight: bold;")
            rr.addWidget(lab)
            rr.addWidget(sp)
            mid.addLayout(rr)

        hexrow = QHBoxLayout()
        lab_hex = QLabel("#")
        lab_hex.setMinimumWidth(45)
        lab_hex.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        self.edit_hex = QLineEdit("00E5FF")
        self.edit_hex.setMaxLength(9)
        self.edit_hex.setFixedWidth(110)
        self.edit_hex.editingFinished.connect(self._hex_changed)
        hexrow.addWidget(lab_hex)
        hexrow.addWidget(self.edit_hex)
        mid.addLayout(hexrow)
        mid.addStretch()
        editor.addLayout(mid)
        editor.addSpacing(18)

        pal = QGridLayout()
        pal.setSpacing(2)
        lbl_pal = QLabel(T("fw360_palette"))
        lbl_pal.setStyleSheet("color: #cdd6f4;")

        # Col-span dinamico che si adatta a 12 colonne
        pal.addWidget(lbl_pal, 0, 0, 1, len(self.PRESETS[0]))

        for r_i, rowcols in enumerate(self.PRESETS):
            for c_i, hexv in enumerate(rowcols):
                b = QPushButton()
                b.setFixedSize(24, 24)
                b.setCursor(QCursor(Qt.PointingHandCursor))
                b.setStyleSheet(f"background-color: {hexv}; border: 1px solid #45475a; border-radius: 3px;")
                b.clicked.connect(lambda _=None, hv=hexv: self._apply_preset_hex(hv))
                pal.addWidget(b, r_i + 1, c_i)

        pal_host = QWidget()
        pal_host.setLayout(pal)
        editor.addWidget(pal_host, alignment=Qt.AlignTop)
        editor.addStretch()

        settings_layout.addWidget(self.editor_host)
        dyn_layout.addWidget(self.settings_panel)

    def _on_mode_changed(self, idx):
        if self._updating:
            return
        s = self._strip_by_id(self.selected_id)
        if s is None:
            return
        mode = self.mode_combo.itemData(idx)
        if mode is None or mode == s.get("mode", "static"):
            return
        s["mode"] = mode
        if mode == "static":
            s.pop("fx", None)
        else:
            self.effect_editor.set_effect(mode, None)
            s["fx"] = self.effect_editor.export()
            r, g, b = self.effect_editor.display_color()
            s["r"], s["g"], s["b"] = r, g, b
        self._refresh_editor()
        self._refresh_timeline(s["channel"])
        self._schedule_save()

    def _on_effect_changed(self):
        s = self._strip_by_id(self.selected_id)
        if s is None or s.get("mode", "static") == "static":
            return
        s["fx"] = self.effect_editor.export()
        r, g, b = self.effect_editor.display_color()
        s["r"], s["g"], s["b"] = r, g, b
        self._refresh_timeline(s["channel"])
        self._schedule_save()

    def _effect_kwargs(self, strip):
        mode = strip.get("mode", "static")
        fx = strip.get("fx", {}) or {}
        call = dict(fx.get("params", {}) or {})
        call.update(fx.get("flags", {}) or {})
        cols = [tuple(c) for c in (fx.get("colors") or [])]
        kind = EFFECTS[mode].colors[0]
        if kind == 'point_strip':
            if len(cols) >= 1:
                call["point_color"] = cols[0]
            if len(cols) >= 2:
                call["strip_color"] = cols[1]
        else:
            if cols:
                call["colors"] = cols
            if fx.get("background") is not None:
                call["background"] = tuple(fx["background"])
        return call

    # ---------------------------------------------------------------- helper
    def _strip_by_id(self, sid):
        for s in self.strips:
            if s["id"] == sid:
                return s
        return None

    def _channel_strips(self, ch):
        return [s for s in self.strips if s["channel"] == ch]

    def _refresh_all_timelines(self):
        for ch, tl in self.timelines.items():
            tl.set_strips(self._channel_strips(ch), self.selected_id)

    def _refresh_timeline(self, ch):
        self.timelines[ch].set_strips(self._channel_strips(ch), self.selected_id)

    # ------------------------------------------------------ creazione / rimozione
    def _default_color(self):
        s = self._strip_by_id(self.selected_id)
        if s is not None:
            return s["r"], s["g"], s["b"]
        return 0, 229, 255

    def _add_strip(self, channel, start):
        if len(self.strips) >= self.MAX_STRIPS:
            QMessageBox.information(self, T("fw360_strips"), T("fw360_max_strips"))
            return
        r, g, b = self._default_color()
        sid = self._next_id; self._next_id += 1
        self.strips.append({"id": sid, "channel": int(channel),
                            "start": int(start), "r": r, "g": g, "b": b,
                            "mode": "static"})
        self.selected_id = sid
        self._refresh_all_timelines()
        self._refresh_editor()
        self._schedule_save()

    def _on_strip_added(self, channel, start):
        self._add_strip(channel, start)

    def _remove_strip(self, sid):
        s = self._strip_by_id(sid)
        if s is None:
            return
        self.strips.remove(s)
        if self.selected_id == sid:
            self.selected_id = None
        self._refresh_all_timelines()
        self._refresh_editor()
        self._schedule_save()

    def _remove_selected(self):
        if self.selected_id is not None:
            self._remove_strip(self.selected_id)

    def _duplicate_selected(self):
        s = self._strip_by_id(self.selected_id)
        if s is None:
            return
        if len(self.strips) >= self.MAX_STRIPS:
            QMessageBox.information(self, T("fw360_strips"), T("fw360_max_strips"))
            return
        sid = self._next_id
        self._next_id += 1
        new = {"id": sid, "channel": s["channel"],
               "start": min(self.MAX_LED - self.STRIP_WIDTH + 1, int(s["start"]) + self.STRIP_WIDTH),
               "r": s["r"], "g": s["g"], "b": s["b"],
               "mode": s.get("mode", "static")}
        fx = s.get("fx")
        if isinstance(fx, dict):
            new["fx"] = {
                "params": dict(fx.get("params", {}) or {}),
                "flags": dict(fx.get("flags", {}) or {}),
                "colors": [tuple(c) for c in (fx.get("colors") or [])],
                "background": tuple(fx["background"]) if fx.get("background") is not None else None,
            }
        self.strips.append(new)
        self.selected_id = sid
        self._refresh_all_timelines()
        self._refresh_editor()
        self._schedule_save()

    def _clear_channel(self, ch):
        removed = self._channel_strips(ch)
        if not removed:
            return
        ids = {s["id"] for s in removed}
        self.strips = [s for s in self.strips if s["id"] not in ids]
        if self.selected_id in ids:
            self.selected_id = None
        self._refresh_all_timelines()
        self._refresh_editor()
        self._schedule_save()

    # ------------------------------------------------------ selezione / spostamento
    def _on_strip_selected(self, sid):
        self.selected_id = sid
        self._refresh_all_timelines()
        self._refresh_editor()

    def _on_strip_moved(self, sid, new_start):
        s = self._strip_by_id(sid)
        if s is None:
            return
        s["start"] = int(new_start)
        self._refresh_timeline(s["channel"])
        self._schedule_save()

    # ---------------------------------------------------------------- editor
    def _toggle_settings_panel(self):
        vis = not self.settings_panel.isVisible()
        self.settings_panel.setVisible(vis)

    def _refresh_editor(self):
        s = self._strip_by_id(self.selected_id)
        has = s is not None
        self.dynamic_editor_host.setVisible(has)

        if not has:
            return

        # Sposta l'editor all'interno del layout del canale attualmente selezionato
        target_layout = self.channel_sections[s["channel"]].body_layout
        if self.dynamic_editor_host.parentWidget() != self.channel_sections[s["channel"]].body:
            target_layout.addWidget(self.dynamic_editor_host)

        mode = s.get("mode", "static")
        self._updating = True
        i = self.mode_combo.findData(mode)
        if i >= 0:
            self.mode_combo.setCurrentIndex(i)
        self._updating = False

        if mode == "static":
            self.effect_editor.setVisible(False)
            self.editor_host.setVisible(True)
            self._h, self._s, self._v = self._rgb_to_hsv(s["r"], s["g"], s["b"])
            self._load_editor_widgets()
        else:
            self.editor_host.setVisible(False)
            self.effect_editor.setVisible(True)
            self.effect_editor.set_effect(mode, s.get("fx"))

    def _load_editor_widgets(self):
        self._updating = True
        self.wheel.set_hs(self._h, self._s)
        self.slider_v.setValue(int(round(self._v * 100)))
        self.lbl_v_val.setText(f"{int(round(self._v*100))}%")
        r, g, b = self._hsv_to_rgb(self._h, self._s, self._v)
        self.spin_r.setValue(r); self.spin_g.setValue(g); self.spin_b.setValue(b)
        self.edit_hex.setText(f"{r:02X}{g:02X}{b:02X}")
        self._update_swatch(r, g, b)
        self._updating = False

    @staticmethod
    def _hsv_to_rgb(h, s, v):
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))

    def _rgb_to_hsv(self, r, g, b):
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if s <= 0.0001:
            h = self._h  # su un grigio mantieni la tonalita' attuale della ruota
        return h, s, v

    def _update_swatch(self, r, g, b):
        self.swatch.setStyleSheet(
            f"border-radius: 6px; border: 1px solid #45475a; background: rgb({r},{g},{b});")

    def _commit_color_to_strip(self):
        s = self._strip_by_id(self.selected_id)
        if s is None:
            return
        s["r"], s["g"], s["b"] = self._hsv_to_rgb(self._h, self._s, self._v)
        self._refresh_timeline(s["channel"])
        self._schedule_save()

    # -- callback della ruota / rgb / hex / valore
    def _wheel_changed(self):
        if self._updating:
            return
        self._h = self.wheel.hue(); self._s = self.wheel.sat()
        self._sync_after_change(skip_wheel=True)

    def _value_changed(self, val):
        self.lbl_v_val.setText(f"{val}%")
        if self._updating:
            return
        self._v = val / 100.0
        self._sync_after_change(skip_value=True)

    def _rgb_changed(self, _=None):
        if self._updating:
            return
        self._h, self._s, self._v = self._rgb_to_hsv(
            self.spin_r.value(), self.spin_g.value(), self.spin_b.value())
        self._sync_after_change(skip_rgb=True)

    def _hex_changed(self):
        if self._updating:
            return
        rgb = self._parse_hex(self.edit_hex.text())
        if rgb is None:
            self._load_editor_widgets()
            return
        self._h, self._s, self._v = self._rgb_to_hsv(*rgb)
        self._sync_after_change(skip_hex=True)

    def _apply_preset_hex(self, hexv):
        if self.selected_id is None:
            return
        rgb = self._parse_hex(hexv)
        if rgb is None:
            return
        self._h, self._s, self._v = self._rgb_to_hsv(*rgb)
        self._sync_after_change()

    def _sync_after_change(self, skip_wheel=False, skip_value=False,
                           skip_rgb=False, skip_hex=False):
        r, g, b = self._hsv_to_rgb(self._h, self._s, self._v)
        self._updating = True
        if not skip_wheel:
            self.wheel.set_hs(self._h, self._s)
        if not skip_value:
            self.slider_v.setValue(int(round(self._v * 100)))
            self.lbl_v_val.setText(f"{int(round(self._v*100))}%")
        if not skip_rgb:
            self.spin_r.setValue(r); self.spin_g.setValue(g); self.spin_b.setValue(b)
        if not skip_hex:
            self.edit_hex.setText(f"{r:02X}{g:02X}{b:02X}")
        self._update_swatch(r, g, b)
        self._updating = False
        self._commit_color_to_strip()

    def _global_brightness_changed(self, val):
        self.global_brightness = val
        self.lbl_gb_val.setText(f"{val} %")
        self._schedule_save()

    @staticmethod
    def _parse_hex(s):
        s = s.strip().lstrip('#').upper()
        if len(s) == 8:      # AARRGGBB (formato Aquasuite): scarta l'alpha
            s = s[2:]
        if len(s) == 6:
            try:
                return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
            except ValueError:
                return None
        return None

    # ---------------------------------------------------------------- invio
    def _apply_state_to_engine(self):
        eng = self.main_window.fw360_engine
        if not eng.is_connected:
            eng.connect()
        eng.all_off()
        eng.clear_strips()
        for s in self.strips:
            mode = s.get("mode", "static")
            if mode == "static":
                eng.add_strip(s["channel"], s["start"], s["r"], s["g"], s["b"])
            else:
                try:
                    eng.add_effect(s["channel"], s["start"], mode, **self._effect_kwargs(s))
                except Exception:
                    eng.add_strip(s["channel"], s["start"], s["r"], s["g"], s["b"])
        eng.set_brightness_percent(self.global_brightness)
        return eng

    def _flash_button(self, btn, ok, ok_key, reset_key):
        icon_check = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "check.svg")
        icon_save = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "save.svg")
        if ok:
            btn.setText(f" {T(ok_key)}")
            btn.setIcon(QIcon(get_colored_pixmap(icon_check, 16, "#11111b")))
            btn.setStyleSheet("background-color: #00e676 !important; color: #11111b !important; font-weight: bold;")
        else:
            btn.setText(f" {T('fw360_io_error')}")
            btn.setIcon(QIcon())
            btn.setStyleSheet("background-color: #ff3333 !important; color: #ffffff !important; font-weight: bold;")

        QTimer.singleShot(2000, lambda: (btn.setText(f" {T(reset_key)}"), btn.setIcon(QIcon(get_colored_pixmap(icon_save, 16, "#11111b"))), btn.setStyleSheet("")))

    def apply_to_device(self):
        """Invia le strisce alla scheda come anteprima dal vivo (non permanente)."""
        eng = self._apply_state_to_engine()
        self._flash_button(self.btn_save, True, "fw360_flash_ok", "fw360_save_device")

    def save_to_flash(self):
        """Salva le strisce nella config e chiede al demone di applicarle e renderle
        PERMANENTI (save_to_flash) sulla scheda. L'invio USB lo fa il demone (root)."""
        self._persist_to_config()
        resp = self.main_window.send_daemon_command({"action": "apply_rgb", "save_flash": True})
        ok = bool(resp) and resp.get("status") == "ok"
        self._flash_button(self.btn_save, ok, "fw360_flash_ok", "fw360_save_device")
