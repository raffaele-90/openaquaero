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

import sys
import os
import stat
import subprocess
import socket
import json
import time
import threading
from engine import AquaeroEngine
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QSystemTrayIcon, QMenu, QStyle,
                               QListWidget, QListWidgetItem, QStackedWidget,
                               QLabel, QPushButton, QComboBox, QLineEdit, QScrollArea,
                               QGroupBox, QCheckBox, QMessageBox, QFrame, QDialog, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, Slot, SLOT
from PySide6.QtGui import QAction, QIcon, QFont, QColor, QPixmap

# --- Importazioni Modulari ---
from config_manager import global_config, save_config, CONFIG_FILE
from i18n import T
from osd_widget import AquaeroOSD
from ui_tabs import DashboardTabWidget, SecurityTabWidget, SettingsTabWidget, GuideTabWidget, OSDConfigTabWidget, HardwareTabWidget, Farbwerk360TabWidget, get_colored_pixmap
from ui_widgets import ChannelControlWidget, ProcessMappingDialog
from farbwerk360_effects import Farbwerk360EffectsEngine


IPC_SOCKET_PATH = "/tmp/aquacontrol_osd.sock"

def get_dynamic_style(opacity_value, is_imperium=False):
    main_accent = "#FFD700" if is_imperium else "#00e5ff"
    main_accent_hover = "#FDE047" if is_imperium else "#5cf0ff"
    sidebar_sel_bg = "rgba(139, 0, 0, 0.6)" if is_imperium else "rgba(0, 229, 255, 50)"
    sidebar_sel_border = "#FFD700" if is_imperium else "#00e5ff"

    # Sfondi: Grigio scuro (Normale) vs Rosso Porpora Scuro (Imperium)
    bg_main = f"rgba(45, 10, 15, {opacity_value})" if is_imperium else f"rgba(20, 22, 24, {opacity_value})"
    bg_sidebar = f"rgba(25, 5, 10, {min(255, opacity_value + 35)})" if is_imperium else f"rgba(10, 10, 15, {min(255, opacity_value + 35)})"
    bg_solid = "rgba(70, 15, 20, 225)" if is_imperium else "rgba(35, 38, 41, 225)"

    return f"""
    QMainWindow {{ background: transparent; }}

    #CentralWidget {{
        background-color: {bg_main};
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 15);
    }}

    QWidget {{ color: #e0e0e0; font-family: system-ui, sans-serif; }}

    #SidebarContainer {{
        background-color: {bg_sidebar};
        border-right: 1px solid rgba({ '255, 215, 0' if is_imperium else '0, 229, 255' }, 30);
        border-top-left-radius: 12px;
        border-bottom-left-radius: 12px;
    }}

    QListWidget#Sidebar {{ background: transparent; border: none; outline: 0; }}
    QListWidget#Sidebar::item {{ margin: 8px 0px; border-left: 4px solid transparent; padding-left: 15px; }}
    QListWidget#Sidebar::item:selected {{ background-color: {sidebar_sel_bg}; border-left: 4px solid {sidebar_sel_border}; color: #ffffff; }}

    #InfoButton {{ background: transparent; border: none; color: #a6adc8; font-size: 24px; padding: 20px 0px; }}
    #InfoButton:hover {{ color: {main_accent}; }}

    QGroupBox {{ border: 1px solid rgba(255, 255, 255, 20); border-radius: 8px; margin-top: 5px; padding: 10px; background-color: {bg_solid}; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; color: {main_accent}; font-size: 13px; font-weight: bold; }}

    QPushButton#ActionBtn {{ background-color: {main_accent} !important; color: #11111b !important; font-size: 14px; font-weight: bold; border-radius: 6px; padding: 12px; border: none; }}
    QPushButton#ActionBtn:disabled {{ background-color: #313244 !important; color: #585b70 !important; }}

    QPushButton#SecurityBtn {{ background-color: #ff3333 !important; color: #ffffff !important; font-size: 14px; font-weight: bold; border-radius: 6px; padding: 12px; border: none; }}
    QPushButton#SecurityBtn:disabled {{ background-color: #313244 !important; color: #585b70 !important; }}

    QLineEdit, QComboBox {{ background-color: rgba(0, 0, 0, 80); border: 1px solid rgba(255, 255, 255, 20); border-radius: 4px; padding: 5px; color: #ffffff; }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea QWidget {{ background: transparent; }}

    QScrollBar:vertical {{ background-color: rgba(0, 0, 0, 80); width: 8px; margin: 0px; border-radius: 4px; }}
    QScrollBar::handle:vertical {{ background-color: rgba({ '255, 215, 0' if is_imperium else '0, 229, 255' }, 180); min-height: 30px; border-radius: 4px; }}
    QScrollBar::handle:vertical:hover {{ background-color: {main_accent_hover}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

    QScrollBar:horizontal {{ background-color: rgba(0, 0, 0, 80); height: 8px; margin: 0px; border-radius: 4px; }}
    QScrollBar::handle:horizontal {{ background-color: rgba({ '255, 215, 0' if is_imperium else '0, 229, 255' }, 180); min-width: 30px; border-radius: 4px; }}
    QScrollBar::handle:horizontal:hover {{ background-color: {main_accent_hover}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
    """

class IPCServer(QThread):
    toggle_osd_signal = Signal()
    def __init__(self):
        super().__init__()
        self.running = True
        if os.path.exists(IPC_SOCKET_PATH):
            try: os.remove(IPC_SOCKET_PATH)
            except: pass
    def run(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.bind(IPC_SOCKET_PATH)
            s.listen(1)
            os.chmod(IPC_SOCKET_PATH, 0o666)
        except Exception as e:
            print(f"IPC Socket error: {e}")
            return
        while self.running:
            try:
                conn, _ = s.accept()
                data = conn.recv(1024)
                if b"toggle_osd" in data:
                    self.toggle_osd_signal.emit()
                conn.close()
            except: pass
    def stop(self):
        self.running = False
        try:
            dummy = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            dummy.connect(IPC_SOCKET_PATH)
            dummy.close()
        except: pass
        self.wait()

class DaemonClientWorker(QThread):
    telemetry_ready = Signal(dict)

    def __init__(self):
        super().__init__()
        self.running = True
        self.socket_path = "/run/aquacontrol.sock"

    def run(self):
        while self.running:
            try:
                # Si connette al demone
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client.connect(self.socket_path)

                # Prepara la richiesta: chiediamo solo la telemetria
                request = {
                    "action": "sync"
                }

                client.sendall(json.dumps(request).encode('utf-8'))

                # La telemetria con lo storico può superare i 16 KB: leggiamo fino
                # a EOF, altrimenti il JSON arriva troncato e json.loads fallisce.
                chunks = []
                while True:
                    buf = client.recv(65536)
                    if not buf:
                        break
                    chunks.append(buf)

                if chunks:
                    telemetry = json.loads(b"".join(chunks).decode('utf-8'))
                    self.telemetry_ready.emit(telemetry)

                client.close()
            except Exception as e:
                # Se il demone non è attivo, mandiamo dati vuoti per non far crashare la GUI
                self.telemetry_ready.emit({})

            time.sleep(1)

    def stop(self):
        self.running = False
        self.wait()

class AquaControlUI(QMainWindow):

    def send_daemon_command(self, payload):
        """Comando one-shot al demone (modalità PWM/DC, calibrazione flusso)."""
        try:
            c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            c.settimeout(3.0)
            c.connect("/run/aquacontrol.sock")
            c.sendall(json.dumps(payload).encode('utf-8'))
            chunks = []
            while True:
                buf = c.recv(4096)
                if not buf:
                    break
                chunks.append(buf)
            c.close()
            return json.loads(b"".join(chunks).decode('utf-8')) if chunks else {}
        except Exception as e:
            print(f"[GUI] Comando al demone fallito: {e}")
            return {}

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setWindowTitle(T("app_title"))
        self.resize(1000, 950)
        self.updating_combo = False
        self.alarm_triggered = False

        self.autostart_dir = os.path.expanduser("~/.config/autostart")
        self.desktop_file_path = os.path.join(self.autostart_dir, "aquacontrol.desktop")

        self.ipc_server = IPCServer()
        self.ipc_server.toggle_osd_signal.connect(self.toggle_osd_from_hotkey)
        self.ipc_server.start()

        self.osd_window = AquaeroOSD()
        self.osd_window.position_changed.connect(self.save_osd_position)
        if global_config.get("osd_export", False):
            self.osd_window.show()
            QTimer.singleShot(100, self.restore_osd_position)

        self.setup_tray_icon()
        self.init_settings_vars()
        self.engine = AquaeroEngine()
        self.fw360_engine = Farbwerk360EffectsEngine()
        self.setup_ui()

        self.hw_thread = DaemonClientWorker()
        self.hw_thread.telemetry_ready.connect(self.on_telemetry_received)
        self.hw_thread.start()
        self.is_controlling = True

        # Ultimo snapshot canali inviato al demone: spinge il push live solo su modifica.
        self._last_pushed_channels = None
        self.refresh_profile_list()
        self.combo_profiles.currentIndexChanged.connect(self.load_selected_profile)
        self.load_last_profile()

        self.dirty_timer = QTimer(self)
        self.dirty_timer.timeout.connect(self.check_dirty_state)
        self.dirty_timer.start(500)


    def init_settings_vars(self):
        self.chk_autostart = QCheckBox(T("autostart"))
        self.chk_autostart.setStyleSheet("font-size: 13px;")
        self.chk_autostart.setChecked(os.path.exists(self.desktop_file_path))

        self.chk_minimized = QCheckBox(T("start_min"))
        self.chk_minimized.setStyleSheet("font-size: 13px;")
        self.chk_minimized.setChecked(global_config.get("autostart_min", False))
        self.chk_minimized.setEnabled(self.chk_autostart.isChecked())

        self.chk_autostart.toggled.connect(self.on_autostart_toggled)
        self.chk_minimized.toggled.connect(self.toggle_autostart)

        self.chk_autoswitch = QCheckBox(T("autoswitch"))
        self.chk_autoswitch.setStyleSheet("font-size: 13px;")
        self.chk_autoswitch.setChecked(global_config.get("autoswitch_enabled", False))
        self.chk_autoswitch.toggled.connect(lambda v: self._save_simple_config("autoswitch_enabled", v))

        self.btn_autoswitch_settings = QPushButton()
        icon_settings = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "settings.svg")
        self.btn_autoswitch_settings.setIcon(QIcon(get_colored_pixmap(icon_settings, 20, "#cdd6f4")))
        self.btn_autoswitch_settings.setFixedWidth(40)
        self.btn_autoswitch_settings.clicked.connect(self.open_autoswitch_settings)

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)

        is_imperium = global_config.get("lang") == "la"
        if is_imperium:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "imperium-edition.svg")
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(QIcon.fromTheme("aquacontrol", self.style().standardIcon(QStyle.SP_ComputerIcon)))

        self.tray_menu = QMenu()

        self.action_toggle_osd = QAction(T("tray_toggle_osd"), self)
        self.action_toggle_osd.triggered.connect(self.toggle_osd_from_tray)
        self.tray_menu.addAction(self.action_toggle_osd)
        self.tray_menu.addSeparator()

        show_action = QAction(T("tray_show"), self)
        show_action.triggered.connect(self.showNormal)
        self.tray_menu.addAction(show_action)

        self.tray_profiles_menu = QMenu(T("tray_change_profile"), self.tray_menu)
        self.tray_menu.addMenu(self.tray_profiles_menu)
        self.tray_menu.aboutToShow.connect(self.update_tray_profiles)
        self.tray_menu.addSeparator()

        quit_action = QAction(T("tray_quit"), self)
        quit_action.triggered.connect(self.force_quit)
        self.tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_click)

    def setup_ui(self):

        # 1. Widget Centrale (Sfondo trasparente)
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_h_layout = QHBoxLayout(central_widget)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # 2. SIDEBAR CONTAINER (La colonna scura a sinistra)
        sidebar_container = QWidget()
        sidebar_container.setObjectName("SidebarContainer")
        sidebar_container.setFixedWidth(75)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 3. LISTA ICONE (Sidebar)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")

        # LOGICA ESPANSIONE: Diciamo alla lista di occupare tutto lo spazio verticale
        self.sidebar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar.setFrameShape(QFrame.NoFrame)

        # Imposta la dimensione fissa per le icone SVG nella sidebar
        self.sidebar.setIconSize(QSize(35, 35))

        # Percorso assoluto della directory contenente le icone
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(base_dir, "assets", "icons")

        # Lista di tuple: (nome_file_svg, tooltip_tradotto)
        icons = [
            ("panoramic.svg", T("tab_dash")),
            ("curves.svg", T("fan_tab_title")),
            ("hardware.svg", T("tab_hw_channels")),
            ("farbwerk360.svg", T("tab_farbwerk360")),
            ("security.svg", T("sidebar_sec")),
            ("osd.svg", T("sidebar_osd")),
            ("settings.svg", T("tab_settings")),
            ("manual.svg", T("tab_guide"))
        ]

        for icon_file, tooltip in icons:
            item = QListWidgetItem()
            # Carica l'immagine dal file e la imposta come icona dell'elemento
            icon_path = os.path.join(icons_dir, icon_file)
            item.setIcon(QIcon(icon_path))
            item.setToolTip(tooltip)
            self.sidebar.addItem(item)

        sidebar_layout.addWidget(self.sidebar)

        # 4. TASTO INFO
        self.btn_info_sidebar = QPushButton()
        self.btn_info_sidebar.setObjectName("InfoButton")
        self.btn_info_sidebar.setCursor(Qt.PointingHandCursor)
        info_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "info.svg")
        self.btn_info_sidebar.setIcon(QIcon(info_icon_path))
        self.btn_info_sidebar.setIconSize(QSize(35, 35))
        self.btn_info_sidebar.clicked.connect(self.show_about_dialog)
        sidebar_layout.addWidget(self.btn_info_sidebar)

        # 5. CONTENUTI (STACKED WIDGET)
        self.stack = QStackedWidget()

        # Inizializziamo ogni Tab con il suo NOME CORRETTO (self.xxx)
        self.dashboard_tab = DashboardTabWidget()
        self.stack.addWidget(self.dashboard_tab)

        self.fan_page = QWidget()
        fan_layout = QVBoxLayout(self.fan_page)
        fan_layout.setContentsMargins(15, 15, 15, 15)
        self.build_fan_control_ui(fan_layout)
        self.stack.addWidget(self.fan_page)

        self.hw_channels_tab = HardwareTabWidget(self)
        self.stack.addWidget(self.hw_channels_tab)

        self.farbwerk360_tab = Farbwerk360TabWidget(self)
        self.stack.addWidget(self.farbwerk360_tab)

        self.security_tab = SecurityTabWidget()
        self.stack.addWidget(self.security_tab)

        self.osd_tab = OSDConfigTabWidget(self)
        self.stack.addWidget(self.osd_tab)

        self.settings_tab = SettingsTabWidget(self)
        self.stack.addWidget(self.settings_tab)

        self.guide_tab = GuideTabWidget()
        self.stack.addWidget(self.guide_tab)

        # 6. ASSEMBLAGGIO FINALE
        main_h_layout.addWidget(sidebar_container)
        main_h_layout.addWidget(self.stack)

        # Connessioni logiche
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        # 7. APPLICAZIONE STILE E OPACITÀ (Corretto ai toni Base / Skin Imperiale)
        initial_opacity = global_config.get("window_opacity", 180)
        is_imperium = global_config.get("lang") == "la"
        self.setStyleSheet(get_dynamic_style(initial_opacity, is_imperium))

    def build_fan_control_ui(self, layout):
        header_layout = QHBoxLayout()
        lbl_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "curves.svg")
        lbl_icon.setPixmap(QIcon(icon_path).pixmap(24, 24))
        header_layout.addWidget(lbl_icon)

        lbl_main_title = QLabel(T("fan_tab_title"))
        is_imperium = global_config.get("lang") == "la"
        lbl_main_title.setStyleSheet(f"font-size: 24px; color: {'#FFD700' if is_imperium else '#00e5ff'}; font-weight: bold;")
        header_layout.addWidget(lbl_main_title)
        header_layout.addStretch()

        layout.addLayout(header_layout)
        layout.addSpacing(15)

        lbl_prof_group = QLabel(T("profile_group"))
        lbl_prof_group.setStyleSheet("font-size: 16px; color: #cdd6f4; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(lbl_prof_group)

        top_bar = QHBoxLayout()
        profile_group = QGroupBox()
        profile_layout = QHBoxLayout()
        self.combo_profiles = QComboBox()

        self.btn_save_current = QPushButton()
        icon_save = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "save.svg")
        self.btn_save_current.setIcon(QIcon(get_colored_pixmap(icon_save, 20, "#cdd6f4")))
        self.btn_save_current.setFixedWidth(40)
        self.btn_save_current.clicked.connect(self.save_current_profile)

        self.btn_delete_profile = QPushButton()
        icon_del = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "close.svg")
        self.btn_delete_profile.setIcon(QIcon(get_colored_pixmap(icon_del, 20, "#cdd6f4")))
        self.btn_delete_profile.setFixedWidth(40)
        self.btn_delete_profile.clicked.connect(self.delete_current_profile)

        self.txt_new_profile = QLineEdit()
        self.txt_new_profile.setPlaceholderText(T("placeholder"))
        self.btn_save_profile = QPushButton(T("save_btn"))
        is_imperium = global_config.get("lang") == "la"
        self.btn_save_profile.setStyleSheet(f"background-color: {'#FFD700' if is_imperium else '#00e5ff'}; color: #11111b;")
        self.btn_save_profile.clicked.connect(self.save_new_profile)

        profile_layout.addWidget(self.combo_profiles)
        profile_layout.addWidget(self.btn_save_current)
        profile_layout.addWidget(self.btn_delete_profile)
        profile_layout.addWidget(QLabel("   |   "))
        profile_layout.addWidget(self.txt_new_profile)
        profile_layout.addWidget(self.btn_save_profile)
        profile_group.setLayout(profile_layout)
        top_bar.addWidget(profile_group)
        layout.addLayout(top_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        self.channels_layout = QVBoxLayout(container)
        layout.addWidget(scroll)

        self.channels = []
        for i in range(1, 5):
            cw = ChannelControlWidget(i, engine=self.engine)
            self.channels_layout.addWidget(cw)
            self.channels.append(cw)

    def on_telemetry_received(self, data):
        # Le chiavi per-canale sono INTERE nel demone, ma il JSON le rende STRINGHE.
        # Le riconvertiamo una volta sola, così dashboard, canali e OSD le trovano.
        for _k in ("rpms", "volts", "pwm_loads", "flows"):
            if isinstance(data.get(_k), dict):
                data[_k] = {int(_kk): _vv for _kk, _vv in data[_k].items()}

        self.dashboard_tab.update_telemetry(data)

        # Dati condivisi tra i widget dei canali e l'OSD.
        temps = data.get('temps', {})
        rpms = data.get('rpms', {})
        volts = data.get('volts', {})
        pwm_loads = data.get('pwm_loads', {})
        osd_data = []

        osd_conf = global_config.get("osd_config", {})

        if getattr(self, 'chk_osd', None) and self.chk_osd.isChecked():
            # Aggiunta Flussi all'OSD
            for f_id in range(1, 3):
                comp_id = f"flow_{f_id}"
                conf_f = osd_conf.get(comp_id, {"enabled": False, "custom_name": ""})
                if conf_f.get("enabled"):
                    flow_val = data.get('flows', {}).get(f_id, 0.0)
                    # Utilizzo della traduzione invece di forzare "Sensore X"
                    fallback_name = T('hw_flow_sensor_num').format(i=f_id)
                    flow_name = conf_f.get("custom_name") or fallback_name
                    osd_data.append({'name': flow_name, 'flow': flow_val})

        hw_config = global_config.get("hardware_channels", {})

        for ch in self.channels:
            ch_conf = hw_config.get(str(ch.channel_id), {})
            is_enabled = ch_conf.get("enabled", True)

            ch.setVisible(is_enabled)

            if not is_enabled:
                continue

            # Passiamo i carichi PWM già calcolati
            ch.process_telemetry(temps, rpms, volts, pwm_loads)

            if getattr(self, 'chk_osd', None) and self.chk_osd.isChecked():
                ch_id = f"ch_{ch.channel_id}"
                ch_conf = osd_conf.get(ch_id, {"enabled": True, "custom_name": ""})
                if ch_conf.get("enabled", True):
                    sensor_id = ch.combo_sensors.currentData()
                    t = temps.get(sensor_id) if sensor_id else 0.0
                    if t is None: t = 0.0
                    r = rpms.get(ch.channel_id, 0)
                    v = volts.get(ch.channel_id, 0.0)
                    p = pwm_loads.get(ch.channel_id, 0) # <-- OSD LEGGE IL DATO DEL DEMONE
                    ch_name = ch_conf.get("custom_name") or ch.edit_name.text()
                    osd_data.append({'name': ch_name, 'temp': t, 'rpm': r, 'volt': v, 'pwm': p})

        if getattr(self, 'chk_osd', None) and self.chk_osd.isChecked() and osd_data:
            self.osd_window.update_data(osd_data)
            self.restore_osd_position()

        # Allarmi dal demone: la GUI POSSIEDE l'OSD, quindi qui fa SOLO l'OSD-rosso.
        # Popup rosso, suono e comando personalizzato sono passati all'agent, così la
        # reazione vale anche a GUI chiusa e non viene eseguita due volte (GUI + agent).
        active_alarms = data.get("active_alarms", [])

        if active_alarms and not self.alarm_triggered:
            self.alarm_triggered = True
            sec_config = global_config.get("security", {})
            if sec_config.get("actions", {}).get("osd_en") and self.osd_window.isVisible():
                self.osd_window.bg_widget.setStyleSheet("background-color: rgba(200, 0, 0, 235); border-radius: 12px; border: 3px solid #ffffff;")

        elif not active_alarms and self.alarm_triggered:
            self.alarm_triggered = False
            if self.osd_window.isVisible():
                self.osd_window.apply_scaling()

    def check_dirty_state(self):
        p_name = self.combo_profiles.currentText()
        if not p_name or p_name not in global_config["profiles"]: return
        if p_name == "Default":
            self.btn_delete_profile.setEnabled(False)
            self.btn_delete_profile.setStyleSheet("background-color: #313244; color: #585b70; font-size: 16px; padding: 5px;")
        else:
            self.btn_delete_profile.setEnabled(True)
            self.btn_delete_profile.setStyleSheet("background-color: #313244; color: #ff3333; font-size: 16px; font-weight: bold; padding: 5px;")

        saved_profile_data = global_config["profiles"][p_name]
        current_profile_data = {str(ch.channel_id): ch.get_state() for ch in self.channels}
        current_safe = json.loads(json.dumps(current_profile_data))

        # Push live: se i canali sono cambiati dall'ultimo invio, li spingiamo subito al
        # demone (senza salvare). Lui li tiene in RAM e li applica nel loop 1 Hz.
        if current_safe != self._last_pushed_channels:
            self._last_pushed_channels = current_safe
            self.send_daemon_command({"action": "apply_channels", "channels": current_safe})

        is_dirty = (saved_profile_data != current_safe)

        self.btn_save_current.setEnabled(is_dirty)
        if is_dirty: self.btn_save_current.setStyleSheet("background-color: #00e5ff; color: #11111b; font-size: 16px; padding: 5px;")
        else: self.btn_save_current.setStyleSheet("background-color: #313244; color: #6c7086; font-size: 16px; padding: 5px;")

    def save_current_profile(self):
        p_name = self.combo_profiles.currentText()
        if not p_name: return
        global_config["profiles"][p_name] = {str(ch.channel_id): ch.get_state() for ch in self.channels}
        save_config(global_config)

        self.btn_save_current.setStyleSheet("background-color: #00e676; color: #11111b; font-size: 16px; padding: 5px;")

        QTimer.singleShot(1000, self.check_dirty_state)

    def delete_current_profile(self):
        p_name = self.combo_profiles.currentText()
        if p_name == "Default": return
        reply = QMessageBox.question(self, T("dialog_del_title"), T("dialog_del_msg").format(p=p_name), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del global_config["profiles"][p_name]
            global_config["last_profile"] = "Default"
            save_config(global_config)
            self.refresh_profile_list()
            self.updating_combo = True
            self.combo_profiles.setCurrentText("Default")
            self.updating_combo = False
            self.load_selected_profile()

    def refresh_profile_list(self):
        self.updating_combo = True
        self.combo_profiles.clear()
        self.combo_profiles.addItems(global_config["profiles"].keys())
        self.updating_combo = False

    def save_new_profile(self):
        p_name = self.txt_new_profile.text().strip()
        if not p_name: return
        if p_name == "Default":
            QMessageBox.warning(self, T("dialog_warn_title"), T("dialog_warn_default"))
            return
        global_config["profiles"][p_name] = {str(ch.channel_id): ch.get_state() for ch in self.channels}
        global_config["last_profile"] = p_name
        save_config(global_config)
        self.refresh_profile_list()
        self.updating_combo = True
        self.combo_profiles.setCurrentText(p_name)
        self.updating_combo = False
        self.txt_new_profile.clear()
        self.check_dirty_state()

    def load_selected_profile(self, index=None):
        if self.updating_combo: return
        p_name = self.combo_profiles.currentText()
        if p_name in global_config["profiles"]:
            profile_data = global_config["profiles"][p_name]
            for ch in self.channels:
                ch_data = profile_data.get(str(ch.channel_id))
                if ch_data: ch.set_state(ch_data)
            # Salviamo solo se il profilo attivo cambia davvero: evita una scrittura
            # inutile a ogni avvio (che farebbe anche ricaricare la config al demone).
            if global_config.get("last_profile") != p_name:
                global_config["last_profile"] = p_name
                save_config(global_config)
            self.check_dirty_state()

    def load_last_profile(self):
        last_p = global_config.get("last_profile")
        if last_p and last_p in global_config["profiles"]:
            self.updating_combo = True
            self.combo_profiles.setCurrentText(last_p)
            self.updating_combo = False
            self.load_selected_profile()

    def change_osd_scale(self, val):
        self._save_simple_config("osd_scale", val)
        self.osd_window.set_scale(val)
        QTimer.singleShot(50, self.restore_osd_position)

    def show_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(T("info_btn"))
        dialog.setStyleSheet("QDialog { background-color: #232629; color: #cdd6f4; }")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        lbl_icon = QLabel()

        is_imperium = global_config.get("lang") == "la"

        if is_imperium:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "imperium-edition.svg")
            pixmap = QIcon(icon_path).pixmap(120, 120) # Gigante e gloriosa!
        else:
            system_icon = "/usr/share/icons/hicolor/512x512/apps/aquacontrol.png"
            local_icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aquacontrol.png")

            if os.path.exists(system_icon):
                pixmap = QPixmap(system_icon)
            elif os.path.exists(local_icon):
                pixmap = QPixmap(local_icon)
            else:
                pixmap = QIcon.fromTheme("aquacontrol").pixmap(75, 75)

        if not pixmap.isNull():
            lbl_icon.setPixmap(pixmap.scaled(120 if is_imperium else 75, 120 if is_imperium else 75, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        lbl_title = QLabel()
        lbl_title.setTextFormat(Qt.RichText)
        lbl_title.setText(T("info_dialog_header"))

        header_layout.addWidget(lbl_icon)
        header_layout.addSpacing(15)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("border: 1px solid #45475a;")
        layout.addWidget(line)

        # Creiamo un layout orizzontale per affiancare l'icona al testo
        warning_layout = QHBoxLayout()

        # 1. L'icona vettoriale ricolorata
        lbl_warn_icon = QLabel()
        icon_warn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "warning.svg")
        lbl_warn_icon.setPixmap(get_colored_pixmap(icon_warn, 24, "#ffc107"))
        lbl_warn_icon.setAlignment(Qt.AlignTop)

        # 2. Il testo
        lbl_warning = QLabel()
        lbl_warning.setTextFormat(Qt.RichText)
        lbl_warning.setWordWrap(True)
        lbl_warning.setText(T("info_dialog_warning"))

        warning_layout.addWidget(lbl_warn_icon)
        warning_layout.addSpacing(5)
        warning_layout.addWidget(lbl_warning)
        warning_layout.addStretch()

        # Aggiungiamo il layout orizzontale a quello principale
        layout.addLayout(warning_layout)

        btn_layout = QHBoxLayout()

        is_imperium = global_config.get("lang") == "la"
        txt_ok = " Fiat!" if is_imperium else " OK"
        colore_ok = "#FFD700" if is_imperium else "#00e5ff"

        btn_ok = QPushButton(txt_ok)
        icon_check = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "check.svg")
        btn_ok.setIcon(QIcon(get_colored_pixmap(icon_check, 16, "#11111b")))
        btn_ok.setFixedWidth(100)
        btn_ok.setStyleSheet(f"background-color: {colore_ok}; color: #11111b; font-weight: bold; border-radius: 4px; padding: 6px;")
        btn_ok.clicked.connect(dialog.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        dialog.exec()

    def change_language(self, lang):
        current_saved_lang = global_config.get("lang", "en")

        if current_saved_lang != lang:

            if lang == "la":
                msg = QMessageBox(self)
                msg.setWindowTitle("Decretum Imperiale")

                msg.setText("The high patricians of the academic ivory tower deem anyone lacking their illustrious scrolls and titles entirely unworthy of the sacred art of coding.\n\nThe humble architect of this software, conversely, decrees that this program shall only serve those who understand the tongue of the greatest Empire.\n\nAre you a citizen of Rome, or a mere barbarian?")

                msg.setStyleSheet("QMessageBox { background-color: #1e1e2e; color: #cdd6f4; font-size: 14px; }")

                btn_ave = msg.addButton("Ave Caesar", QMessageBox.AcceptRole)
                btn_ave.setStyleSheet("background-color: #FFD700; color: #8B0000; font-weight: bold; padding: 6px; border-radius: 4px;")

                btn_pleb = msg.addButton("I am a barbarian", QMessageBox.RejectRole)
                btn_pleb.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 6px; border-radius: 4px;")

                msg.exec()

                if msg.clickedButton() == btn_pleb:

                    QMessageBox.warning(self, "Repulsus!", "I knew you were just a barbarian academic, unworthy of Rome.")

                    # 2. Ripristino visivo forzato della combobox alla lingua precedente
                    self.settings_tab.combo_lang.blockSignals(True)
                    self.settings_tab.combo_lang.setCurrentText(current_saved_lang)
                    self.settings_tab.combo_lang.blockSignals(False)
                    return

            global_config["lang"] = lang
            save_config(global_config)

            prompt_text = T("lang_prompt") if lang != "la" else "Lingua mutata est. Visne iterum incipere?"
            reply = QMessageBox.question(self, T("info_btn"), prompt_text, QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.force_quit_and_restart()
            else:
                QMessageBox.information(self, "Language", T("lang_restart"))

    def force_quit_and_restart(self):
        self.ipc_server.stop()
        self.hw_thread.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def force_quit(self):
        self.is_quitting = True
        self.ipc_server.stop()
        self.hw_thread.stop()
        QApplication.quit()

    def on_autostart_toggled(self, checked):
        self.chk_minimized.setEnabled(checked)
        self.toggle_autostart()

    def toggle_autostart(self, *args):
        enabled = self.chk_autostart.isChecked()
        minimized = self.chk_minimized.isChecked()
        global_config["autostart_min"] = minimized
        save_config(global_config)
        if enabled:
            os.makedirs(self.autostart_dir, exist_ok=True)
            exec_cmd = "/usr/bin/aquacontrol --minimized" if minimized else "/usr/bin/aquacontrol"
            with open(self.desktop_file_path, "w") as f:
                f.write(f"[Desktop Entry]\nType=Application\nExec={exec_cmd}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\nName=AquaControl\nComment=Suite di controllo per Aquaero 6 LT\nCategories=System;HardwareSettings;\n")
            os.chmod(self.desktop_file_path, os.stat(self.desktop_file_path).st_mode | stat.S_IEXEC)
        elif os.path.exists(self.desktop_file_path):
            os.remove(self.desktop_file_path)

    def _save_simple_config(self, key, value):
        global_config[key] = value
        save_config(global_config)

    def open_autoswitch_settings(self):
        ProcessMappingDialog(self).exec()

    def update_tray_profiles(self):
        self.tray_profiles_menu.clear()
        for p_name in global_config.get("profiles", {}).keys():
            action = QAction(p_name, self)
            action.triggered.connect(lambda checked, p=p_name: self.load_profile_by_name(p))
            self.tray_profiles_menu.addAction(action)

    def load_profile_by_name(self, p_name):
        self.updating_combo = True
        index = self.combo_profiles.findText(p_name)
        if index >= 0:
            self.combo_profiles.setCurrentIndex(index)
            self.updating_combo = False
            self.load_selected_profile()
            self.tray_icon.showMessage("AquaControl", T("tray_prof_activated").format(p=p_name), QSystemTrayIcon.Information, 1500)
        else: self.updating_combo = False

    def toggle_osd_from_tray(self):
        self.chk_osd.setChecked(not self.chk_osd.isChecked())

    def toggle_osd(self, checked):
        self._save_simple_config("osd_export", checked)
        if checked:
            self.osd_window.show()
            self.restore_osd_position()
        else: self.osd_window.hide()

    def toggle_osd_from_hotkey(self):
        new_state = not global_config.get("osd_export", False)
        global_config["osd_export"] = new_state
        save_config(global_config)
        if hasattr(self, 'chk_osd'):
            self.chk_osd.blockSignals(True)
            self.chk_osd.setChecked(new_state)
            self.chk_osd.blockSignals(False)
        if new_state:
            self.osd_window.show()
            self.restore_osd_position()
        else: self.osd_window.hide()

    def save_osd_position(self, x, y):
        global_config.setdefault("osd_config", {})["pos_x"] = x
        global_config["osd_config"]["pos_y"] = y
        save_config(global_config)

    def restore_osd_position(self):
        pos_x = global_config.get("osd_config", {}).get("pos_x")
        pos_y = global_config.get("osd_config", {}).get("pos_y")
        screen = QApplication.primaryScreen().geometry()
        if pos_x is not None and pos_y is not None and 0 <= pos_x < screen.width() and 0 <= pos_y < screen.height():
            self.osd_window.move(pos_x, pos_y)
        else: self.osd_window.move(screen.width() - self.osd_window.width() - 20, 20)

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden(): self.showNormal()
            else: self.hide()

    def closeEvent(self, event):
        if getattr(self, 'is_quitting', False):
            event.accept()
            return

        if global_config.get("close_to_tray", True):
            event.ignore()
            self.hide()
        else:
            self.force_quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    is_imperium = global_config.get("lang") == "la"
    icon_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "imperium-edition.svg") if is_imperium else "aquacontrol.png"

    app.setWindowIcon(QIcon(icon_file))
    app.setDesktopFileName("aquacontrol")

    initial_opacity = global_config.get("window_opacity", 180)
    app.setStyleSheet(get_dynamic_style(initial_opacity, is_imperium))

    win = AquaControlUI()
    win.setWindowIcon(QIcon(icon_file))

    if "--minimized" not in sys.argv:
        win.show()
    sys.exit(app.exec())
