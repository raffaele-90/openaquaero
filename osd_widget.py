from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QProgressBar, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class AquaeroOSD(QWidget):
    def __init__(self):
        super().__init__()
        self.scale = 1.0
        self.max_rows = 8  # Default: crea una nuova colonna dopo 8 righe
        self.bg_opacity = 220
        self.color_names = "#cdd6f4"
        self.color_values = "#00e5ff"
        self.color_badges = "#00e5ff"
        self.custom_font = None

        # BUGFIX WAYLAND: Sostituiamo Qt.ToolTip con Qt.Tool.
        # ToolTip creava una dipendenza logica (xdg_popup) con la finestra principale,
        # facendola muovere in tandem. Qt.Tool crea una finestra overlay indipendente
        # ma la mantiene invisibile dalla taskbar e dall'Alt+Tab.
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint |
                            Qt.Tool | Qt.WindowTransparentForInput | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Layout Principale a Griglia (permette ancoraggi perfetti in 2D su 9 punti)
        self.layout = QGridLayout(self)

        self.bg_widget = QFrame(self)
        self.bg_layout = QVBoxLayout(self.bg_widget)
        self.layout.addWidget(self.bg_widget)

        # --- Intestazione OSD ---
        self.header_layout = QHBoxLayout()
        self.icon_lbl = QLabel("📊")
        self.title_lbl = QLabel("OPENAQUAERO OSD")
        self.header_layout.addWidget(self.icon_lbl)
        self.header_layout.addWidget(self.title_lbl)
        self.header_layout.addStretch()
        self.bg_layout.addLayout(self.header_layout)

        self.header_line = QFrame()
        self.header_line.setFrameShape(QFrame.HLine)
        self.bg_layout.addWidget(self.header_line)
        # -------------------------------------

        # Il contenitore per la griglia multi-colonna
        self.grid_layout = QGridLayout()
        self.bg_layout.addLayout(self.grid_layout)

        self.row_widgets = []
        self.apply_scaling()

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

        self._force_rebuild = True # Flag per forzare il ricalcolo al prossimo aggiornamento
        self.apply_scaling()

    def apply_scaling(self):
        s = self.scale

        if self.custom_font:
            self.title_lbl.setFont(self.custom_font)

        self.layout.setContentsMargins(int(10*s), int(10*s), int(10*s), int(10*s))

        self.bg_widget.setStyleSheet(
            f"background-color: rgba(17, 17, 27, {self.bg_opacity}); "
            f"border-radius: {int(8*s)}px; "
            f"border: {max(1, int(1*s))}px solid rgba(255, 255, 255, 30);"
        )
        self.bg_layout.setContentsMargins(int(15*s), int(12*s), int(15*s), int(12*s))
        self.bg_layout.setSpacing(int(8*s))

        self.icon_lbl.setStyleSheet(f"font-size: {int(14*s)}px; background: transparent; border: none;")
        self.title_lbl.setStyleSheet(
            f"color: {self.color_badges}; font-weight: 900; "
            f"font-size: {int(11*s)}px; letter-spacing: {int(1*s)}px; "
            f"background: transparent; border: none;"
        )
        self.header_line.setStyleSheet(
            f"background-color: rgba(255, 255, 255, 20); "
            f"border: none; max-height: {max(1, int(1*s))}px;"
        )

        self.grid_layout.setSpacing(int(6*s))

    def update_data(self, hardware_data):
        s = self.scale

        if not hardware_data:
            for w in self.row_widgets:
                self.grid_layout.removeWidget(w)
                w.deleteLater()
            self.row_widgets.clear()
            if hasattr(self, 'sensor_ui'): self.sensor_ui.clear()
            return

        # 1. RICOSTRUZIONE TOTALE (Solo se cambi sensori o modifichi l'estetica)
        if not hasattr(self, 'sensor_ui') or len(self.sensor_ui) != len(hardware_data) or getattr(self, '_force_rebuild', False):
            self._force_rebuild = False
            for w in self.row_widgets:
                self.grid_layout.removeWidget(w)
                w.deleteLater()
            self.row_widgets.clear()
            self.sensor_ui = []

            for i, item in enumerate(hardware_data):
                row = i % self.max_rows
                col = i // self.max_rows

                row_container = QWidget()
                row_container.setStyleSheet("background: transparent; border: none;")
                row_layout = QHBoxLayout(row_container)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(int(10*s))

                lbl_badge = QLabel()
                lbl_badge.setAlignment(Qt.AlignCenter)
                lbl_badge.setFixedWidth(int(38*s))
                if self.custom_font: lbl_badge.setFont(self.custom_font)
                lbl_badge.setStyleSheet(f"background-color: {self.color_badges}; color: #11111b; font-weight: 900; font-size: {int(10*s)}px; border-radius: {int(3*s)}px; padding: {int(2*s)}px;")
                row_layout.addWidget(lbl_badge)

                lbl_name = QLabel()
                lbl_name.setFixedWidth(int(130*s))
                if self.custom_font: lbl_name.setFont(self.custom_font)
                lbl_name.setStyleSheet(f"color: {self.color_names}; font-weight: 700; font-size: {int(12*s)}px;")
                row_layout.addWidget(lbl_name)

                lbl_val = QLabel()
                lbl_val.setFixedWidth(int(65*s))
                lbl_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                row_layout.addWidget(lbl_val)

                lbl_rpm = QLabel()
                lbl_rpm.setFixedWidth(int(75*s))
                lbl_rpm.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                row_layout.addWidget(lbl_rpm)

                prog_bar = QProgressBar()
                prog_bar.setRange(0, 100)
                prog_bar.setTextVisible(True)
                prog_bar.setFormat("%p%")
                prog_bar.setFixedSize(int(80*s), int(16*s))
                prog_bar.setStyleSheet(f"QProgressBar {{ border: 1px solid #313244; border-radius: {int(3*s)}px; background-color: #181825; text-align: center; color: #cdd6f4; font-weight: 800; font-size: {int(10*s)}px; font-family: monospace; }} QProgressBar::chunk {{ background-color: {self.color_badges}; border-radius: {int(2*s)}px; }}")

                spacer = QWidget()
                spacer.setFixedSize(int(80*s), int(16*s))

                row_layout.addWidget(prog_bar)
                row_layout.addWidget(spacer)

                self.grid_layout.addWidget(row_container, row, col)
                self.row_widgets.append(row_container)

                self.sensor_ui.append({
                    'badge': lbl_badge,
                    'name': lbl_name,
                    'val': lbl_val,
                    'rpm': lbl_rpm,
                    'prog': prog_bar,
                    'spacer': spacer
                })
            self.adjustSize()

        # 2. AGGIORNAMENTO IN-PLACE (Fast-Path: Risolve definitivamente il flickering)
        for i, item in enumerate(hardware_data):
            ui = self.sensor_ui[i]

            name_text = item.get('name', '').upper()
            display_name = name_text.replace(" VOLTS", "")
            rpm = item.get('rpm')
            pwm = item.get('pwm')
            temp = item.get('temp')

            if "VOLT" in name_text: badge_txt = "VLT"
            elif rpm is not None: badge_txt = "FAN"
            elif pwm is not None: badge_txt = "PWR"
            elif temp is not None: badge_txt = "TMP"
            else: badge_txt = "SYS"

            ui['badge'].setText(badge_txt)
            ui['name'].setText(display_name)

            if temp is not None:
                unit = "V" if badge_txt == "VLT" else "°C"
                ui['val'].setText(f"{temp:.1f} {unit}")
                ui['val'].setStyleSheet(f"color: {self.color_values}; font-family: monospace; font-weight: 800; font-size: {int(13*s)}px;")
            else:
                ui['val'].setText("--")
                ui['val'].setStyleSheet(f"color: #45475a;")

            if rpm is not None:
                ui['rpm'].setText(f"{rpm} RPM")
                ui['rpm'].setStyleSheet(f"color: #94e2d5; font-family: monospace; font-weight: 800; font-size: {int(13*s)}px;")
            else:
                ui['rpm'].setText("")

            if pwm is not None:
                ui['prog'].show()
                ui['spacer'].hide()
                ui['prog'].setValue(int(pwm))
            else:
                ui['prog'].hide()
                ui['spacer'].show()
