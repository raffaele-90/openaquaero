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

import threading
import time
import subprocess
import datetime
import re
import glob
import os
import json
from collections import deque

try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False

class AquaeroEngine:
    """
    Livello di astrazione hardware fondamentale per AquaControl.
    Gestisce la mappatura dei dispositivi, la scansione generica hwmon di Linux, i calcoli PWM,
    i sensori virtuali (Delta T), la logica PID e la mappatura hardware (potenza minima/Boost).
    """
    def __init__(self):
        self.path = self._find_aquaero_hwmon()
        self.pwm_channels = {}
        self.fan_channels = {}
        self.sensors = {}

        self.last_pwm_written = {}
        self.active_boosts = set()

        self.sys_sensors_meta = {}
        self.sys_sensors_paths = {}

        self.nvml_initialized = False

        # Memoria di stato per il controllore PID {channel_id: {'integral': 0.0, 'prev_error': 0.0, 'last_time': 0.0}}
        self.pid_states = {}

        # Buffer circolare per memorizzare gli ultimi 60 campionamenti (utile per Sparklines)
        self.history = {}

        # Configurazione dinamica dei sensori virtuali (es. Delta T)
        self.virtual_sensors_config = {}

        self._init_system_sensors()

        if not self.path:
            print("ERROR: No Aquaero device found in sysfs.")
            return

        self._map_hardware()

    def _init_system_sensors(self):
        """Scansiona e memorizza nella cache i sensori di sistema disponibili tramite hwmon e NVML."""
        # 1. Scansione HWMON standard di Linux
        for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
            try:
                with open(os.path.join(hwmon, "name"), "r") as f:
                    hw_name = f.read().strip().upper()
            except Exception:
                continue

            if "AQUAERO" in hw_name:
                continue

            hwmon_id = os.path.basename(hwmon)

            # Sensori di temperatura
            for t_input in sorted(glob.glob(os.path.join(hwmon, "temp*_input"))):
                base_name = os.path.basename(t_input).split('_')[0]
                label_path = os.path.join(hwmon, f"{base_name}_label")

                sensor_label = hw_name
                if os.path.exists(label_path):
                    try:
                        with open(label_path, "r") as f:
                            lbl_read = f.read().strip()
                            if lbl_read:
                                sensor_label += f" ({lbl_read})"
                    except Exception: pass
                else:
                    sensor_label += f" ({base_name})"

                s_id = f"sys_{hwmon_id}_{base_name}"
                self.sys_sensors_meta[s_id] = {'label': sensor_label, 'type': 'temp'}
                self.sys_sensors_paths[s_id] = t_input

            # Sensori di voltaggio
            for in_input in sorted(glob.glob(os.path.join(hwmon, "in*_input"))):
                base_name = os.path.basename(in_input).split('_')[0]
                label_path = os.path.join(hwmon, f"{base_name}_label")

                sensor_label = hw_name
                if os.path.exists(label_path):
                    try:
                        with open(label_path, "r") as f:
                            lbl_read = f.read().strip()
                            if lbl_read:
                                sensor_label += f" ({lbl_read})"
                    except Exception: pass
                else:
                    sensor_label += f" ({base_name})"

                s_id = f"sys_{hwmon_id}_{base_name}"
                self.sys_sensors_meta[s_id] = {'label': f"{sensor_label} Volts", 'type': 'volt'}
                self.sys_sensors_paths[s_id] = in_input

            # Carico GPU (sysfs generico)
            device_busy_path = os.path.join(hwmon, "device", "gpu_busy_percent")
            if os.path.exists(device_busy_path):
                s_id = f"sys_{hwmon_id}_load"
                self.sys_sensors_meta[s_id] = {'label': f"{hw_name} (Load)", 'type': 'load'}
                self.sys_sensors_paths[s_id] = device_busy_path

        # 2. Inizializzazione NVML per GPU NVIDIA
        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
                device_count = pynvml.nvmlDeviceGetCount()

                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes): name = name.decode('utf-8')

                    s_id_temp = f"sys_nvml_gpu{i}_temp"
                    self.sys_sensors_meta[s_id_temp] = {'label': f"NVIDIA {name} (Temp)", 'type': 'temp'}
                    self.sys_sensors_paths[s_id_temp] = handle

                    s_id_load = f"sys_nvml_gpu{i}_load"
                    self.sys_sensors_meta[s_id_load] = {'label': f"NVIDIA {name} (Load)", 'type': 'load'}
                    self.sys_sensors_paths[s_id_load] = handle
            except Exception:
                self.nvml_initialized = False

    def get_available_system_sensors(self):
        """Restituisce un dizionario che associa gli ID dei sensori alle etichette dell'interfaccia utente."""
        return {s_id: meta['label'] for s_id, meta in self.sys_sensors_meta.items()}

    def get_system_telemetry(self):
        """Interroga le metriche correnti per tutti i sensori hwmon/nvml registrati."""
        sys_data = {}

        for s_id, path in self.sys_sensors_paths.items():
            s_type = self.sys_sensors_meta[s_id]['type']

            if s_id.startswith("sys_nvml"):
                try:
                    if s_type == 'temp':
                        val = pynvml.nvmlDeviceGetTemperature(path, pynvml.NVML_TEMPERATURE_GPU)
                        sys_data[s_id] = float(val)
                    elif s_type == 'load':
                        util = pynvml.nvmlDeviceGetUtilizationRates(path)
                        sys_data[s_id] = float(util.gpu)
                except Exception: pass
            else:
                try:
                    with open(path, "r") as f:
                        raw = int(f.read().strip())
                        if s_type in ('temp', 'volt'):
                            sys_data[s_id] = raw / 1000.0
                        elif s_type == 'load':
                            sys_data[s_id] = float(raw)
                except Exception: pass

        return sys_data

    def _find_aquaero_hwmon(self):
        """Individua il percorso hwmon dinamico assegnato al dispositivo Aquaero."""
        for name_file in glob.glob("/sys/class/hwmon/hwmon*/name"):
            try:
                with open(name_file, 'r') as f:
                    if "aquaero" in f.read():
                        return os.path.dirname(name_file)
            except Exception: continue
        return None

    def _map_hardware(self):
        """Associa specifici canali proprietari Aquaero (PWM, Fan, Volt, Temp)."""
        self.volt_channels = {}
        self.flow_channels = {}

        for i in range(1, 5):
            pwm_path = os.path.join(self.path, f"pwm{i}")
            if os.path.exists(pwm_path):
                self.pwm_channels[i] = pwm_path

            fan_path = os.path.join(self.path, f"fan{i}_input")
            if os.path.exists(fan_path):
                self.fan_channels[i] = fan_path

        # Mappatura sensori di flusso
        for i, fan_id in enumerate([5, 6], start=1):
            flow_path = os.path.join(self.path, f"fan{fan_id}_input")
            if os.path.exists(flow_path):
                self.flow_channels[i] = flow_path

        # Mappatura Voltaggi (Regex + Fallback) ---
        mapped_channels = set()

        for label_file in glob.glob(os.path.join(self.path, "in*_label")):
            try:
                with open(label_file, 'r') as f:
                    label_text = f.read().strip()
                    # Cerca la parola "fan" seguita (anche con spazi) da un numero da 1 a 4
                    match = re.search(r'fan\s*([1-4])', label_text, re.IGNORECASE)
                    if match:
                        ch_num = int(match.group(1))
                        input_file = label_file.replace("_label", "_input")
                        if os.path.exists(input_file):
                            self.volt_channels[ch_num] = input_file
                            mapped_channels.add(ch_num)
            except Exception:
                pass

        # 2. Rete di Sicurezza (Fallback)
        # Se le label falliscono o mancano, mappa usando l'ABI standard hwmon (in0=Ch1, in1=Ch2, ecc.)
        for i in range(1, 5):
            if i not in mapped_channels:
                fallback_file = os.path.join(self.path, f"in{i-1}_input")
                if os.path.exists(fallback_file):
                    self.volt_channels[i] = fallback_file

        for temp_file in glob.glob(os.path.join(self.path, "temp*_input")):
            sensor_id = os.path.basename(temp_file).split('_')[0]
            label_file = temp_file.replace("input", "label")
            label_name = sensor_id.capitalize()
            if os.path.exists(label_file):
                try:
                    with open(label_file, 'r') as f:
                        read_label = f.read().strip()
                        if read_label: label_name = read_label
                except Exception: pass
            self.sensors[sensor_id] = {'path': temp_file, 'label': f"{label_name} ({sensor_id})"}

    def get_fan_volt(self, channel):
        if channel in getattr(self, 'volt_channels', {}):
            try:
                with open(self.volt_channels[channel], "r") as f:
                    return int(f.read().strip()) / 1000.0
            except Exception: return 0.0
        return 0.0

    def get_available_sensors(self):
        sorted_sensors = sorted(self.sensors.items(), key=lambda item: int(item[0].replace('temp', '')))
        return {k: v['label'] for k, v in sorted_sensors}

    def get_sensor_temp(self, sensor_id):
        if sensor_id not in self.sensors: return None
        try:
            with open(self.sensors[sensor_id]['path'], "r") as f:
                return int(f.read().strip()) / 1000.0
        except Exception: return None

    def get_fan_rpm(self, channel):
        if channel in self.fan_channels:
            try:
                with open(self.fan_channels[channel], "r") as f:
                    return int(f.read().strip())
            except Exception: return 0
        return 0

    def get_flow_rate(self, channel):
        """Legge il sensore di flusso e converte in L/h."""
        if channel in getattr(self, 'flow_channels', {}):
            try:
                with open(self.flow_channels[channel], "r") as f:
                    return float(f.read().strip()) / 10.0
            except Exception: return 0.0
        return 0.0

    # ---------------------------------------------------------
    # INTEGRAZIONE DASHBOARD (Storico, Virtuali, UI)
    # ---------------------------------------------------------

    def set_virtual_sensor(self, virtual_id, hot_sensor_id, cold_sensor_id):
        """Registra o aggiorna un sensore virtuale nel motore."""
        self.virtual_sensors_config[virtual_id] = {
            "hot": hot_sensor_id,
            "cold": cold_sensor_id
        }

    def _update_history(self, sensor_id, value):
        """Mantiene un buffer circolare degli ultimi 60 campionamenti per i grafici."""
        if value is None:
            return

        if sensor_id not in self.history:
            self.history[sensor_id] = deque(maxlen=60)
        self.history[sensor_id].append(value)

    def get_dashboard_telemetry(self):
        sys_data = self.get_system_telemetry()

        aqua_temps = {}
        for s_id in self.sensors:
            aqua_temps[s_id] = self.get_sensor_temp(s_id)

        aqua_rpms = {}
        aqua_volts = {}
        for ch_id in range(1, 5):
            aqua_rpms[ch_id] = self.get_fan_rpm(ch_id)
            aqua_volts[ch_id] = self.get_fan_volt(ch_id)

        aqua_flows = {}
        for flow_id in range(1, 3):
            flow_val = self.get_flow_rate(flow_id)
            aqua_flows[flow_id] = flow_val
            self._update_history(f"flow_rate_{flow_id}", flow_val)

        all_temps = {**sys_data, **aqua_temps}

        virtual_data = {}
        for v_id, config in self.virtual_sensors_config.items():
            hot_val = all_temps.get(config["hot"])
            cold_val = all_temps.get(config["cold"])

            delta = self.calculate_virtual_delta(hot_val, cold_val)
            if delta is not None:
                virtual_data[v_id] = delta
                all_temps[v_id] = delta

        for s_id, val in all_temps.items():
            self._update_history(s_id, val)
        for ch_id, rpm in aqua_rpms.items():
            self._update_history(f"ch_rpm_{ch_id}", rpm)

        pwm_loads = {}
        for ch_id in range(1, 5):
            raw_pwm = self.last_pwm_written.get(ch_id, 0)
            pwm_loads[ch_id] = int((raw_pwm / 255.0) * 100)

        return {
            "system": sys_data,
            "temps": aqua_temps,
            "rpms": aqua_rpms,
            "volts": aqua_volts,
            "flows": aqua_flows,
            "virtuals": virtual_data,
            "pwm_loads": pwm_loads,
            "history": {k: list(v) for k, v in self.history.items()}
        }

    # ---------------------------------------------------------
    # MATEMATICA E LOGICA DI CONTROLLO
    # ---------------------------------------------------------

    def calculate_virtual_delta(self, temp_hot, temp_cold):
        """
        Calcola il Delta T tra due sensori (es. Temperatura Acqua - Temperatura Ambiente).
        Impedisce che il valore scenda sotto zero per evitare conflitti logici.
        """
        if temp_hot is None or temp_cold is None: return None
        return max(0.0, temp_hot - temp_cold)

    # NOTA: I parametri p_min e p_max qui rappresentano la logica visiva (es 0-100), non l'hardware
    def calculate_pwm_auto(self, temp, t_min, t_max, p_min, p_max, gamma=1.0):
        """Calcola il valore target PWM logico utilizzando una curva polinomiale (restituisce un valore compreso tra 0 e 100%)."""
        if temp is None: return 0.0
        if temp <= t_min: return float(p_min)
        if temp >= t_max: return float(p_max)
        if t_max == t_min: return float(p_max)

        t_norm = (temp - t_min) / (t_max - t_min)
        curve_factor = pow(t_norm, gamma)
        return p_min + (p_max - p_min) * curve_factor

    def calculate_pwm_manual(self, temp, curve_points):
        """Calcola il valore target logico del PWM tramite interpolazione lineare (restituisce un valore tra 0 e 100%)."""
        if temp is None or not curve_points: return 0.0

        sorted_points = sorted(curve_points, key=lambda p: p[0])

        if temp <= sorted_points[0][0]: return float(sorted_points[0][1])
        if temp >= sorted_points[-1][0]: return float(sorted_points[-1][1])

        for i in range(len(sorted_points) - 1):
            t1, p1 = sorted_points[i]
            t2, p2 = sorted_points[i+1]

            if t1 <= temp <= t2:
                if t1 == t2: return float(p2)
                else: return p1 + (p2 - p1) * ((temp - t1) / (t2 - t1))
        return 0.0


    def calculate_pwm_pid(self, channel, current_temp, target_temp, pid_mode="Normal", custom_kp=0.0, custom_ki=0.0, custom_kd=0.0):
        """Calcola il valore target logico del PWM utilizzando un PID (restituisce un valore tra 0 e 100%)."""
        if current_temp is None: return 0.0

        current_time = time.time()
        state = self.pid_states.setdefault(channel, {'integral': 0.0, 'prev_error': 0.0, 'last_time': current_time})

        dt = current_time - state['last_time']
        if dt <= 0.0: dt = 1.0

        error = current_temp - target_temp

        presets = {
            "Slow":   {"kp": 3.0, "ki": 0.05, "kd": 0.1},
            "Normal": {"kp": 5.0, "ki": 0.08, "kd": 0.3},
            "Fast":   {"kp": 8.0, "ki": 0.10, "kd": 0.5}
        }

        if pid_mode in presets:
            kp = presets[pid_mode]["kp"]
            ki = presets[pid_mode]["ki"]
            kd = presets[pid_mode]["kd"]
        else:
            kp = custom_kp
            ki = custom_ki
            kd = custom_kd

        # 1. Proporzionale
        P = kp * error

        # 2. Integrale con limitazione ANTI-WINDUP
        state['integral'] += error * dt

        if state['integral'] < 0.0:
            state['integral'] = 0.0

        max_i_contribution = 100.0
        if ki > 0:
            if state['integral'] * ki > max_i_contribution:
                state['integral'] = max_i_contribution / ki

        I = ki * state['integral']

        # 3. Derivativo
        D = kd * (error - state['prev_error']) / dt

        state['prev_error'] = error
        state['last_time'] = current_time

        # Output logico puro (0-100%)
        logical_percent = P + I + D

        if logical_percent <= 0:
            return 0.0

        return max(0.0, min(100.0, logical_percent))

    # ---------------------------------------------------------
    # MAPPATURA HARDWARE (Min Power & Start Boost)
    # ---------------------------------------------------------

    def apply_hardware_limits(self, channel, logical_percent, min_power_percent):
        """
        Converte il valore percentuale logico (0-100) nel valore in byte (0-255)
        richiesto dal controller hardware, applicando la soglia di potenza minima.
        """
        logical_percent = float(logical_percent)
        min_power_percent = float(max(0, min(100, min_power_percent)))

        # Calcolo dell'output Hardware
        if logical_percent <= 0.0:
            hardware_percent = 0.0
        else:
            hardware_percent = min_power_percent + ((100.0 - min_power_percent) * (logical_percent / 100.0))

        hardware_percent = max(0.0, min(100.0, hardware_percent))
        byte_val = int(hardware_percent * 2.55)

        return byte_val, hardware_percent

    def set_fan_speed(self, channel, pwm_value):
        """Scrive il valore target PWM in sysfs. Implementa un controllo del delta per ridurre l'utilizzo del bus USB."""
        if channel in self.pwm_channels:
            try:
                pwm_value = int(max(0, min(255, pwm_value)))

                if self.last_pwm_written.get(channel) == pwm_value:
                    return

                with open(self.pwm_channels[channel], "w") as f:
                    f.write(str(pwm_value))

                self.last_pwm_written[channel] = pwm_value
            except PermissionError:
                print(f"Insufficient permissions on PWM{channel}.")
            except Exception:
                pass

    def trigger_emergency_shutdown(self, reason="Unknown", value=0.0, delay_seconds=0):

        log_dir = "/var/lib/aquacontrol"
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] SHUTDOWN DI EMERGENZA! Motivo: '{reason}' | Valore: {value}\n"

        try:
            # 1. Scrittura del log storico permanente
            with open(os.path.join(log_dir, "emergency_log.txt"), "a") as f:
                f.write(log_message)

            # 2. Biglietto diagnostico per il prossimo login. Accumuliamo un contatore
            #    (non sovrascriviamo) così l'agent può dire "spento N volte" anche se la
            #    GUI non è mai stata riaperta tra un'emergenza e l'altra. Manteniamo le
            #    chiavi reason/value/timestamp per retro-compatibilità con i lettori vecchi.
            pending_file = os.path.join(log_dir, "emergency_pending.json")
            prev_count = 0
            try:
                if os.path.exists(pending_file):
                    with open(pending_file, "r") as pf:
                        prev_count = json.load(pf).get("count", 0)
            except Exception:
                prev_count = 0
            with open(pending_file, "w") as f:
                json.dump({"count": prev_count + 1, "reason": reason,
                           "value": value, "timestamp": timestamp}, f, indent=4)
        except Exception:
            # In emergenza non blocchiamo l'arresto se la scrittura fallisce
            pass

        print(f"[Emergenza] Innesco spegnimento hardware tra {delay_seconds} secondi. Salvate i dati.")

        if delay_seconds > 0:
            time.sleep(delay_seconds)

        # Spegnimento del sistema
        subprocess.Popen(["systemctl", "poweroff"])

    def set_channel_mode_hid(self, channel, mode):
        """Cambia modalità (DC o PWM) tramite protocollo USB raw."""
        try:
            import hid
        except ImportError:
            print("ERRORE: python-hidapi non trovato. Switch PWM/DC disabilitato.")
            return

        VENDOR_ID = 0x0c70
        PRODUCT_ID = 0xf001 # Aquaero 6

        try:
            # 1. Scansiona e trova l'interfaccia USB che accetta il Report 0x0B
            target_path = None
            for dev_info in hid.enumerate(VENDOR_ID, PRODUCT_ID):
                try:
                    tmp_dev = hid.device()
                    tmp_dev.open_path(dev_info['path'])
                    # Test silente per verificare i permessi
                    tmp_dev.get_feature_report(0x0b, 1025)
                    target_path = dev_info['path']
                    tmp_dev.close()
                    break
                except Exception:
                    pass

            if not target_path:
                print("[HIDAPI] Errore: Nessuna interfaccia USB accetta il comando di scrittura.")
                return

            # 2. Apertura sicura sull'interfaccia corretta
            device = hid.device()
            device.open_path(target_path)

            REPORT_ID = 0x0b
            # Scarica il blocco di configurazione reale (1025 bytes, il primo byte è il Report ID)
            buf = device.get_feature_report(REPORT_ID, 1025)

            # --- OFFSET ESATTI RICAVATI DAL REVERSE ENGINEERING ---
            FAN_MODE_OFFSETS = {
                1: 539, # Canale 1
                2: 559, # Canale 2
                3: 579, # Canale 3
                4: 599  # Canale 4
            }

            if channel in FAN_MODE_OFFSETS:
                target_index = FAN_MODE_OFFSETS[channel]

                # Modifica del byte: 0x00 = Power Controlled (DC), 0x02 = PWM
                if mode == "PWM":
                    buf[target_index] = 0x02
                else:
                    buf[target_index] = 0x00

                # Rispedisce il payload all'Aquaero (buf[0] contiene già il Report ID 0x0b)
                device.send_feature_report(buf)
                print(f"[HIDAPI] Switch completato con successo: Canale {channel} -> {mode} (Indice Memoria: {target_index}).")

            device.close()

        except Exception as e:
            print(f"[HIDAPI] Errore di comunicazione USB: {e}")

    def set_flow_calibration_hid(self, channel, impulses_per_liter):
        """Imposta la calibrazione nella EEPROM dell'Aquaero."""
        try:
            import hid
        except ImportError:
            return

        VENDOR_ID = 0x0c70
        PRODUCT_ID = 0xf001 # Aquaero 6

        try:
            target_path = None
            for dev_info in hid.enumerate(VENDOR_ID, PRODUCT_ID):
                try:
                    tmp_dev = hid.device()
                    tmp_dev.open_path(dev_info['path'])
                    tmp_dev.get_feature_report(0x0b, 1025)
                    target_path = dev_info['path']
                    tmp_dev.close()
                    break
                except Exception: pass

            if not target_path: return

            device = hid.device()
            device.open_path(target_path)
            buf = device.get_feature_report(0x0b, 1025)

            # --- OFFSET ESATTI HARDWARE ---
            FLOW_CALIBRATION_OFFSETS = {
                1: 416,
                2: 422
            }

            if channel in FLOW_CALIBRATION_OFFSETS:
                target_index = FLOW_CALIBRATION_OFFSETS[channel]
                impulses = int(max(0, min(65535, impulses_per_liter)))

                buf[target_index] = impulses & 0xFF
                buf[target_index + 1] = (impulses >> 8) & 0xFF

                device.send_feature_report(buf)
                print(f"[HIDAPI] Calibrazione Flow {channel} impostata a {impulses} imp/l.")

            device.close()
        except Exception as e:
            print(f"[HIDAPI] Errore: {e}")

    def apply_pwm(self, channel_id, target_pwm, boost_enabled=False, boost_time=1.0):
        """
        Gestisce l'invio del segnale PWM. Se il canale richiede un avvio rapido (boost),
        delega l'esecuzione a un thread asincrono per non bloccare il ciclo di lettura principale.
        """
        if channel_id in self.active_boosts:
            return

        last_pwm = self.last_pwm_written.get(channel_id, 0)

        if last_pwm == 0 and target_pwm > 0 and boost_enabled:
            threading.Thread(
                target=self._async_boost_worker,
                args=(channel_id, target_pwm, boost_time),
                daemon=True
            ).start()
        else:
            self.set_fan_speed(channel_id, target_pwm)
            # Aggiorna la memoria della GUI SOLO se non stiamo innescando un boost
            self.last_pwm_written[channel_id] = target_pwm

    def _async_boost_worker(self, channel_id, target_pwm, boost_time):
        """
        Esegue l'impulso iniziale (100% PWM) per il tempo specificato,
        seguito dall'assestamento al valore nominale.
        """
        self.active_boosts.add(channel_id)

        # Invia l'impulso hardware
        self.set_fan_speed(channel_id, 255)
        # Forza la GUI a mostrare l'effettivo 100% per tutta la durata del boost
        self.last_pwm_written[channel_id] = 255

        time.sleep(boost_time)

        # Fine impulso, torna al target richiesto
        self.set_fan_speed(channel_id, target_pwm)
        self.last_pwm_written[channel_id] = target_pwm

        self.active_boosts.discard(channel_id)
