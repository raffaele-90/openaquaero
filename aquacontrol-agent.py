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
import sys
import time
import json
import socket
import subprocess

from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel,
                               QPushButton, QFrame)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QObject, Slot, SLOT
from PySide6.QtDBus import QDBusConnection

import config_manager
from config_manager import load_config, CONFIG_FILE
from i18n import T

DAEMON_SOCKET = "/run/aquacontrol.sock"
PENDING_FILE = "/var/lib/aquacontrol/emergency_pending.json"
WARN_SOUND = "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga"


def _reload_global_config():
    """Rilegge il file condiviso e aggiorna il dict globale in-place. Serve perché T()
    legge config_manager.global_config: così l'agent riflette lingua e impostazioni
    cambiate dalla GUI senza riavviarsi. È una LETTURA: l'agent non scrive mai."""
    fresh = load_config()
    config_manager.global_config.clear()
    config_manager.global_config.update(fresh)
    return config_manager.global_config


class DaemonListener(QThread):
    """Ascolta il demone sullo stesso canale della GUI (sync a 1 Hz), che porta anche
    active_alarms. L'agent ASCOLTA e non comanda mai la sessione dal demone: è così che
    resta chiuso il buco di sicurezza della ≤ 4.0."""
    telemetry_ready = Signal(dict)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while self.running:
            try:
                c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                c.connect(DAEMON_SOCKET)
                c.sendall(json.dumps({"action": "sync"}).encode("utf-8"))
                # La telemetria con lo storico può superare i 16 KB: leggiamo fino a EOF.
                chunks = []
                while True:
                    buf = c.recv(65536)
                    if not buf:
                        break
                    chunks.append(buf)
                c.close()
                if chunks:
                    self.telemetry_ready.emit(json.loads(b"".join(chunks).decode("utf-8")))
            except Exception:
                # Demone assente: emettiamo vuoto, l'agent non deve crashare.
                self.telemetry_ready.emit({})
            time.sleep(1)

    def stop(self):
        self.running = False
        self.wait()


class AlarmPopup(QDialog):
    """Popup rosso d'emergenza, modello 5.0: NESSUN conto alla rovescia. Il comando
    personalizzato è già stato lanciato dall'agent all'innesco. Questo pulsante NON
    ferma lo spegnimento (lo decide il demone, l'agent non può fermarlo); al più
    interrompe il comando ancora in esecuzione lato sessione. Etichetta onesta."""
    def __init__(self, messages, on_close=None):
        super().__init__()
        self._on_close = on_close
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(550, 260)

        layout = QVBoxLayout(self)
        bg = QFrame()
        bg.setStyleSheet("background-color: rgba(30,30,46,250); border: 4px solid #ff3333; border-radius: 12px;")
        bl = QVBoxLayout(bg)

        title = QLabel(T("alarm_critical_title"))
        title.setStyleSheet("color:#ff3333; font-size:22px; font-weight:bold;")
        title.setAlignment(Qt.AlignCenter)
        bl.addWidget(title)

        msg = QLabel("\n".join(messages))
        msg.setStyleSheet("color:#cdd6f4; font-size:16px;")
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        bl.addWidget(msg)

        btn = QPushButton(T("alarm_close_verify"))
        btn.setStyleSheet("background-color:#ff3333; color:#ffffff; font-size:18px; font-weight:bold; padding:15px;")
        btn.clicked.connect(self._close_clicked)
        bl.addWidget(btn)

        layout.addWidget(bg)
        self._center()

    def _center(self):
        g = QApplication.primaryScreen().geometry()
        self.move((g.width() - self.width()) // 2, (g.height() - self.height()) // 2)

    def _close_clicked(self):
        if callable(self._on_close):
            self._on_close()
        self.accept()


class Agent(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.cfg = _reload_global_config()
        self._config_mtime = self._mtime()
        self.alarm_active = False
        self.alarm_proc = None
        self.popup = None

        # Autoswitch profilo: 'target' = profilo dell'app attualmente rilevata; 'prev' =
        # profilo attivo PRIMA dello switch, da rimettere alla chiusura dell'app.
        self._auto_target = None
        self._auto_prev = None

        self.listener = DaemonListener()
        self.listener.telemetry_ready.connect(self.on_telemetry)
        self.listener.start()

        # Ripresa dalla sospensione: alla riattivazione chiediamo al demone di riapplicare
        # il profilo Farbwerk (l'agent innesca, il demone root fa l'invio USB). Copre il
        # caso con sessione utente attiva; il caso senza login lo coprirà un hook systemd
        # di sistema in fase di packaging.
        system_bus = QDBusConnection.systemBus()
        system_bus.connect(
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager",
            "PrepareForSleep",
            self,
            SLOT("on_prepare_for_sleep(bool)")
        )

        # Cambio profilo automatico in base ai processi in esecuzione. Vive qui e non nella
        # GUI, così continua a lavorare a interfaccia chiusa. Cadenza come la vecchia
        # versione nella GUI (5 s).
        self._autoswitch_timer = QTimer(self)
        self._autoswitch_timer.timeout.connect(self._check_autoswitch)
        self._autoswitch_timer.start(5000)

        # Diagnostica di riepilogo: dipende dal login, non dalla GUI aperta -> funziona
        # anche se la GUI non viene mai riaperta tra un'emergenza e l'altra.
        QTimer.singleShot(1500, self._check_pending_emergency)

    # ------------------------------------------------------------------ config
    def _mtime(self):
        try:
            return os.path.getmtime(CONFIG_FILE)
        except OSError:
            return None

    def _maybe_reload(self):
        """Ricarica la config solo se il file è cambiato: tiene aggiornati lingua e azioni
        d'allarme (suono/comando) modificate dalla GUI, senza IPC e senza scrivere."""
        m = self._mtime()
        if m != self._config_mtime:
            self._config_mtime = m
            self.cfg = _reload_global_config()

    # --------------------------------------------------------------- telemetria
    def on_telemetry(self, data):
        self._maybe_reload()
        # All'agent serve solo la lista active_alarms: niente OSD, niente widget dei canali.
        alarms = data.get("active_alarms", [])
        if alarms and not self.alarm_active:
            self.alarm_active = True
            self._on_alarm(alarms)
        elif not alarms and self.alarm_active:
            self.alarm_active = False

    # ------------------------------------------------------------------ allarmi
    def _on_alarm(self, alarms):
        act = self.cfg.get("security", {}).get("actions", {})

        if act.get("sound_en"):
            try:
                subprocess.Popen(["paplay", WARN_SOUND])
            except Exception:
                pass

        # Comando personalizzato: subito, in background, non bloccante, senza countdown.
        self.alarm_proc = None
        if act.get("cmd_en") and act.get("cmd_val"):
            try:
                self.alarm_proc = subprocess.Popen(act["cmd_val"], shell=True)
            except Exception:
                self.alarm_proc = None

        if self.popup is None or not self.popup.isVisible():
            self.popup = AlarmPopup(alarms, on_close=self._stop_alarm_command)
            self.popup.show()

    def _stop_alarm_command(self):
        # Pulsante "onesto": ferma al più il comando lato sessione, non lo spegnimento.
        p = self.alarm_proc
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass

    # ------------------------------------------------------------------ ripresa
    def _send_daemon(self, payload):
        """Richiesta one-shot al demone sullo stesso socket della GUI (l'agent invia
        richieste al demone; è il demone che non deve mai comandare la sessione)."""
        try:
            c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            c.settimeout(3.0)
            c.connect(DAEMON_SOCKET)
            c.sendall(json.dumps(payload).encode("utf-8"))
            try:
                c.recv(4096)
            except Exception:
                pass
            c.close()
        except Exception:
            pass

    @Slot(bool)
    def on_prepare_for_sleep(self, sleeping):
        # sleeping=False significa risveglio. Applichiamo solo se l'utente ha attivato la
        # spunta "applica alla ripresa"; l'invio USB effettivo lo fa il demone.
        if not sleeping:
            self.cfg = _reload_global_config()
            if self.cfg.get("fw360_apply_on_resume", False):
                QTimer.singleShot(3000, lambda: self._send_daemon({"action": "apply_rgb"}))

    # ----------------------------------------------------------------- autoswitch
    def _check_autoswitch(self):
        """Se un'app mappata è in esecuzione applica il suo profilo; alla chiusura rimette
        quello attivo PRIMA dello switch. Scatta una volta per apertura: un cambio manuale
        fatto nel frattempo resta finché l'app resta aperta. L'agent non scrive la config:
        fotografa il NOME del profilo di partenza e spinge i canali al demone con
        'apply_channels', esattamente come fa la GUI per il controllo manuale."""
        self._maybe_reload()
        if not self.cfg.get("autoswitch_enabled", False):
            # Disattivato mentre uno switch è attivo: si rientra e si azzera lo stato.
            if self._auto_target is not None:
                self._restore_profile(self._auto_prev)
                self._auto_target = None
                self._auto_prev = None
            return

        detected = None
        for proc_name, prof_name in self.cfg.get("process_profiles", {}).items():
            try:
                if subprocess.run(["pgrep", "-f", proc_name],
                                  capture_output=True).returncode == 0:
                    detected = prof_name
                    break
            except Exception:
                pass

        if detected is not None and detected != self._auto_target:
            # Prima app rilevata: si fotografa il profilo attivo ADESSO (il 'precedente'),
            # da ripristinare alla chiusura. Non si ri-fotografa se già in autoswitch.
            if self._auto_target is None:
                self._auto_prev = self.cfg.get("last_profile", "Default")
            self._apply_profile(detected)
            self._auto_target = detected
        elif detected is None and self._auto_target is not None:
            # Nessuna app mappata più attiva: ritorno al profilo di partenza.
            self._restore_profile(self._auto_prev)
            self._auto_target = None
            self._auto_prev = None

    def _apply_profile(self, prof_name):
        channels = self.cfg.get("profiles", {}).get(prof_name)
        if channels is not None:
            self._send_daemon({"action": "apply_channels", "channels": channels})

    def _restore_profile(self, prof_name):
        # Ripristino esplicito del profilo di partenza: robusto anche se nel frattempo la
        # GUI ha cambiato last_profile. Se quel profilo non esiste più, canali None e il
        # demone torna da solo al last_profile su file.
        channels = self.cfg.get("profiles", {}).get(prof_name) if prof_name else None
        self._send_daemon({"action": "apply_channels", "channels": channels})

    # -------------------------------------------------------------- diagnostica
    def _check_pending_emergency(self):
        if not os.path.exists(PENDING_FILE):
            return
        try:
            with open(PENDING_FILE, "r") as f:
                data = json.load(f)
            os.remove(PENDING_FILE)
        except Exception:
            return

        count = data.get("count", 1)
        reason = data.get("reason", "?")
        ts = data.get("timestamp", "--")

        dlg = QDialog()
        dlg.setWindowTitle(T("alarm_critical_title"))
        dlg.setStyleSheet("QDialog { background-color: #313244; color: #cdd6f4; }")
        dlg.resize(520, 240)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        head = QLabel(
            f"<h3 style='color:#ff3333; margin:0;'>{T('loop_emergency')}</h3>"
            f"<p style='color:#a6adc8; margin:5px 0 0 0;'>{T('popup_fail_safe_msg')}</p>")
        head.setTextFormat(Qt.RichText)
        head.setWordWrap(True)
        lay.addWidget(head)

        details = QLabel(
            f"<p style='font-size:13px; color:#cdd6f4; line-height:1.6; margin:0;'>"
            f"<b>{T('popup_log_title')}</b><br>"
            f"&bull; <b>{count}&times;</b> {T('loop_emergency')}<br>"
            f"&bull; <b>{T('popup_date_time')}</b> {ts}<br>"
            f"&bull; <b>{T('popup_alarm_cause')}</b> "
            f"<span style='color:#f38ba8; font-weight:bold;'>{reason}</span></p>")
        details.setTextFormat(Qt.RichText)
        details.setWordWrap(True)
        lay.addWidget(details)

        btn = QPushButton(T("alarm_close_verify"))
        btn.setStyleSheet("background-color:#00e5ff; color:#11111b; font-weight:bold; border-radius:4px; padding:6px;")
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)

        dlg.exec()


def main():
    # Rete di sicurezza: il servizio utente non va MAI avviato come root (con sudo si
    # aggancerebbe alla sessione di root, inesistente, e non partirebbe come previsto).
    if os.geteuid() == 0:
        print("Errore: aquacontrol-agent è un servizio utente e non va eseguito come root.")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    agent = Agent(app)
    app._agent = agent   # riferimento per evitare la distruzione prematura
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
