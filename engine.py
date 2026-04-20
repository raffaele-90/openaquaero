import os
import glob

# Tentativo di import silente per il supporto opzionale alle GPU Nvidia (Hardware Agnostic)
try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False

class AquaeroEngine:
    """
    Motore core di OpenAquaero.
    Gestisce l'astrazione hardware, la scansione universale dei sensori Linux (hwmon)
    e le chiamate API per le curve termiche.
    """
    def __init__(self):
        self.path = self._find_aquaero_hwmon()
        self.pwm_channels = {}
        self.fan_channels = {}
        self.sensors = {}

        # DELTA CHECK: Cache per evitare scritture USB ridondanti.
        # Scrivere continuamente lo stesso valore di PWM via USB può saturare
        # il bus o causare lag nel microcontrollore dell'Aquaero.
        self.last_pwm_written = {}

        # Mappe per l'aggregazione dei sensori di sistema (Temps, Volts, Loads)
        self.sys_sensors_meta = {}
        self.sys_sensors_paths = {}

        self.nvml_initialized = False
        self._init_system_sensors()

        if not self.path:
            print("ERRORE: Nessuna scheda Aquaero rilevata nel sistema sysfs!")
            return

        self._map_hardware()

    def _init_system_sensors(self):
        """
        Scansiona e mette in cache tutti i percorsi dei sensori di sistema all'avvio.
        Costruisce dinamicamente i label leggendo i metadati esposti dal kernel Linux.
        """
        # 1. Scansione Standard Linux (HWMON)
        for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
            try:
                with open(os.path.join(hwmon, "name"), "r") as f:
                    hw_name = f.read().strip().upper()
            except Exception:
                continue

            # Bypassiamo l'Aquaero per non creare duplicati (gestito separatamente)
            if "AQUAERO" in hw_name:
                continue

            hwmon_id = os.path.basename(hwmon)

            # -- Sensori di Temperatura --
            for t_input in sorted(glob.glob(os.path.join(hwmon, "temp*_input"))):
                base_name = os.path.basename(t_input).split('_')[0]
                label_path = os.path.join(hwmon, f"{base_name}_label")

                sensor_label = hw_name
                # Tenta di leggere il label descrittivo assegnato dal driver del kernel
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

            # -- Sensori di Voltaggio --
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

            # -- Carico GPU (Agnostico: Standard AMD/Intel tramite sysfs) --
            device_busy_path = os.path.join(hwmon, "device", "gpu_busy_percent")
            if os.path.exists(device_busy_path):
                s_id = f"sys_{hwmon_id}_load"
                self.sys_sensors_meta[s_id] = {'label': f"{hw_name} (Load)", 'type': 'load'}
                self.sys_sensors_paths[s_id] = device_busy_path

        # 2. Inizializzazione NVML per GPU Nvidia (Driver proprietari)
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
        """Restituisce dizionario (ID -> Label) per popolare la UI"""
        return {s_id: meta['label'] for s_id, meta in self.sys_sensors_meta.items()}

    def get_system_telemetry(self):
        """Polling in tempo reale di tutte le metriche hwmon/nvml registrate"""
        sys_data = {}

        for s_id, path in self.sys_sensors_paths.items():
            s_type = self.sys_sensors_meta[s_id]['type']

            if s_id.startswith("sys_nvml"):
                # Path NVML contiene l'handle della GPU, non un file
                try:
                    if s_type == 'temp':
                        val = pynvml.nvmlDeviceGetTemperature(path, pynvml.NVML_TEMPERATURE_GPU)
                        sys_data[s_id] = float(val)
                    elif s_type == 'load':
                        util = pynvml.nvmlDeviceGetUtilizationRates(path)
                        sys_data[s_id] = float(util.gpu)
                except Exception: pass
            else:
                # Lettura raw standard da sysfs
                try:
                    with open(path, "r") as f:
                        raw = int(f.read().strip())
                        # I valori hwmon per temp e volt sono in millesimi
                        if s_type in ('temp', 'volt'):
                            sys_data[s_id] = raw / 1000.0
                        elif s_type == 'load':
                            sys_data[s_id] = float(raw)
                except Exception: pass

        return sys_data

    # --- FUNZIONI SPECIFICHE AQUAERO ---

    def _find_aquaero_hwmon(self):
        """Individua dinamicamente l'id hwmon assegnato all'Aquaero dal kernel"""
        for name_file in glob.glob("/sys/class/hwmon/hwmon*/name"):
            try:
                with open(name_file, 'r') as f:
                    if "aquaero" in f.read():
                        return os.path.dirname(name_file)
            except Exception: continue
        return None

    def _map_hardware(self):
        """Mappa i canali PWM, Fan e Temp proprietari dell'Aquaero"""
        for i in range(1, 5):
            pwm_path = os.path.join(self.path, f"pwm{i}")
            if os.path.exists(pwm_path):
                self.pwm_channels[i] = pwm_path

            fan_path = os.path.join(self.path, f"fan{i}_input")
            if os.path.exists(fan_path):
                self.fan_channels[i] = fan_path

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

    # --- MOTORE DI CALCOLO CURVE ---

    def calculate_pwm_auto(self, temp, t_min, t_max, p_min, p_max, gamma=1.0):
        """
        Calcola il target PWM usando una curva polinomiale.
        Il valore restituito è moltiplicato per 2.55 per scalare dal formato
        percentuale utente (0-100%) al formato hardware a 8 bit (0-255).
        """
        if temp is None: return 0
        if temp <= t_min: return int(p_min * 2.55)
        if temp >= t_max: return int(p_max * 2.55)
        if t_max == t_min: return int(p_max * 2.55)

        t_norm = (temp - t_min) / (t_max - t_min)
        curve_factor = pow(t_norm, gamma)
        pwm_percent = p_min + (p_max - p_min) * curve_factor
        return int(pwm_percent * 2.55)

    def calculate_pwm_manual(self, temp, curve_points):
        """Calcola il PWM tramite interpolazione lineare tra n punti (x=Temp, y=PWM%)"""
        if temp is None or not curve_points: return 0

        sorted_points = sorted(curve_points, key=lambda p: p[0])

        if temp <= sorted_points[0][0]: return int(sorted_points[0][1] * 2.55)
        if temp >= sorted_points[-1][0]: return int(sorted_points[-1][1] * 2.55)

        for i in range(len(sorted_points) - 1):
            t1, p1 = sorted_points[i]
            t2, p2 = sorted_points[i+1]

            if t1 <= temp <= t2:
                if t1 == t2: pwm_percent = p2
                else: pwm_percent = p1 + (p2 - p1) * ((temp - t1) / (t2 - t1))
                return int(pwm_percent * 2.55)
        return 0

    def set_fan_speed(self, channel, pwm_value):
        """Invia istruzioni al controller. Implementa il Delta Check."""
        if channel in self.pwm_channels:
            try:
                pwm_value = int(max(0, min(255, pwm_value)))

                # DELTA CHECK: Salta la scrittura se il valore è invariato
                if self.last_pwm_written.get(channel) == pwm_value:
                    return

                with open(self.pwm_channels[channel], "w") as f:
                    f.write(str(pwm_value))

                self.last_pwm_written[channel] = pwm_value
            except PermissionError:
                # Silenziamo o logghiamo: avviene se non ci sono permessi udev configurati
                print(f"Permessi hwmon insufficienti su PWM{channel}.")
            except Exception:
                pass
