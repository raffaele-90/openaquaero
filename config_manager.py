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
import json
import tempfile

# --------------------------------------------------------------------------
# PERCORSO DI SISTEMA CONDIVISO (non usare ~ / expanduser!)
#
# Il demone gira come root e parte al boot, quando ancora nessun utente ha una
# sessione: per lui "~" = /root, mentre per la GUI "~" = /home/<utente>. Erano
# due file diversi, ed è per questo che il demone leggeva un profilo vuoto e
# portava tutti i canali (pompa inclusa) a 0%.
#
# La cartella va creata dall'installer come  root:aquacontrol  con permessi 2770
# (setgid + scrittura di gruppo), così il demone (root) legge e la GUI (utente
# nel gruppo 'aquacontrol') scrive lo stesso identico file.
# Da sorgente, una tantum:
#   sudo install -dm2770 -o root -g aquacontrol /var/lib/aquacontrol
# --------------------------------------------------------------------------
CONFIG_DIR = "/var/lib/aquacontrol"
CONFIG_FILE = os.path.join(CONFIG_DIR, "aquacontrol.json")


def load_config():
    """Deserializza il file di impostazioni JSON. Fornisce un dizionario predefinito se il file è assente."""
    default_config = {
        "lang": "en",
        "use_fahrenheit": False,
        "sensors": {},
        "channels_names": {},
        "profiles": {"Default": {}},
        "last_profile": "Default",
        "hardware_channels": {},
        "flow_sensors": {},
        "autostart_min": False,
        "osd_export": False,
        "osd_scale": 1.0,
        "autoswitch_enabled": False,
        "process_profiles": {},
        "security": {},
        "osd_config": {},
        "fw360_strips": [],
        "fw360_brightness": 100,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                default_config.update(data)
            return default_config
        except Exception:
            # File corrotto o lettura fallita: meglio i default che un crash.
            pass
    return default_config


def save_config(cfg):
    """
    Serializza la configurazione in modo ATOMICO: scrive su un file temporaneo nella
    stessa cartella e poi lo rinomina (os.replace), così il demone (che rilegge al
    cambio di mtime) non legge mai un JSON troncato a metà scrittura.

    Ritorna True se salvato, False se la scrittura fallisce. NON solleva eccezioni sui
    fallimenti di I/O: il caso tipico è l'utente aggiunto al gruppo 'aquacontrol' ma
    SENZA ri-login (permesso negato sulla cartella 2770), e la GUI non deve morire per
    questo — al più non persiste. Qui niente Qt: questo modulo lo importa anche il demone.
    """
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=CONFIG_DIR, prefix=".aquacontrol.", suffix=".tmp")
    except Exception as e:
        print(f"[config] Salvataggio non riuscito su {CONFIG_FILE}: {e}", file=sys.stderr)
        return False

    try:
        with os.fdopen(fd, "w") as f:
            json.dump(cfg, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        # Leggibile/scrivibile da utente e gruppo (root legge comunque).
        try:
            os.chmod(tmp_path, 0o664)
        except OSError:
            pass
        os.replace(tmp_path, CONFIG_FILE)
        return True
    except Exception as e:
        print(f"[config] Salvataggio non riuscito su {CONFIG_FILE}: {e}", file=sys.stderr)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return False


# Variabile globale esportata per il resto dei moduli
global_config = load_config()
