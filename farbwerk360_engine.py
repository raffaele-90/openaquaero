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

import struct
import subprocess

try:
    import hid
except Exception:
    hid = None


class Farbwerk360Engine:
    """Genera i payload HID feature-report da 1666 byte per la Farbwerk 360
    (colori statici + strisce virtuali). API: set_channel, add_strip, commit,
    save_to_flash. Formato del payload documentato in PROTOCOL.md."""
    VENDOR_ID = 0x0C70
    PRODUCT_ID = 0xF010
    PAYLOAD_SIZE = 1666

    BRIGHTNESS_OFFSET = 16
    SLOT_BASE = 19
    SLOT_SIZE = 70
    NUM_SLOTS = 20          # 20 slot fisici (offset 19..1418)
    MAX_STRIPS = 20         # massimo numero di strisce virtuali
    STRIP_WIDTH = 15        # larghezza fissa di ogni striscia (implicita, non salvata)
    ROUTE_BASE = 1419
    CRC_RANGE = (1, 1664)

    # posizioni interne allo slot
    OFF_ENABLE = 0
    OFF_MODE = 1
    OFF_FLAG_A = 15
    OFF_FLAG_B = 21
    OFF_COLOR = 47          # 3 byte: G, R, B

    # Template CANONICO di uno slot ATTIVO (colore azzerato a +47/48/49).
    # Verificato UNICO su tutte le catture statiche: ogni slot acceso e' identico
    # a questo tranne i 3 byte di colore. Scriviamo QUESTO (non un patch su ALLOFF)
    # cosi' gli slot attivi sono byte-perfect.
    SLOT_ACTIVE_TEMPLATE = bytes.fromhex(
        "0f01f0000000ffff0a0f0000006400ff0000006400ff000000000000000000000000000000000000000000000000ff000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00"
    )

    ALLOFF_HEX = "0300010200a900000000000000000000ff00000000f0000000ffff0a0f000000640064000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000f0000000ffff0a0f000000640064000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000f0000000ffff0a0f000000640064000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000f0000000ffff0a0f000000640064000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000f0000000ffff0a0f000000640164000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000f0000000ffff0a0f000000640064000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000f0000000ffff0a0f000000640164000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000f0000000ffff0a0f000000640064000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000f0000000ffff0a0f000000640164000000640064000000000000000000000000000000000000000000000000ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff00ff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000ffff00000000ffff00000000ffff00000000ffff00000000ffff00000000ffff00000000ffff00000000ffff00000000ffff00000000ffff0000007800010000"

    def __init__(self):
        self.base = bytearray.fromhex(self.ALLOFF_HEX)
        self.channels = {1: None, 2: None, 3: None, 4: None}  # (r,g,b) 0-255 o None
        self.strips = []          # lista di dict {channel, start, r, g, b}, ordine di creazione
        self.brightness = 0xFF
        self.device_paths = []

    # --------------------------------------------------------------- stato
    @property
    def is_connected(self):
        return bool(self.device_paths)

    @property
    def strip_count(self):
        return len(self.strips)

    # ---- API a canale (retrocompatibile: un colore pieno per canale) ----
    def set_channel(self, channel, r, g, b):
        """Accende un canale (1..4) con colore RGB standard 0..255 (striscia dal LED 1)."""
        if channel not in self.channels:
            raise ValueError("Canale non valido (deve essere 1..4).")
        clamp = lambda v: max(0, min(255, int(round(v))))
        self.channels[channel] = (clamp(r), clamp(g), clamp(b))

    def clear_channel(self, channel):
        """Spegne un canale (1..4)."""
        if channel in self.channels:
            self.channels[channel] = None

    def all_off(self):
        for ch in self.channels:
            self.channels[ch] = None

    # ---- API a STRISCE virtuali (nuova) ----
    def add_strip(self, channel, start, r, g, b):
        """Crea una striscia larga 15 LED. Ritorna l'indice (0-based); il numero
        controller mostrato dalla scheda sara' indice+1.
          channel : canale fisico 1..4 (RGBpx1..RGBpx4)
          start   : LED iniziale 1..90 (posizione sulla scala della scheda)
          r,g,b   : colore RGB standard 0..255
        L'ordine di creazione determina lo slot occupato (come fa Aquasuite)."""
        if channel not in (1, 2, 3, 4):
            raise ValueError("Canale non valido (deve essere 1..4).")
        if len(self.strips) >= self.MAX_STRIPS:
            raise ValueError("Raggiunto il massimo di {} strisce.".format(self.MAX_STRIPS))
        clamp = lambda v: max(0, min(255, int(round(v))))
        start = max(1, min(90, int(round(start))))
        self.strips.append({'channel': int(channel), 'start': start,
                            'r': clamp(r), 'g': clamp(g), 'b': clamp(b)})
        return len(self.strips) - 1

    def set_strip(self, index, channel=None, start=None, r=None, g=None, b=None):
        """Modifica una striscia esistente (solo i parametri passati)."""
        if not (0 <= index < len(self.strips)):
            raise IndexError("Indice striscia fuori range.")
        s = self.strips[index]
        clamp = lambda v: max(0, min(255, int(round(v))))
        if channel is not None:
            if channel not in (1, 2, 3, 4):
                raise ValueError("Canale non valido (deve essere 1..4).")
            s['channel'] = int(channel)
        if start is not None:
            s['start'] = max(1, min(90, int(round(start))))
        if r is not None: s['r'] = clamp(r)
        if g is not None: s['g'] = clamp(g)
        if b is not None: s['b'] = clamp(b)

    def remove_strip(self, index):
        """Elimina una striscia. ATTENZIONE: cambia gli indici/controller successivi
        (proprio come cancellare un led controller in Aquasuite)."""
        if 0 <= index < len(self.strips):
            self.strips.pop(index)

    def clear_strips(self):
        """Elimina tutte le strisce virtuali."""
        self.strips = []

    def get_strips(self):
        """Copia della lista strisce (per la UI)."""
        return [dict(s) for s in self.strips]

    # ---- luminosita' ----
    def set_brightness(self, value):
        """Luminosita' globale come byte 0..255."""
        self.brightness = max(0, min(255, int(round(value))))

    def set_brightness_percent(self, percent):
        """Luminosita' globale in percentuale 0..100."""
        self.brightness = max(0, min(255, int(round(percent * 255 / 100.0))))

    # -------------------------------------------------------------- payload
    def _effective_strips(self):
        """Ritorna la lista di strisce da scrivere. Se sono state usate le API a
        strisce (self.strips non vuoto) usa quelle; altrimenti deriva una striscia
        per ogni canale acceso (modalita' retrocompatibile), a partire dal LED 1."""
        if self.strips:
            return self.strips
        derived = []
        for ch in (1, 2, 3, 4):
            c = self.channels[ch]
            if c is not None:
                r, g, b = c
                derived.append({'channel': ch, 'start': 1, 'r': r, 'g': g, 'b': b})
        return derived

    def build_payload(self):
        """Costruisce e restituisce i 1666 byte pronti per l'invio (CRC incluso)."""
        p = bytearray(self.base)
        p[self.BRIGHTNESS_OFFSET] = self.brightness & 0xFF

        strips = self._effective_strips()[:self.MAX_STRIPS]

        # Slot attivi: scrivo il template canonico + colore G-R-B
        for k, s in enumerate(strips):
            off = self.SLOT_BASE + k * self.SLOT_SIZE
            p[off:off + self.SLOT_SIZE] = self.SLOT_ACTIVE_TEMPLATE
            p[off + self.OFF_COLOR + 0] = s['g'] & 0xFF   # Green
            p[off + self.OFF_COLOR + 1] = s['r'] & 0xFF   # Red
            p[off + self.OFF_COLOR + 2] = s['b'] & 0xFF   # Blue

        # Tabella di routing: azzero l'area, poi scrivo i record ordinati
        for i in range(self.ROUTE_BASE, self.ROUTE_BASE + 3 * self.MAX_STRIPS):
            p[i] = 0
        records = [(k + 1, s['channel'] - 1, s['start'] - 1)
                   for k, s in enumerate(strips)]
        records.sort(key=lambda rec: (rec[1], -rec[0]))   # canale ASC, controller DESC
        for i, (b0, b1, b2) in enumerate(records):
            rec = self.ROUTE_BASE + 3 * i
            p[rec + 0] = b0
            p[rec + 1] = b1
            p[rec + 2] = b2

        lo, hi = self.CRC_RANGE
        p[1664:1666] = self._crc16(p[lo:hi])
        return bytes(p)

    def build_hex(self):
        return self.build_payload().hex()

    @staticmethod
    def _crc16(data):
        poly = 0x8005
        crc = 0xFFFF
        for b in data:
            b = int('{:08b}'.format(b)[::-1], 2)
            crc ^= (b << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ poly) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        crc = int('{:016b}'.format(crc)[::-1], 2)
        crc ^= 0xFFFF
        return struct.pack('>H', crc)

    # --------------------------------------------------------------- device
    def connect(self):
        """Cerca il Farbwerk 360 sulla USB. Non solleva eccezioni: ritorna bool."""
        self.device_paths = []
        if hid is None:
            return False
        try:
            for d in hid.enumerate(self.VENDOR_ID, self.PRODUCT_ID):
                self.device_paths.append(d['path'])
        except Exception:
            self.device_paths = []
        return bool(self.device_paths)

    def reset_usb_device(self):
        """Forza un reset del bus USB per la periferica in caso di blocco."""
        try:
            vendor = f"{self.VENDOR_ID:04x}"
            product = f"{self.PRODUCT_ID:04x}"
            subprocess.run(["usbreset", f"{vendor}:{product}"], capture_output=True)
        except Exception:
            pass

    def commit(self):
        """Genera il payload attuale e lo invia alla scheda. Ritorna bool."""
        if hid is None:
            return False

        self.connect()

        if not self.device_paths:
            self.reset_usb_device()
            self.connect()
            if not self.device_paths:
                return False

        payload = bytearray(self.build_payload())
        for path in self.device_paths:
            try:
                dev = hid.device()
                dev.open_path(path)
                res = dev.send_feature_report(payload)
                dev.close()
                if res >= 0:
                    return True
            except IOError:
                self.reset_usb_device()
                continue
            except Exception:
                continue
        return False

    # Comando di SALVATAGGIO in memoria flash (report Output ID 0x02, 11 byte).
    # Comando FISSO ricavato da Aquasuite: "scrivi in flash lo stato attuale della
    # RAM", cosi' i colori sopravvivono a spegnimento e sospensione. Va inviato DOPO
    # commit(). La flash ha cicli di scrittura limitati -> usare con parsimonia.
    SAVE_REPORT = bytes([0x02, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x34, 0xC6])

    def save_to_flash(self):
        """Rende permanente la configurazione attuale della scheda. Ritorna bool."""
        if hid is None:
            return False
        self.connect()  # ri-enumera SEMPRE, come commit()
        if not self.device_paths:
            return False
        for path in self.device_paths:
            try:
                dev = hid.device()
                dev.open_path(path)
                res = dev.write(self.SAVE_REPORT)   # report Output -> SET_REPORT
                dev.close()
                if res >= 0:
                    return True
            except Exception:
                continue
        return False

    def apply_payload_hex(self, payload_hex, save_flash=False):
        """Invia un payload GIA' COSTRUITO (hex di 1666 byte) alla scheda. È il punto di
        SOLA APPLICAZIONE usato dal demone: la costruzione dell'effetto resta nella GUI,
        qui si spinge soltanto il pacchetto già pronto. Ritorna True se l'invio riesce."""
        if hid is None:
            return False
        try:
            payload = bytearray.fromhex(payload_hex)
        except Exception:
            return False
        if len(payload) != self.PAYLOAD_SIZE:
            return False

        self.connect()
        if not self.device_paths:
            self.reset_usb_device()
            self.connect()
            if not self.device_paths:
                return False

        sent = False
        for path in self.device_paths:
            try:
                dev = hid.device()
                dev.open_path(path)
                res = dev.send_feature_report(payload)
                dev.close()
                if res >= 0:
                    sent = True
                    break
            except IOError:
                self.reset_usb_device()
                continue
            except Exception:
                continue

        if sent and save_flash:
            self.save_to_flash()
        return sent

    # --------------------------------------------- compatibilita' / comodita'
    def apply_static_colors(self, channel_configs, brightness=None):
        """Imposta i colori (un colore pieno per canale) e invia in un colpo solo.
        channel_configs: dict {canale(1..4): (r,g,b)} oppure {canale: [{'r','g','b'}]}.
        brightness: opzionale, percentuale 0..100. Ritorna True se l'invio riesce."""
        self.clear_strips()
        self.all_off()
        for ch, val in channel_configs.items():
            ch = int(ch)
            if isinstance(val, dict):
                r, g, b = val.get('r', 0), val.get('g', 0), val.get('b', 0)
            elif isinstance(val, (list, tuple)) and val and isinstance(val[0], dict):
                r, g, b = val[0].get('r', 0), val[0].get('g', 0), val[0].get('b', 0)
            else:
                r, g, b = val
            if (r, g, b) == (0, 0, 0):
                self.clear_channel(ch)
            else:
                self.set_channel(ch, r, g, b)
        if brightness is not None:
            self.set_brightness_percent(brightness)
        return self.commit()

    def apply_strips(self, strips, brightness=None):
        """Imposta una lista di strisce e invia in un colpo solo.
        strips: lista di dict {channel, start, r, g, b} in ordine di creazione.
        brightness: opzionale, percentuale 0..100. Ritorna True se l'invio riesce."""
        self.all_off()
        self.clear_strips()
        for s in strips:
            self.add_strip(s['channel'], s.get('start', 1),
                           s.get('r', 0), s.get('g', 0), s.get('b', 0))
        if brightness is not None:
            self.set_brightness_percent(brightness)
        return self.commit()


if __name__ == "__main__":
    fw = Farbwerk360Engine()
    fw.set_brightness_percent(100)
    # Esempio strisce: RGBpx4 con ciano a LED 10 e rosso a LED 1 (come la cattura)
    fw.add_strip(1, 1, 0, 255, 255)   # RGBpx1 ciano
    fw.add_strip(2, 1, 0, 255, 255)   # RGBpx2 ciano
    fw.add_strip(3, 1, 0, 255, 255)   # RGBpx3 ciano
    fw.add_strip(4, 10, 0, 255, 255)  # RGBpx4 ciano, LED 10-24
    fw.add_strip(4, 1, 255, 0, 0)     # RGBpx4 rosso, LED 1-15
    print(fw.build_hex())
