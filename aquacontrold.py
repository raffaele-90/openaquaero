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
import threading
import grp
from engine import AquaeroEngine
from config_manager import load_config, CONFIG_FILE
from farbwerk360_engine import Farbwerk360Engine

SOCKET_PATH = "/run/aquacontrol.sock"


class AquaControlDaemon:
    def __init__(self):
        print("[Daemon] Inizializzazione motore hardware Aquaero...")
        self.engine = AquaeroEngine()

        self.running = True

        # Configurazione in RAM + timestamp del file per il ricaricamento automatico.
        self.current_config = load_config()
        try:
            self._config_mtime = os.path.getmtime(CONFIG_FILE)
        except OSError:
            self._config_mtime = None

        # Working set live: con la GUI aperta i parametri dei canali arrivano qui
        # (verbo socket 'apply_channels') e hanno precedenza sul profilo su file.
        # Solo in RAM: al riavvio del demone si torna al profilo salvato nel JSON.
        self.live_channels = None

        # Lock per serializzare le scritture al blocco di configurazione HID
        # dell'Aquaero (report 0x0b: modalità PWM/DC, calibrazione flusso).
        self.hid_lock = threading.Lock()

        # Lock separato per la Farbwerk (USB diverso dall'Aquaero): serializza gli invii
        # di colore così due richieste ravvicinate non si accavallano sul bus.
        self.farbwerk_lock = threading.Lock()

        # Stato allarmi
        self.alarm_trackers = {}
        self.alarm_triggered = False
        self.current_alarm_messages = []

    # ------------------------------------------------------------------
    # CONFIGURAZIONE
    # ------------------------------------------------------------------
    def maybe_reload_config(self):
        """Ricarica la config solo se il file è cambiato (confronto mtime).
        È così che le modifiche fatte dalla GUI arrivano al demone, senza IPC."""
        try:
            mtime = os.path.getmtime(CONFIG_FILE)
        except OSError:
            # File non ancora presente (es. primo boot): manteniamo l'ultima config.
            return
        if mtime != self._config_mtime:
            self._config_mtime = mtime
            self.current_config = load_config()
            print("[Daemon] Configurazione ricaricata (file modificato dalla GUI).")

    # ------------------------------------------------------------------
    # FARBWERK 360 (sola applicazione — a evento, non periodico)
    # ------------------------------------------------------------------
    def apply_farbwerk_from_config(self, save_flash=False):
        """Legge il payload Farbwerk dalla config (lo costruisce la GUI) e lo invia alla
        scheda. A EVENTO: avvio del sistema, ripresa dalla sospensione, richiesta
        'apply_rgb' dalla GUI. Gestione indipendente dalle cadenze Aquaero (1 Hz) e boost.
        Lettura fresca della config: la GUI salva SUBITO prima di chiedere l'invio."""
        cfg = load_config()
        payload = cfg.get("fw360_payload")
        if not payload:
            return False
        with self.farbwerk_lock:
            try:
                return Farbwerk360Engine().apply_payload_hex(payload, save_flash=save_flash)
            except Exception as e:
                print(f"[Farbwerk] Invio fallito: {e}")
                return False

    # ------------------------------------------------------------------
    # SICUREZZA (logica pura, isolata dalla GUI)
    # ------------------------------------------------------------------
    def check_security_alarms(self, temps, rpms, volts, flows, pwm_commands, config, profile_data):
        sec_config = config.get("security", {})
        if not sec_config:
            self.current_alarm_messages = []
            return

        channels_sec = sec_config.get("channels", {})
        flows_sec = sec_config.get("flows", {})
        actions_sec = sec_config.get("actions", {})

        # Il sensore di ogni canale vive nel profilo effettivo, ora passato dal chiamante
        # (working set live se presente, altrimenti il profilo su file).

        alarm_triggered_this_tick = False
        alarm_messages = []
        current_time = time.time()

        # 1. Canali 12V
        for ch_id_str, c_sec in channels_sec.items():
            ch_id = int(ch_id_str)
            allowed_delay = c_sec.get("delay_val", 3)
            current_pwm = pwm_commands.get(ch_id, 0)
            current_pwm_percent = int((current_pwm / 255.0) * 100)

            # Salta se la ventola è spenta logicamente
            if current_pwm_percent == 0:
                self.alarm_trackers.pop(ch_id_str, None)
                continue

            channel_violations = []

            if c_sec.get("rpm_en"):
                current_rpm = rpms.get(ch_id, 0)
                if current_rpm <= c_sec.get("rpm_val", 0):
                    channel_violations.append(f"Canale {ch_id}: RPM {current_rpm} critici.")

            if c_sec.get("temp_en"):
                sensor_id = profile_data.get(ch_id_str, {}).get("sensor")
                if sensor_id:
                    current_temp = temps.get(sensor_id)
                    if current_temp is not None and current_temp >= c_sec.get("temp_val", 999):
                        channel_violations.append(f"Canale {ch_id}: Temp {current_temp}°C critica.")

            if c_sec.get("power_en"):
                if current_pwm_percent <= c_sec.get("power_val", 0):
                    channel_violations.append(f"Canale {ch_id}: Potenza {current_pwm_percent}% insufficiente.")

            if c_sec.get("volt_en"):
                current_volt = volts.get(ch_id, 0.0)
                if current_volt <= c_sec.get("volt_val", 0.0):
                    channel_violations.append(f"Canale {ch_id}: Tensione {current_volt}V critica.")

            if channel_violations:
                if ch_id_str not in self.alarm_trackers:
                    self.alarm_trackers[ch_id_str] = current_time
                if current_time - self.alarm_trackers[ch_id_str] >= allowed_delay:
                    alarm_triggered_this_tick = True
                    alarm_messages.extend(channel_violations)
            else:
                self.alarm_trackers.pop(ch_id_str, None)

        # 2. Sensori di flusso
        for f_id_str, f_sec in flows_sec.items():
            f_id = int(f_id_str)
            allowed_delay = f_sec.get("delay_val", 5)
            current_flow = flows.get(f_id, 0.0)
            flow_violations = []

            if f_sec.get("flow_en"):
                if current_flow <= f_sec.get("flow_val", 0.0):
                    flow_violations.append(f"Flusso {f_id}: {current_flow} L/h insufficiente.")

            tracker_key = f"flow_{f_id_str}"
            if flow_violations:
                if tracker_key not in self.alarm_trackers:
                    self.alarm_trackers[tracker_key] = current_time
                if current_time - self.alarm_trackers[tracker_key] >= allowed_delay:
                    alarm_triggered_this_tick = True
                    alarm_messages.extend(flow_violations)
            else:
                self.alarm_trackers.pop(tracker_key, None)

        self.current_alarm_messages = alarm_messages

        # 3. Innesco allarme globale hardware (ESCLUSIVA DI ROOT)
        #    Nota: qui NON eseguiamo il comando personalizzato dell'utente. Quello
        #    resta nella GUI (sessione utente, nessun privilegio). Root si occupa
        #    solo dell'azione pericolosa e privilegiata: lo spegnimento.
        if alarm_triggered_this_tick and not self.alarm_triggered:
            self.alarm_triggered = True
            print(f"[Emergenza] Allarme innescato! Motivi: {alarm_messages}")

            shutdown_enabled = actions_sec.get("shutdown_en")
            delay_seconds = actions_sec.get("delay_val", 0)

            if shutdown_enabled:
                trigger_reason = alarm_messages[0] if alarm_messages else "Emergenza termica"
                self.engine.trigger_emergency_shutdown(trigger_reason, 99.9, delay_seconds)

        elif not alarm_triggered_this_tick and self.alarm_triggered:
            self.alarm_triggered = False
            print("[Emergenza] Rientrata.")

    # ------------------------------------------------------------------
    # SOCKET (comunicazione con la GUI)
    # ------------------------------------------------------------------
    def handle_client(self, conn):
        try:
            data = conn.recv(16384).decode('utf-8')
            if not data:
                return

            request = json.loads(data)
            action = request.get("action")

            if action == "sync":
                # Telemetria per la GUI. Usiamo sendall: la telemetria (con lo
                # storico) può superare la dimensione di un singolo pacchetto.
                telemetry = self.engine.get_dashboard_telemetry()
                telemetry["active_alarms"] = self.current_alarm_messages
                conn.sendall(json.dumps(telemetry).encode('utf-8'))

            elif action == "set_mode":
                # Cambio modalità PWM/DC del canale: operazione HID sull'Aquaero,
                # quindi la fa il demone (root), non la GUI.
                ch = int(request.get("channel"))
                mode = request.get("mode", "PWM")
                with self.hid_lock:
                    self.engine.set_channel_mode_hid(ch, mode)
                conn.sendall(json.dumps({"status": "ok"}).encode('utf-8'))

            elif action == "set_flow_cal":
                # Calibrazione flusso: scrittura HID sull'Aquaero -> demone.
                fid = int(request.get("flow"))
                imp = int(request.get("impulses"))
                with self.hid_lock:
                    self.engine.set_flow_calibration_hid(fid, imp)
                conn.sendall(json.dumps({"status": "ok"}).encode('utf-8'))

            elif action == "apply_rgb":
                # Applicazione Farbwerk richiesta dalla GUI (anteprima/salva) o dall'agent
                # (ripresa). L'invio USB lo fa il demone; è una richiesta esplicita, quindi
                # sempre eseguita (le spunte avvio/ripresa filtrano a monte, non qui).
                ok = self.apply_farbwerk_from_config(save_flash=bool(request.get("save_flash", False)))
                conn.sendall(json.dumps({"status": "ok" if ok else "error"}).encode('utf-8'))

            elif action == "apply_channels":
                # Push live dei parametri canali dalla GUI. Assegno un riferimento nuovo:
                # il ciclo hardware lo legge senza lock (swap atomico sotto GIL).
                # 'channels' assente/null -> None -> il ciclo torna al profilo su file.
                self.live_channels = request.get("channels")
                conn.sendall(json.dumps({"status": "ok"}).encode('utf-8'))

            else:
                conn.sendall(json.dumps({"status": "unknown_action"}).encode('utf-8'))

        except Exception:
            pass
        finally:
            conn.close()

    def socket_server(self):
        """Crea il socket in /run/ per far parlare GUI e demone."""
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)

        # 660: lettura/scrittura solo per root e per il gruppo 'aquacontrol'.
        os.chmod(SOCKET_PATH, 0o660)
        try:
            group_info = grp.getgrnam("aquacontrol")
            os.chown(SOCKET_PATH, 0, group_info.gr_gid)
        except KeyError:
            print("[Daemon] ERRORE CRITICO: il gruppo 'aquacontrol' non esiste sul sistema.")

        server.listen(5)
        print(f"[Daemon] In ascolto su {SOCKET_PATH}")

        while self.running:
            try:
                conn, _ = server.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # CICLO HARDWARE (1 Hz)
    # ------------------------------------------------------------------
    def hardware_loop(self):
        print("[Daemon] Avvio ciclo hardware autonomo...")
        while self.running:
            # Se al boot l'Aquaero non era ancora pronto, ritenta la mappatura
            # (senza re-inizializzare NVML): appena compare, riprende il controllo.
            if self.engine.path is None:
                self.engine.path = self.engine._find_aquaero_hwmon()
                if self.engine.path:
                    self.engine._map_hardware()
                    print("[Daemon] Aquaero rilevato: mappatura hardware completata.")
                else:
                    time.sleep(1)
                    continue

            # Ricarica la config se la GUI l'ha modificata.
            self.maybe_reload_config()

            # 1. Stato attuale dall'hardware
            telemetry = self.engine.get_dashboard_telemetry()
            temps = telemetry.get('temps', {})

            # 2. Profilo effettivo: il working set live spinto dalla GUI ha precedenza sul
            #    profilo salvato; senza GUI (es. prima del login) si usa 'last_profile'.
            if self.live_channels is not None:
                profile_data = self.live_channels
            else:
                active_profile_name = self.current_config.get("last_profile", "Default")
                profile_data = self.current_config.get("profiles", {}).get(active_profile_name, {})
            hw_config = self.current_config.get("hardware_channels", {})

            # 3. Controlli di sicurezza (fail-safe).
            self.check_security_alarms(
                temps,
                telemetry.get('rpms', {}),
                telemetry.get('volts', {}),
                telemetry.get('flows', {}),
                self.engine.last_pwm_written,
                self.current_config,
                profile_data
            )

            # 4. Calcolo e applicazione per ogni canale (1-4)
            for ch_id in range(1, 5):
                ch_str = str(ch_id)
                ch_state = profile_data.get(ch_str, {})
                ch_hw_conf = hw_config.get(ch_str, {})

                # Canale disabilitato: 0% è VOLUTO.
                is_enabled = ch_hw_conf.get("enabled", True)
                if not is_enabled:
                    self.engine.apply_pwm(ch_id, 0)
                    continue

                mode = ch_state.get("mode", "auto")
                sensor_id = ch_state.get("sensor")
                current_temp = temps.get(sensor_id)

                # Delta virtuale
                if ch_state.get("delta_en") and ch_state.get("delta_cold"):
                    cold_temp = temps.get(ch_state.get("delta_cold"))
                    current_temp = self.engine.calculate_virtual_delta(current_temp, cold_temp)

                logical_percent = 0.0
                have_valid_target = False

                if mode == "fixed":
                    logical_percent = ch_state.get("p_fixed", 100)
                    have_valid_target = True
                elif current_temp is not None:
                    have_valid_target = True
                    if mode == "pid":
                        logical_percent = self.engine.calculate_pwm_pid(
                            ch_id, current_temp, ch_state.get("pid_target", 35.0),
                            ch_state.get("pid_mode", "Normal"),
                            ch_state.get("pid_kp", 0.0), ch_state.get("pid_ki", 0.0), ch_state.get("pid_kd", 0.0)
                        )
                    elif mode == "auto":
                        logical_percent = self.engine.calculate_pwm_auto(
                            current_temp, ch_state.get("t_min", 35), ch_state.get("t_max", 45),
                            ch_state.get("p_min", 0), ch_state.get("p_max", 100), ch_state.get("gamma", 1.0)
                        )
                    elif mode == "manual":
                        logical_percent = self.engine.calculate_pwm_manual(current_temp, ch_state.get("points", []))

                # SICUREZZA: se non c'è una base valida (config assente o sensore
                # non leggibile), NON forziamo 0% -> non tocchiamo il canale, così
                # una pompa non viene mai spenta per una dimenticanza o un sensore
                # mancante. L'Aquaero mantiene il suo stato precedente.
                if not have_valid_target:
                    continue

                # Conversione in byte HW con soglia minima
                min_power = ch_hw_conf.get("min_power", 0)
                pwm_byte, _ = self.engine.apply_hardware_limits(ch_id, logical_percent, min_power)

                # Applica (il boost asincrono <1s è gestito dentro engine.py)
                boost_en = ch_hw_conf.get("boost_en", False)
                boost_time = ch_hw_conf.get("boost_time", 1.0)
                self.engine.apply_pwm(ch_id, pwm_byte, boost_enabled=boost_en, boost_time=boost_time)

            time.sleep(1)

    def start(self):
        threading.Thread(target=self.socket_server, daemon=True).start()
        # Applicazione Farbwerk all'avvio del sistema, se l'utente l'ha richiesta con la
        # relativa spunta. È un evento una tantum, fuori dal ciclo hardware periodico.
        try:
            if load_config().get("fw360_apply_on_start", False):
                self.apply_farbwerk_from_config()
        except Exception:
            pass
        self.hardware_loop()


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Errore: aquacontrold deve essere eseguito come root (sudo).")
        sys.exit(1)

    daemon = AquaControlDaemon()
    try:
        daemon.start()
    except KeyboardInterrupt:
        print("\nArresto demone in corso...")
        daemon.running = False
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
