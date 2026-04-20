import sys
import time
import json
import os
import stat
import subprocess

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QSlider, QPushButton, QGroupBox,
                               QFormLayout, QComboBox, QRadioButton, QButtonGroup,
                               QScrollArea, QLineEdit, QInputDialog, QMessageBox,
                               QSystemTrayIcon, QMenu, QStyle, QCheckBox, QDoubleSpinBox,
                               QDialog, QListWidget, QListWidgetItem, QStackedWidget,
                               QSpinBox, QFrame, QColorDialog, QFontDialog)
from PySide6.QtCore import Qt, QThread, Signal, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF, QBrush, QAction, QIcon, QFont
from PySide6.QtCore import QPointF
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from engine import AquaeroEngine
from osd_widget import AquaeroOSD

CONFIG_DIR = os.path.expanduser("~/.config/openaquaero")
CONFIG_FILE = os.path.join(CONFIG_DIR, "openaquaero.json")

def load_config():
    """Deserializza il file JSON delle impostazioni. Fornisce un dizionario di default se assente."""
    default_config = {
        "lang": "it",
        "sensors": {},
        "channels_names": {},
        "profiles": {"Default": {}},
        "last_profile": "Default",
        "autostart_min": False,
        "osd_export": False,
        "osd_scale": 1.0,
        "autoswitch_enabled": False,
        "process_profiles": {},
        "security": {},
        "osd_config": {
            "position_index": 0
        }
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                default_config.update(data)
            return default_config
        except Exception:
            pass
    return default_config

def save_config(cfg):
    """Serializza il dizionario delle impostazioni correnti scrivendolo nel file di configurazione utente."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

global_config = load_config()

TRANSLATIONS = {
    "it": {
        "app_title": "OpenAquaero - Pannello di Controllo",
        "profiles": "Profili Termici",
        "save_btn": "Salva Nuovo",
        "placeholder": "Es. 'Gaming' o 'Silent'",
        "suspend_btn": "⏸ SOSPENDI CONTROLLO",
        "resume_btn": "▶ RIPRENDI CONTROLLO",
        "autostart": "Avvio automatico all'avvio del sistema",
        "start_min": "Avvio minimizzato in tray",
        "channel": "Uscita",
        "unnamed_hw": "Hardware Non Nominato",
        "sensor": "Sensore:",
        "mode": "Modalità:",
        "mode_auto": "Curva Automatica",
        "mode_manual": "Curva Manuale",
        "fixed": "Regime Fisso",
        "t_min": "Temp. Min:",
        "t_max": "Temp. Max:",
        "p_min": "Power Min:",
        "p_max": "Power Max:",
        "p_fixed": "Livello Potenza:",
        "gamma": "Offset/Curvatura:",
        "tray_show": "Mostra OpenAquaero",
        "tray_msg": "Controllo termico attivo in background.",
        "info_btn": "ℹ Info & Licenza",
        "err_sensor": "-- °C",
        "mod_fixed_lbl": "Mod. Fissa",
        "lang_restart": "Riavvia l'applicazione per applicare la nuova lingua.",
        "lang_prompt": "Lingua modificata. Vuoi riavviare l'applicazione ora per applicare le modifiche?",
        "curve_tip": "Doppio Clic: Aggiungi Punto  |  Tasto Destro: Rimuovi Punto",
        "autoswitch": "Cambio Profilo Automatico",
        "hysteresis": "Isteresi termica (Filtro letture)",
        "fan_tab_title": "🎛️ Gestione Uscite",
        "profile_group": "Gestione Profili di Raffreddamento",
        "sidebar_fan": "Controllo Uscite",
        "sidebar_sec": "Impostazioni di Sicurezza",
        "sidebar_osd": "Configurazione OSD",
        "sec_title": "🛡️ Impostazioni di Sicurezza (Fail-Safe)",
        "sec_info": "Configura parametri di emergenza indipendenti per singola uscita. Garantisce l'integrità del sistema intervenendo automaticamente in caso di usura hardware, anomalie idrauliche o cali critici di rendimento.",
        "sec_rpm": "Allarme rotazione (soglia critica ≤):",
        "sec_temp": "Allarme temperatura (soglia critica ≥):",
        "sec_pwm": "Allarme potenza (soglia critica ≤):",
        "sec_global": "Azioni di Emergenza Globali",
        "sec_sound": "🎵 Riproduci Suono di Allarme",
        "sec_osd_flash": "🖥️ Fai lampeggiare l'OSD di Rosso",
        "sec_cmd": "⚠️ Esegui Comando di Emergenza (es. spegnimento):",
        "sec_save": "💾 Salva Impostazioni di Sicurezza",
        "sec_saved_msg": "Impostazioni di emergenza salvate con successo.",
        "osd_title": "🖥️ Configurazione OSD",
        "osd_info": "Seleziona quali sensori mostrare in sovrimpressione e assegna loro un nome personalizzato. Tutti i sensori sono stati rilevati automaticamente.",
        "osd_hotkey": "💡 <b>Attivazione Rapida in Gioco (HotKey):</b><br>Per mostrare/nascondere o spostare l'OSD in gioco, usa gli strumenti della tua distribuzione.<br>Crea due scorciatoie da tastiera (es. <b>F12</b> e <b>F2</b>) e associale a questi comandi:<br>▶ Mostra/Nascondi: <code>openaquaero --toggle-osd</code><br>▶ Sposta posizione OSD: <code>openaquaero --cycle-position</code>",
        "osd_global": "Impostazioni Globali OSD",
        "osd_show": "Mostra Pannello OSD",
        "osd_scale": "   Scala Interfaccia:",
        "osd_aesthetic": "Personalizzazione OSD",
        "osd_opacity": "Trasparenza Sfondo:",
        "osd_max_rows": "Sensori max per colonna:",
        "osd_col_names": "Testi (Nomi Sensori):",
        "osd_col_values": "Numeri e Unità:",
        "osd_col_badges": "Etichette (TMP/FAN):",
        "osd_btn_color": "Modifica Colore",
        "osd_font_style": "Stile:",
        "osd_btn_font": "Scegli Carattere (Font)",
        "osd_sensors_group": "Sensori Visualizzati (Scorri per vederli tutti)",
        "osd_save": "💾 Salva Impostazioni OSD",
        "osd_saved_msg": "Configurazione OSD salvata con successo. Le modifiche saranno visibili al prossimo aggiornamento dei sensori.",
        "author_role": "Creatore e Maintainer:",
        "tray_toggle_osd": "Mostra/Nascondi OSD",
        "tray_change_profile": "Cambia Profilo",
        "tray_quit": "Chiudi OpenAquaero",
        "tray_prof_activated": "Profilo '{p}' attivato.",
        "tray_proc_detected": "Rilevato {proc}. Profilo: {prof}",
        "tray_proc_ended": "Processo terminato. Profilo precedente ripristinato.",
        "proc_title": "Associa Processi ai Profili",
        "proc_ph": "Es. steam, blender, firefox...",
        "btn_add": "Aggiungi",
        "btn_remove": "Rimuovi Selezionato",
        "node_selected": "Punto Selezionato:",
        "color_picker": "Seleziona Colore",
        "font_default": "Font: Predefinito",
        "dialog_del_title": "Elimina Profilo",
        "dialog_del_msg": "Sei sicuro di voler eliminare il profilo '{p}'?",
        "dialog_warn_title": "Attenzione",
        "dialog_warn_default": "Sovrascrivi il profilo 'Default' premendo l'icona Salva a sinistra.",
        "dialog_ren_title": "Rinomina",
        "dialog_ren_msg": "Nuovo nome:",
        "alarm_critical_title": "🚨 ALLARME CRITICO HARDWARE 🚨",
        "alarm_cancel_exec": "ANNULLA ESECUZIONE ({s}s)",
        "alarm_exec_in": "Esecuzione comando di emergenza in: {s}s",
        "alarm_close_verify": "CHIUDI E VERIFICA"
    },
    "en": {
        "app_title": "OpenAquaero - Control Panel",
        "profiles": "Thermal Profiles",
        "save_btn": "Save New",
        "placeholder": "E.g. 'Gaming' or 'Silent'",
        "suspend_btn": "⏸ SUSPEND CONTROL",
        "resume_btn": "▶ RESUME CONTROL",
        "autostart": "Start automatically at system boot",
        "start_min": "Start minimized in tray",
        "channel": "Output",
        "unnamed_hw": "Unnamed Hardware",
        "sensor": "Sensor:",
        "mode": "Mode:",
        "mode_auto": "Automatic Curve",
        "mode_manual": "Manual Curve",
        "fixed": "Fixed Regime",
        "t_min": "Min Temp:",
        "t_max": "Max Temp:",
        "p_min": "Min Power:",
        "p_max": "Max Power:",
        "p_fixed": "Power Level:",
        "gamma": "Offset/Curvature:",
        "tray_show": "Show OpenAquaero",
        "tray_msg": "Thermal control running in background.",
        "info_btn": "ℹ Info & License",
        "err_sensor": "-- °C",
        "mod_fixed_lbl": "Fixed Mod",
        "lang_restart": "Restart the application to apply the new language.",
        "lang_prompt": "Language changed. Do you want to restart the application now to apply changes?",
        "curve_tip": "Double Click: Add Point  |  Right Click: Remove Point",
        "autoswitch": "Automatic Profile Switch",
        "hysteresis": "Thermal Hysteresis (Reading Filter)",
        "fan_tab_title": "🎛️ Outputs Management",
        "profile_group": "Cooling Profiles Management",
        "sidebar_fan": "Outputs Control",
        "sidebar_sec": "Security Settings",
        "sidebar_osd": "OSD Configuration",
        "sec_title": "🛡️ Security Settings (Fail-Safe)",
        "sec_info": "Configure independent emergency parameters for each output. Guarantees system integrity by intervening automatically in case of hardware wear, hydraulic anomalies, or critical performance drops.",
        "sec_rpm": "Rotation alarm (critical threshold ≤):",
        "sec_temp": "Temperature alarm (critical threshold ≥):",
        "sec_pwm": "Power alarm (critical threshold ≤):",
        "sec_global": "Global Emergency Actions",
        "sec_sound": "🎵 Play Alarm Sound",
        "sec_osd_flash": "🖥️ Flash OSD in Red",
        "sec_cmd": "⚠️ Execute Emergency Command (e.g. poweroff):",
        "sec_save": "💾 Save Security Settings",
        "sec_saved_msg": "Emergency settings saved successfully.",
        "osd_title": "🖥️ OSD Configuration",
        "osd_info": "Select which sensors to show on the overlay and assign them a custom name. All sensors have been detected automatically.",
        "osd_hotkey": "💡 <b>In-Game Quick Activation (HotKey):</b><br>To show/hide or move the OSD in-game, use your distribution's tools.<br>Create two keyboard shortcuts (e.g., <b>F12</b> and <b>F2</b>) and bind them to these commands:<br>▶ Show/Hide: <code>openaquaero --toggle-osd</code><br>▶ Move OSD position: <code>openaquaero --cycle-position</code>",
        "osd_global": "Global OSD Settings",
        "osd_show": "Show OSD Panel",
        "osd_scale": "   Interface Scale:",
        "osd_aesthetic": "OSD Customization",
        "osd_opacity": "Background Opacity:",
        "osd_max_rows": "Max sensors per column:",
        "osd_col_names": "Texts (Sensor Names):",
        "osd_col_values": "Numbers and Units:",
        "osd_col_badges": "Badges (TMP/FAN):",
        "osd_btn_color": "Edit Color",
        "osd_font_style": "Style:",
        "osd_btn_font": "Choose Font",
        "osd_sensors_group": "Displayed Sensors (Scroll to see all)",
        "osd_save": "💾 Save OSD Settings",
        "osd_saved_msg": "OSD configuration saved successfully. Changes will be visible on the next sensor update.",
        "author_role": "Creator and Maintainer:",
        "tray_toggle_osd": "Show/Hide OSD",
        "tray_change_profile": "Change Profile",
        "tray_quit": "Quit OpenAquaero",
        "tray_prof_activated": "Profile '{p}' activated.",
        "tray_proc_detected": "Detected {proc}. Profile: {prof}",
        "tray_proc_ended": "Process ended. Previous profile restored.",
        "proc_title": "Link Processes to Profiles",
        "proc_ph": "E.g. steam, blender, firefox...",
        "btn_add": "Add",
        "btn_remove": "Remove Selected",
        "node_selected": "Selected Node:",
        "color_picker": "Select Color",
        "font_default": "Font: Default",
        "dialog_del_title": "Delete Profile",
        "dialog_del_msg": "Are you sure you want to delete the profile '{p}'?",
        "dialog_warn_title": "Warning",
        "dialog_warn_default": "Overwrite the 'Default' profile by clicking the Save icon on the left.",
        "dialog_ren_title": "Rename",
        "dialog_ren_msg": "New name:",
        "alarm_critical_title": "🚨 CRITICAL HARDWARE ALARM 🚨",
        "alarm_cancel_exec": "CANCEL EXECUTION ({s}s)",
        "alarm_exec_in": "Executing emergency command in: {s}s",
        "alarm_close_verify": "CLOSE AND VERIFY"
    },
    "de": {
        "app_title": "OpenAquaero - Bedienfeld",
        "profiles": "Thermische Profile",
        "save_btn": "Neu Speichern",
        "placeholder": "Z.B. 'Gaming' oder 'Silent'",
        "suspend_btn": "⏸ STEUERUNG AUSSETZEN",
        "resume_btn": "▶ STEUERUNG FORTSETZEN",
        "autostart": "Beim Systemstart automatisch ausführen",
        "start_min": "Minimiert im Tray starten",
        "channel": "Ausgang",
        "unnamed_hw": "Unbenannte Hardware",
        "sensor": "Sensor:",
        "mode": "Modus:",
        "mode_auto": "Automatische Kurve",
        "mode_manual": "Manuelle Kurve",
        "fixed": "Fester Betrieb",
        "t_min": "Min Temp:",
        "t_max": "Max Temp:",
        "p_min": "Min Leistung:",
        "p_max": "Max Leistung:",
        "p_fixed": "Leistungsstufe:",
        "gamma": "Offset/Krümmung:",
        "tray_show": "OpenAquaero anzeigen",
        "tray_msg": "Thermische Steuerung läuft im Hintergrund.",
        "info_btn": "ℹ Info & Lizenz",
        "err_sensor": "-- °C",
        "mod_fixed_lbl": "Fester Modus",
        "lang_restart": "Starten Sie die Anwendung neu, um die neue Sprache anzuwenden.",
        "lang_prompt": "Sprache geändert. Möchten Sie die Anwendung jetzt neu starten?",
        "curve_tip": "Doppelklick: Punkt hinzufügen  |  Rechtsklick: Punkt entfernen",
        "autoswitch": "Automatischer Profilwechsel",
        "hysteresis": "Thermische Hysterese (Lesefilter)",
        "fan_tab_title": "🎛️ Ausgänge verwalten",
        "profile_group": "Kühlprofile verwalten",
        "sidebar_fan": "Ausgangssteuerung",
        "sidebar_sec": "Sicherheitseinstellungen",
        "sidebar_osd": "OSD-Konfiguration",
        "sec_title": "🛡️ Sicherheitseinstellungen (Fail-Safe)",
        "sec_info": "Konfigurieren Sie unabhängige Notfallparameter für jeden Ausgang. Garantiert die Systemintegrität durch automatisches Eingreifen bei Hardwareverschleiß, hydraulischen Anomalien oder kritischen Leistungseinbrüchen.",
        "sec_rpm": "Rotationsalarm (kritische Schwelle ≤):",
        "sec_temp": "Temperaturalarm (kritische Schwelle ≥):",
        "sec_pwm": "Leistungsalarm (kritische Schwelle ≤):",
        "sec_global": "Globale Notfallmaßnahmen",
        "sec_sound": "🎵 Alarmton abspielen",
        "sec_osd_flash": "🖥️ OSD rot blinken lassen",
        "sec_cmd": "⚠️ Notfallbefehl ausführen (z.B. poweroff):",
        "sec_save": "💾 Sicherheitseinstellungen speichern",
        "sec_saved_msg": "Notfalleinstellungen erfolgreich gespeichert.",
        "osd_title": "🖥️ OSD-Konfiguration",
        "osd_info": "Wählen Sie aus, welche Sensoren im Overlay angezeigt werden sollen, und weisen Sie ihnen einen benutzerdefinierten Namen zu. Alle Sensoren wurden automatisch erkannt.",
        "osd_hotkey": "💡 <b>Schnellaktivierung im Spiel (HotKey):</b><br>Um das OSD im Spiel ein-/auszublenden oder zu verschieben, verwenden Sie die Tools Ihrer Distribution.<br>Erstellen Sie zwei Tastenkombinationen (z. B. <b>F12</b> und <b>F2</b>) und weisen Sie diese Befehle zu:<br>▶ Ein-/Ausblenden: <code>openaquaero --toggle-osd</code><br>▶ OSD-Position verschieben: <code>openaquaero --cycle-position</code>",
        "osd_global": "Globale OSD-Einstellungen",
        "osd_show": "OSD-Panel anzeigen",
        "osd_scale": "   Schnittstellenskalierung:",
        "osd_aesthetic": "OSD-Anpassung",
        "osd_opacity": "Hintergrundtransparenz:",
        "osd_max_rows": "Max Sensoren pro Spalte:",
        "osd_col_names": "Texte (Sensornamen):",
        "osd_col_values": "Zahlen und Einheiten:",
        "osd_col_badges": "Abzeichen (TMP/FAN):",
        "osd_btn_color": "Farbe bearbeiten",
        "osd_font_style": "Stil:",
        "osd_btn_font": "Schriftart wählen",
        "osd_sensors_group": "Angezeigte Sensoren (scrollen für alle)",
        "osd_save": "💾 OSD-Einstellungen speichern",
        "osd_saved_msg": "OSD-Konfiguration erfolgreich gespeichert. Änderungen werden beim nächsten Sensor-Update sichtbar.",
        "author_role": "Ersteller und Betreuer:",
        "tray_toggle_osd": "OSD anzeigen/ausblenden",
        "tray_change_profile": "Profil ändern",
        "tray_quit": "OpenAquaero beenden",
        "tray_prof_activated": "Profil '{p}' aktiviert.",
        "tray_proc_detected": "{proc} erkannt. Profil: {prof}",
        "tray_proc_ended": "Prozess beendet. Vorheriges Profil wiederhergestellt.",
        "proc_title": "Prozesse mit Profilen verknüpfen",
        "proc_ph": "Z.B. steam, blender, firefox...",
        "btn_add": "Hinzufügen",
        "btn_remove": "Ausgewählte entfernen",
        "node_selected": "Ausgewählter Punkt:",
        "color_picker": "Farbe wählen",
        "font_default": "Schriftart: Standard",
        "dialog_del_title": "Profil löschen",
        "dialog_del_msg": "Möchten Sie das Profil '{p}' wirklich löschen?",
        "dialog_warn_title": "Warnung",
        "dialog_warn_default": "Überschreiben Sie das Profil 'Default', indem Sie auf das Speichern-Symbol links klicken.",
        "dialog_ren_title": "Umbenennen",
        "dialog_ren_msg": "Neuer Name:",
        "alarm_critical_title": "🚨 KRITISCHER HARDWARE-ALARM 🚨",
        "alarm_cancel_exec": "AUSFÜHRUNG ABBRECHEN ({s}s)",
        "alarm_exec_in": "Notfallbefehl wird ausgeführt in: {s}s",
        "alarm_close_verify": "SCHLIESSEN UND ÜBERPRÜFEN"
    },
    "fr": {
        "app_title": "OpenAquaero - Panneau de Contrôle",
        "profiles": "Profils Thermiques",
        "save_btn": "Sauvegarder",
        "placeholder": "Ex. 'Gaming' ou 'Silent'",
        "suspend_btn": "⏸ SUSPENDRE CONTRÔLE",
        "resume_btn": "▶ REPRENDRE CONTRÔLE",
        "autostart": "Démarrage automatique au lancement du système",
        "start_min": "Démarrer minimisé dans le tray",
        "channel": "Sortie",
        "unnamed_hw": "Matériel Sans Nom",
        "sensor": "Capteur:",
        "mode": "Mode:",
        "mode_auto": "Courbe Auto",
        "mode_manual": "Courbe Manuelle",
        "fixed": "Régime Fixe",
        "t_min": "Temp Min:",
        "t_max": "Temp Max:",
        "p_min": "Puissance Min:",
        "p_max": "Puissance Max:",
        "p_fixed": "Niveau Puissance:",
        "gamma": "Décalage/Courbure:",
        "tray_show": "Afficher OpenAquaero",
        "tray_msg": "Contrôle thermique en arrière-plan.",
        "info_btn": "ℹ Info & Licence",
        "err_sensor": "-- °C",
        "mod_fixed_lbl": "Mode Fixe",
        "lang_restart": "Redémarrez l'application pour appliquer la langue.",
        "lang_prompt": "Langue modifiée. Voulez-vous redémarrer maintenant ?",
        "curve_tip": "Double Clic : Ajouter Point  |  Clic Droit : Supprimer Point",
        "autoswitch": "Changement de Profil Automatique",
        "hysteresis": "Hystérésis thermique (Filtre de lecture)",
        "fan_tab_title": "🎛️ Gestion des Sorties",
        "profile_group": "Gestion des Profils de Refroidissement",
        "sidebar_fan": "Contrôle des Sorties",
        "sidebar_sec": "Paramètres de Sécurité",
        "sidebar_osd": "Configuration OSD",
        "sec_title": "🛡️ Paramètres de Sécurité (Fail-Safe)",
        "sec_info": "Configurez des paramètres d'urgence indépendants pour chaque sortie. Garantit l'intégrité du système en intervenant automatiquement en cas d'usure matérielle, d'anomalies hydrauliques ou de baisses de performances critiques.",
        "sec_rpm": "Alarme de rotation (seuil critique ≤) :",
        "sec_temp": "Alarme de température (seuil critique ≥) :",
        "sec_pwm": "Alarme de puissance (seuil critique ≤) :",
        "sec_global": "Actions d'Urgence Globales",
        "sec_sound": "🎵 Jouer un Son d'Alarme",
        "sec_osd_flash": "🖥️ Faire clignoter l'OSD en Rouge",
        "sec_cmd": "⚠️ Exécuter une Commande d'Urgence (ex. poweroff) :",
        "sec_save": "💾 Sauvegarder les Paramètres de Sécurité",
        "sec_saved_msg": "Paramètres d'urgence sauvegardés avec succès.",
        "osd_title": "🖥️ Configuration OSD",
        "osd_info": "Sélectionnez les capteurs à afficher en superposition et attribuez-leur un nom personnalisé. Tous les capteurs ont été détectés automatiquement.",
        "osd_hotkey": "💡 <b>Activation Rapide en Jeu (HotKey) :</b><br>Pour afficher/masquer ou déplacer l'OSD en jeu, utilisez les outils de votre distribution.<br>Créez deux raccourcis clavier (ex. <b>F12</b> et <b>F2</b>) et associez-les à ces commandes :<br>▶ Afficher/Masquer : <code>openaquaero --toggle-osd</code><br>▶ Déplacer la position OSD : <code>openaquaero --cycle-position</code>",
        "osd_global": "Paramètres Globaux OSD",
        "osd_show": "Afficher le Panneau OSD",
        "osd_scale": "   Échelle de l'Interface :",
        "osd_aesthetic": "Personnalisation OSD",
        "osd_opacity": "Opacité de l'Arrière-plan :",
        "osd_max_rows": "Capteurs max par colonne :",
        "osd_col_names": "Textes (Noms des Capteurs) :",
        "osd_col_values": "Nombres et Unités :",
        "osd_col_badges": "Badges (TMP/FAN) :",
        "osd_btn_color": "Modifier la Couleur",
        "osd_font_style": "Style :",
        "osd_btn_font": "Choisir la Police (Font)",
        "osd_sensors_group": "Capteurs Affichés (Faites défiler pour tout voir)",
        "osd_save": "💾 Sauvegarder les Paramètres OSD",
        "osd_saved_msg": "Configuration OSD sauvegardée avec succès. Les modifications seront visibles lors de la prochaine mise à jour des capteurs.",
        "author_role": "Créateur et Mainteneur :",
        "tray_toggle_osd": "Afficher/Masquer OSD",
        "tray_change_profile": "Changer de Profil",
        "tray_quit": "Quitter OpenAquaero",
        "tray_prof_activated": "Profil '{p}' activé.",
        "tray_proc_detected": "{proc} détecté. Profil : {prof}",
        "tray_proc_ended": "Processus terminé. Profil précédent restauré.",
        "proc_title": "Lier les Processus aux Profils",
        "proc_ph": "Ex. steam, blender, firefox...",
        "btn_add": "Ajouter",
        "btn_remove": "Supprimer la sélection",
        "node_selected": "Point Sélectionné :",
        "color_picker": "Sélectionner la couleur",
        "font_default": "Police : Par défaut",
        "dialog_del_title": "Supprimer le Profil",
        "dialog_del_msg": "Êtes-vous sûr de vouloir supprimer le profil '{p}' ?",
        "dialog_warn_title": "Attention",
        "dialog_warn_default": "Écrasez le profil 'Default' en cliquant sur l'icône de sauvegarde à gauche.",
        "dialog_ren_title": "Renommer",
        "dialog_ren_msg": "Nouveau nom :",
        "alarm_critical_title": "🚨 ALARME MATÉRIELLE CRITIQUE 🚨",
        "alarm_cancel_exec": "ANNULER L'EXÉCUTION ({s}s)",
        "alarm_exec_in": "Exécution de la commande d'urgence dans : {s}s",
        "alarm_close_verify": "FERMER ET VÉRIFIER"
    },
    "es": {
        "app_title": "OpenAquaero - Panel de Control",
        "profiles": "Perfiles Térmicos",
        "save_btn": "Guardar Nuevo",
        "placeholder": "Ej. 'Gaming' o 'Silent'",
        "suspend_btn": "⏸ SUSPENDER CONTROL",
        "resume_btn": "▶ REANUDAR CONTROL",
        "autostart": "Inicio automático al arrancar el sistema",
        "start_min": "Iniciar minimizado en la bandeja",
        "channel": "Salida",
        "unnamed_hw": "Hardware Sin Nombre",
        "sensor": "Sensor:",
        "mode": "Modo:",
        "mode_auto": "Curva Automática",
        "mode_manual": "Curva Manual",
        "fixed": "Régimen Fijo",
        "t_min": "Temp Mín:",
        "t_max": "Temp Máx:",
        "p_min": "Potencia Mín:",
        "p_max": "Potencia Máx:",
        "p_fixed": "Nivel Potencia:",
        "gamma": "Offset/Curvatura:",
        "tray_show": "Mostrar OpenAquaero",
        "tray_msg": "Control térmico en segundo plano.",
        "info_btn": "ℹ Info & Licencia",
        "err_sensor": "-- °C",
        "mod_fixed_lbl": "Modo Fijo",
        "lang_restart": "Reinicie la aplicación para aplicar el idioma.",
        "lang_prompt": "Idioma cambiado. ¿Desea reiniciar ahora?",
        "curve_tip": "Doble Clic: Añadir Punto  |  Clic Derecho: Eliminar Punto",
        "autoswitch": "Cambio de Perfil Automático",
        "hysteresis": "Histéresis térmica (Filtro de lectura)",
        "fan_tab_title": "🎛️ Gestión de Salidas",
        "profile_group": "Gestión de Perfiles de Refrigeración",
        "sidebar_fan": "Control de Salidas",
        "sidebar_sec": "Configuración de Seguridad",
        "sidebar_osd": "Configuración OSD",
        "sec_title": "🛡️ Configuración de Seguridad (Fail-Safe)",
        "sec_info": "Configura parámetros de emergencia independientes para cada salida. Garantiza la integridad del sistema interviniendo automáticamente en caso de desgaste del hardware, anomalías hidráulicas o caídas críticas de rendimiento.",
        "sec_rpm": "Alarma de rotación (umbral crítico ≤):",
        "sec_temp": "Alarma de temperatura (umbral crítico ≥):",
        "sec_pwm": "Alarma de potencia (umbral crítico ≤):",
        "sec_global": "Acciones de Emergencia Globales",
        "sec_sound": "🎵 Reproducir Sonido de Alarma",
        "sec_osd_flash": "🖥️ Hacer parpadear el OSD en Rojo",
        "sec_cmd": "⚠️ Ejecutar Comando de Emergencia (ej. poweroff):",
        "sec_save": "💾 Guardar Configuración de Seguridad",
        "sec_saved_msg": "Configuración de emergencia guardada con éxito.",
        "osd_title": "🖥️ Configuración OSD",
        "osd_info": "Selecciona qué sensores mostrar en la superposición y asígnales un nombre personalizado. Todos los sensores han sido detectados automáticamente.",
        "osd_hotkey": "💡 <b>Activación Rápida en Juego (HotKey):</b><br>Para mostrar/ocultar o mover el OSD en el juego, usa las herramientas de tu distribución.<br>Crea dos atajos de teclado (ej. <b>F12</b> y <b>F2</b>) y asígnalos a estos comandos:<br>▶ Mostrar/Ocultar: <code>openaquaero --toggle-osd</code><br>▶ Mover posición OSD: <code>openaquaero --cycle-position</code>",
        "osd_global": "Configuración Global OSD",
        "osd_show": "Mostrar Panel OSD",
        "osd_scale": "   Escala de Interfaz:",
        "osd_aesthetic": "Personalización OSD",
        "osd_opacity": "Opacidad del Fondo:",
        "osd_max_rows": "Sensores máx por columna:",
        "osd_col_names": "Textos (Nombres de Sensores):",
        "osd_col_values": "Números y Unidades:",
        "osd_col_badges": "Insignias (TMP/FAN):",
        "osd_btn_color": "Modificar Color",
        "osd_font_style": "Estilo:",
        "osd_btn_font": "Elegir Fuente (Font)",
        "osd_sensors_group": "Sensores Mostrados (Desplázate para ver todos)",
        "osd_save": "💾 Guardar Configuración OSD",
        "osd_saved_msg": "Configuración OSD guardada con éxito. Los cambios serán visibles en la próxima actualización de los sensores.",
        "author_role": "Creador y Mantenedor:",
        "tray_toggle_osd": "Mostrar/Ocultar OSD",
        "tray_change_profile": "Cambiar Perfil",
        "tray_quit": "Salir de OpenAquaero",
        "tray_prof_activated": "Perfil '{p}' activado.",
        "tray_proc_detected": "Detectado {proc}. Perfil: {prof}",
        "tray_proc_ended": "Proceso finalizado. Perfil anterior restaurado.",
        "proc_title": "Vincular Procesos a Perfiles",
        "proc_ph": "Ej. steam, blender, firefox...",
        "btn_add": "Añadir",
        "btn_remove": "Eliminar Seleccionado",
        "node_selected": "Punto Seleccionado:",
        "color_picker": "Seleccionar Color",
        "font_default": "Fuente: Predeterminada",
        "dialog_del_title": "Eliminar Perfil",
        "dialog_del_msg": "¿Estás seguro de que deseas eliminar el perfil '{p}'?",
        "dialog_warn_title": "Advertencia",
        "dialog_warn_default": "Sobrescribe el perfil 'Default' haciendo clic en el icono de guardar a la izquierda.",
        "dialog_ren_title": "Renombrar",
        "dialog_ren_msg": "Nuevo nombre:",
        "alarm_critical_title": "🚨 ALARMA CRÍTICA DE HARDWARE 🚨",
        "alarm_cancel_exec": "CANCELAR EJECUCIÓN ({s}s)",
        "alarm_exec_in": "Ejecutando comando de emergencia en: {s}s",
        "alarm_close_verify": "CERRAR Y VERIFICAR"
    }
}

def T(key):
    """Restituisce la stringa tradotta in base alla lingua impostata in configurazione."""
    lang = global_config.get("lang", "it")
    return TRANSLATIONS.get(lang, TRANSLATIONS["it"]).get(key, key)

# Definizione del foglio di stile globale Qt. L'architettura visiva si affida
# ad un singolo colore di accento (#00e5ff) su sfondi scuri desaturati per ottimizzare il contrasto.
MODERN_STYLE = """
QMainWindow { background-color: #11111b; }
QWidget { color: #cdd6f4; font-family: system-ui, 'Inter', 'Noto Sans', sans-serif; }
QScrollArea { border: none; background-color: transparent; }
QGroupBox { border: 2px solid #313244; border-radius: 8px; margin-top: 25px; background-color: #181825; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 0px; top: 2px; padding: 0px 5px; background-color: transparent; border: none; color: #00e5ff; font-weight: bold; font-size: 15px; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 5px; color: #cdd6f4; font-weight: bold; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #00e5ff; }
QPushButton { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 5px; padding: 8px 15px; font-weight: bold; }
QPushButton:hover:!disabled { background-color: #1e1e2e; border: 1px solid #00e5ff; color: #00e5ff; }
QPushButton:pressed:!disabled { background-color: #00e5ff; color: #11111b; }
QPushButton:disabled { color: #585b70; border: 1px solid #313244; }
QSlider::groove:horizontal { border: 1px solid #313244; height: 6px; background: #1e1e2e; border-radius: 3px; }
QSlider::handle:horizontal { background: #00e5ff; border: 2px solid #1e1e2e; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }
QSlider::handle:horizontal:hover { background: #73f0ff; }
QSlider::handle:horizontal:disabled { background: #45475a; }
QRadioButton, QCheckBox { font-weight: bold; }
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 7px; border: 2px solid #45475a; background: #1e1e2e; }
QRadioButton::indicator:checked { background: #00e5ff; border: 2px solid #00e5ff; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 2px solid #45475a; background: #1e1e2e; }
QCheckBox::indicator:checked { background: #00e5ff; border: 2px solid #00e5ff; }
QCheckBox::indicator:disabled { border: 2px solid #313244; background: #181825; }
QListWidget#Sidebar { background-color: #11111b; border-right: 2px solid #313244; outline: 0; }
QListWidget#Sidebar::item { padding: 15px 0px; border-bottom: 1px solid #181825; }
QListWidget#Sidebar::item:selected { background-color: #1e1e2e; border-left: 4px solid #00e5ff; }
"""

# --- MODULO IPC (Inter-Process Communication) ---
# Implementazione basata su QLocalSocket necessaria per bypassare le restrizioni 
# dei compositor moderni (es. Wayland) sui keylogger globali. Permette al DE
# di inviare parametri all'istanza in esecuzione.
def send_remote_command(command):
    socket = QLocalSocket()
    socket.connectToServer("OpenAquaero_Server")
    if socket.waitForConnected(500):
        socket.write(command.encode())
        socket.waitForBytesWritten(500)
        return True
    return False

class CommandServer(QLocalServer):
    command_received = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.newConnection.connect(self.handle_connection)
    def handle_connection(self):
        socket = self.nextPendingConnection()
        if socket.waitForReadyRead(500):
            command = socket.readAll().data().decode()
            self.command_received.emit(command)
            socket.disconnectFromServer()
# ---------------------------------------------------

class HardwareWorker(QThread):
    """Worker in background per l'interrogazione hardware asincrona e calcolo termico."""
    telemetry_ready = Signal(dict)
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.running = True
        self.active_control = True
        self.pwm_commands = {}
        
    def run(self):
        while self.running:
            data = {'temps': {}, 'rpms': {}}
            for s_id in self.engine.sensors.keys():
                data['temps'][s_id] = self.engine.get_sensor_temp(s_id)
            for ch_id in range(1, 5):
                data['rpms'][ch_id] = self.engine.get_fan_rpm(ch_id)

            data['system'] = self.engine.get_system_telemetry()

            if self.active_control:
                for ch_id, pwm_val in self.pwm_commands.items():
                    self.engine.set_fan_speed(ch_id, pwm_val)
            self.telemetry_ready.emit(data)
            time.sleep(1)
            
    def stop(self):
        self.running = False
        self.wait()

class CurveVisualizer(QWidget):
    """Componente grafico per la renderizzazione della curva termica automatica polinomiale."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.t_min = 35; self.t_max = 45; self.p_min = 0; self.p_max = 100
        self.gamma = 1.0; self.current_temp = 0.0

    def update_curve(self, t_min, t_max, p_min, p_max, gamma, current_temp):
        self.t_min = t_min; self.t_max = t_max; self.p_min = p_min; self.p_max = p_max
        self.gamma = gamma; self.current_temp = current_temp
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width(); h = self.height()
        
        bg_color = QColor("#11111b") if self.isEnabled() else QColor("#181825")
        painter.fillRect(0, 0, w, h, bg_color)
        
        margin_x = 35; margin_y = 25
        graph_w = w - (margin_x * 2); graph_h = h - (margin_y * 2)
        
        painter.setPen(QPen(QColor("#45475a"), 1, Qt.DashLine))
        painter.drawLine(margin_x, h - margin_y, w - margin_x, h - margin_y)
        painter.drawLine(margin_x, margin_y, margin_x, h - margin_y)

        vis_t_min = 10.0; vis_t_max = 100.0
        polygon = QPolygonF()
        polygon.append(QPointF(margin_x, h - margin_y))
        
        for i in range(51):
            temp_step = vis_t_min + (i / 50.0) * (vis_t_max - vis_t_min)
            if temp_step <= self.t_min: pwm = self.p_min
            elif temp_step >= self.t_max: pwm = self.p_max
            else:
                if self.t_max == self.t_min: t_norm = 1.0
                else: t_norm = (temp_step - self.t_min) / (self.t_max - self.t_min)
                pwm = self.p_min + (self.p_max - self.p_min) * pow(t_norm, self.gamma)
            
            x = margin_x + ((temp_step - vis_t_min) / (vis_t_max - vis_t_min)) * graph_w
            y = (h - margin_y) - ((pwm / 100.0) * graph_h)
            polygon.append(QPointF(x, y))
            
        polygon.append(QPointF(w - margin_x, h - margin_y))
        
        painter.setPen(Qt.NoPen)
        brush_color = QColor("#00e5ff") if self.isEnabled() else QColor("#45475a")
        brush_color.setAlpha(40)
        painter.setBrush(QBrush(brush_color))
        painter.drawPolygon(polygon)
        
        pen_color = QColor("#00e5ff") if self.isEnabled() else QColor("#555555")
        painter.setPen(QPen(pen_color, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolyline(polygon.mid(1, 51))

        painter.setPen(QPen(QColor("#a6adc8"), 1))
        font = painter.font(); font.setPointSize(8); painter.setFont(font)
        painter.drawText(5, h - margin_y + 4, "0%")
        painter.drawText(5, margin_y + 4, "100%")
        painter.drawText(margin_x - 10, h - 5, "10°C")
        painter.drawText(w - margin_x - 15, h - 5, "100°C")

        if self.isEnabled() and vis_t_min <= self.current_temp <= vis_t_max:
            x_temp = margin_x + ((self.current_temp - vis_t_min) / (vis_t_max - vis_t_min)) * graph_w
            painter.setPen(QPen(QColor("#00e5ff"), 2, Qt.DashLine))
            painter.drawLine(int(x_temp), margin_y, int(x_temp), h - margin_y)

class InteractiveCurveWidget(QWidget):
    """Componente grafico per la manipolazione interattiva a nodi (interpolazione lineare)."""
    curve_changed = Signal()
    node_selected = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setMouseTracking(True)
        self.points = [[25.0, 20.0], [45.0, 40.0], [70.0, 100.0]]
        self.current_temp = 0.0
        self.current_pwm = 0.0
        self.MIN_T = 10.0; self.MAX_T = 100.0
        self.MIN_P = 0.0; self.MAX_P = 100.0
        self.margin_x = 40; self.margin_y = 25
        self.dragging_idx = -1; self.hover_idx = -1; self.selected_idx = -1

    def t_to_x(self, t):
        w = self.width() - (self.margin_x * 2)
        return self.margin_x + ((t - self.MIN_T) / (self.MAX_T - self.MIN_T)) * w
        
    def p_to_y(self, p):
        h = self.height() - (self.margin_y * 2)
        return (self.height() - self.margin_y) - ((p - self.MIN_P) / (self.MAX_P - self.MIN_P)) * h
        
    def x_to_t(self, x):
        w = self.width() - (self.margin_x * 2)
        val = self.MIN_T + ((x - self.margin_x) / w) * (self.MAX_T - self.MIN_T)
        return max(self.MIN_T, min(self.MAX_T, val))
        
    def y_to_p(self, y):
        h = self.height() - (self.margin_y * 2)
        val = self.MIN_P + (((self.height() - self.margin_y) - y) / h) * (self.MAX_P - self.MIN_P)
        return max(self.MIN_P, min(self.MAX_P, val))

    def mousePressEvent(self, event):
        if not self.isEnabled(): return
        pos = event.position()
        for i, (t, p) in enumerate(self.points):
            x = self.t_to_x(t); y = self.p_to_y(p)
            if (pos.x() - x)**2 + (pos.y() - y)**2 < 100:
                if event.button() == Qt.LeftButton:
                    self.dragging_idx = i; self.selected_idx = i
                    self.node_selected.emit(t, p)
                elif event.button() == Qt.RightButton and len(self.points) > 2:
                    self.points.pop(i); self.selected_idx = -1
                    self.curve_changed.emit()
                self.update()
                return
        if event.button() == Qt.LeftButton:
            self.selected_idx = -1
            self.update()

    def mouseMoveEvent(self, event):
        if not self.isEnabled(): return
        pos = event.position()
        hovered = -1
        for i, (t, p) in enumerate(self.points):
            x = self.t_to_x(t); y = self.p_to_y(p)
            if (pos.x() - x)**2 + (pos.y() - y)**2 < 100:
                hovered = i
                break
                
        if hovered != self.hover_idx:
            self.hover_idx = hovered
            self.update()
            
        if self.dragging_idx >= 0:
            raw_t = self.x_to_t(pos.x()); raw_p = self.y_to_p(pos.y())
            new_t = round(raw_t * 2) / 2.0; new_p = round(raw_p * 2) / 2.0
            
            min_t_bound = self.MIN_T if self.dragging_idx == 0 else self.points[self.dragging_idx-1][0] + 0.1
            max_t_bound = self.MAX_T if self.dragging_idx == len(self.points)-1 else self.points[self.dragging_idx+1][0] - 0.1
            safe_t = max(min_t_bound, min(max_t_bound, new_t))
            safe_p = max(self.MIN_P, min(self.MAX_P, new_p))
            
            self.points[self.dragging_idx] = [safe_t, safe_p]
            self.node_selected.emit(safe_t, safe_p)
            self.curve_changed.emit()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_idx = -1
            self.update()

    def mouseDoubleClickEvent(self, event):
        if not self.isEnabled(): return
        if event.button() == Qt.LeftButton and len(self.points) < 20:
            new_t = round(self.x_to_t(event.position().x()) * 2) / 2.0
            new_p = round(self.y_to_p(event.position().y()) * 2) / 2.0
            self.points.append([new_t, new_p])
            self.points.sort(key=lambda p: p[0])
            self.curve_changed.emit()
            self.update()

    def update_selected_node_from_spinbox(self, new_t, new_p):
        if self.selected_idx < 0: return None, None
        min_t_bound = self.MIN_T if self.selected_idx == 0 else self.points[self.selected_idx-1][0] + 0.1
        max_t_bound = self.MAX_T if self.selected_idx == len(self.points)-1 else self.points[self.selected_idx+1][0] - 0.1
        safe_t = max(min_t_bound, min(max_t_bound, new_t))
        safe_p = max(self.MIN_P, min(self.MAX_P, new_p))
        self.points[self.selected_idx] = [safe_t, safe_p]
        self.curve_changed.emit()
        self.update()
        return safe_t, safe_p

    def update_telemetry(self, temp, pwm):
        self.current_temp = temp
        self.current_pwm = pwm
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width(); h = self.height()
        
        bg_color = QColor("#11111b") if self.isEnabled() else QColor("#181825")
        painter.fillRect(0, 0, w, h, bg_color)
        
        graph_w = w - (self.margin_x * 2); graph_h = h - (self.margin_y * 2)
        
        painter.setPen(QPen(QColor("#313244"), 1, Qt.DashLine))
        painter.drawLine(self.margin_x, h - self.margin_y, w - self.margin_x, h - self.margin_y)
        painter.drawLine(self.margin_x, self.margin_y, self.margin_x, h - self.margin_y)

        painter.setPen(QPen(QColor("#a6adc8"), 1))
        font = painter.font(); font.setPointSize(8); painter.setFont(font)
        painter.drawText(5, h - self.margin_y + 4, "0%")
        painter.drawText(5, self.margin_y + 4, "100%")
        painter.drawText(self.margin_x - 10, h - 5, f"{int(self.MIN_T)}°C")
        painter.drawText(w - self.margin_x - 10, h - 5, f"{int(self.MAX_T)}°C")

        if self.points:
            polygon = QPolygonF()
            polygon.append(QPointF(self.t_to_x(self.points[0][0]), h - self.margin_y))
            for t, p in self.points:
                polygon.append(QPointF(self.t_to_x(t), self.p_to_y(p)))
            polygon.append(QPointF(self.t_to_x(self.points[-1][0]), h - self.margin_y))
            
            brush_color = QColor("#00e5ff") if self.isEnabled() else QColor("#45475a")
            brush_color.setAlpha(30)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(brush_color))
            painter.drawPolygon(polygon)

        pen_color = QColor("#00e5ff") if self.isEnabled() else QColor("#555555")
        painter.setPen(QPen(pen_color, 2))
        painter.setBrush(Qt.NoBrush)
        
        for i in range(len(self.points) - 1):
            x1, y1 = self.t_to_x(self.points[i][0]), self.p_to_y(self.points[i][1])
            x2, y2 = self.t_to_x(self.points[i+1][0]), self.p_to_y(self.points[i+1][1])
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        if self.isEnabled() and self.MIN_T <= self.current_temp <= self.MAX_T:
            curr_x = int(self.t_to_x(self.current_temp))
            curr_y = int(self.p_to_y(self.current_pwm))
            
            painter.setPen(QPen(QColor("#00e5ff"), 1, Qt.DashLine))
            painter.drawLine(curr_x, self.margin_y, curr_x, h - self.margin_y)
            painter.drawLine(self.margin_x, curr_y, w - self.margin_x, curr_y)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#00e5ff")))
            painter.drawEllipse(QPointF(curr_x, curr_y), 4, 4)

        if self.isEnabled():
            for i, (t, p) in enumerate(self.points):
                x = self.t_to_x(t); y = self.p_to_y(p)
                is_active = (i == self.dragging_idx or i == self.hover_idx or i == self.selected_idx)
                
                node_color = QColor("#ffffff") if is_active else QColor("#00e5ff")
                r = 6 if is_active else 4
                
                painter.setPen(QPen(QColor("#1e1e2e"), 1))
                painter.setBrush(QBrush(node_color))
                painter.drawEllipse(QPointF(x, y), r, r)

                if is_active:
                    tooltip_text = f"{t}°C | {p}%"
                    font.setPointSize(9); painter.setFont(font)
                    metrics = painter.fontMetrics()
                    tw = metrics.horizontalAdvance(tooltip_text)
                    th = metrics.height()
                    tx = max(5, min(x - tw/2, w - tw - 5))
                    ty = y - r - th - 5
                    
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(QColor("#00e5ff")))
                    painter.drawRoundedRect(QRectF(tx - 4, ty - 2, tw + 8, th + 4), 3, 3)
                    
                    painter.setPen(QPen(QColor("#11111b")))
                    painter.drawText(int(tx), int(ty + th - 3), tooltip_text)

class ChannelControlWidget(QGroupBox):
    """Componente UI per il controllo logico e visivo del singolo canale hardware PWM."""
    def __init__(self, channel_id, engine, parent=None):
        super().__init__("", parent)
        self.channel_id = channel_id
        self.engine = engine
        self.last_known_temp = 0.0
        self.temp_history = [] 
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title_layout = QHBoxLayout()
        lbl_ch = QLabel(f"{T('channel')} {self.channel_id} |")
        lbl_ch.setStyleSheet("font-size: 18px; color: #a6adc8;")
        
        self.edit_name = QLineEdit()
        self.edit_name.setStyleSheet("font-size: 18px; border: none; background: transparent; color: #00e5ff; font-weight: bold;")
        
        saved_name = global_config["channels_names"].get(str(self.channel_id), T("unnamed_hw"))
        self.edit_name.setText(saved_name)
        self.edit_name.editingFinished.connect(self.save_channel_name)
        
        title_layout.addWidget(lbl_ch); title_layout.addWidget(self.edit_name)
        main_layout.addLayout(title_layout)

        line = QWidget(); line.setFixedHeight(1); line.setStyleSheet("background-color: #444;")
        main_layout.addWidget(line)

        top_layout = QHBoxLayout()
        status_layout = QVBoxLayout()
        
        self.lbl_temp = QLabel("Temp: -- °C")
        self.lbl_temp.setStyleSheet("color: #cdd6f4; font-size: 15px; font-weight: bold;")
        self.lbl_pwm = QLabel("Power: -- %")
        self.lbl_pwm.setStyleSheet("color: #a6adc8; font-size: 15px;")
        self.lbl_rpm = QLabel("Speed: -- RPM")
        self.lbl_rpm.setStyleSheet("color: #a6adc8; font-size: 15px;")
        
        status_layout.addWidget(self.lbl_temp); status_layout.addWidget(self.lbl_pwm); status_layout.addWidget(self.lbl_rpm)
        top_layout.addLayout(status_layout)

        setup_layout = QFormLayout()
        sensor_box = QHBoxLayout()
        
        self.combo_sensors = QComboBox()
        self.refresh_sensors()
        
        self.btn_rename_sensor = QPushButton("✎")
        self.btn_rename_sensor.setFixedWidth(35)
        self.btn_rename_sensor.clicked.connect(self.rename_current_sensor)
        
        sensor_box.addWidget(self.combo_sensors); sensor_box.addWidget(self.btn_rename_sensor)
        self.lbl_sensor_title = QLabel(T("sensor"))
        setup_layout.addRow(self.lbl_sensor_title, sensor_box)

        hyst_layout = QHBoxLayout()
        self.chk_hysteresis = QCheckBox(T("hysteresis"))
        self.chk_hysteresis.setStyleSheet("font-size: 12px; font-weight: normal;")
        
        self.spin_hysteresis = QDoubleSpinBox() 
        self.spin_hysteresis.setDecimals(0)
        self.spin_hysteresis.setRange(2, 60)
        self.spin_hysteresis.setValue(5)
        self.spin_hysteresis.setSuffix(" sec")
        self.spin_hysteresis.setEnabled(False)
        
        self.chk_hysteresis.toggled.connect(self.spin_hysteresis.setEnabled)
        self.chk_hysteresis.toggled.connect(lambda: self.temp_history.clear()) 
        
        hyst_layout.addWidget(self.chk_hysteresis)
        hyst_layout.addWidget(self.spin_hysteresis)
        hyst_layout.addStretch()
        setup_layout.addRow("", hyst_layout)

        radio_layout = QHBoxLayout()
        self.radio_auto = QRadioButton(T("mode_auto"))
        self.radio_manual = QRadioButton(T("mode_manual"))
        self.radio_fixed = QRadioButton(T("fixed"))
        self.radio_auto.setChecked(True)
        
        radio_layout.addWidget(self.radio_auto)
        radio_layout.addWidget(self.radio_manual)
        radio_layout.addWidget(self.radio_fixed)
        
        self.radio_auto.toggled.connect(self.update_ui_mode)
        self.radio_manual.toggled.connect(self.update_ui_mode)
        self.radio_fixed.toggled.connect(self.update_ui_mode)
        setup_layout.addRow(T("mode"), radio_layout)

        top_layout.addLayout(setup_layout)
        main_layout.addLayout(top_layout)

        self.box_auto = QWidget()
        auto_layout = QVBoxLayout(self.box_auto)
        auto_layout.setContentsMargins(0, 0, 0, 0)
        self.graph_auto = CurveVisualizer()
        auto_layout.addWidget(self.graph_auto)

        slider_layout = QFormLayout()
        self.slider_t_min = self.create_slider(10, 100, 35); self.val_t_min = QLabel("35 °C")
        self.slider_t_max = self.create_slider(10, 100, 45); self.val_t_max = QLabel("45 °C")
        self.slider_p_min = self.create_slider(0, 100, 0); self.val_p_min = QLabel("0 %")
        self.slider_p_max = self.create_slider(0, 100, 100); self.val_p_max = QLabel("100 %")
        self.slider_gamma = QSlider(Qt.Horizontal); self.slider_gamma.setRange(1, 30); self.slider_gamma.setValue(10)
        self.val_gamma = QLabel("1.0")

        self.slider_t_min.valueChanged.connect(lambda v: (self.val_t_min.setText(f"{v} °C"), self.update_graph_auto()))
        self.slider_t_max.valueChanged.connect(lambda v: (self.val_t_max.setText(f"{v} °C"), self.update_graph_auto()))
        self.slider_p_min.valueChanged.connect(lambda v: (self.val_p_min.setText(f"{v} %"), self.update_graph_auto()))
        self.slider_p_max.valueChanged.connect(lambda v: (self.val_p_max.setText(f"{v} %"), self.update_graph_auto()))
        self.slider_gamma.valueChanged.connect(lambda v: (self.val_gamma.setText(f"{v/10.0}"), self.update_graph_auto()))

        slider_layout.addRow(QLabel(T("t_min")), self.make_row(self.slider_t_min, self.val_t_min))
        slider_layout.addRow(QLabel(T("t_max")), self.make_row(self.slider_t_max, self.val_t_max))
        slider_layout.addRow(QLabel(T("p_min")), self.make_row(self.slider_p_min, self.val_p_min))
        slider_layout.addRow(QLabel(T("p_max")), self.make_row(self.slider_p_max, self.val_p_max))
        slider_layout.addRow(QLabel(T("gamma")), self.make_row(self.slider_gamma, self.val_gamma))
        auto_layout.addLayout(slider_layout)
        main_layout.addWidget(self.box_auto)

        self.box_manual = QWidget()
        manual_layout = QVBoxLayout(self.box_manual)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        self.graph_manual = InteractiveCurveWidget()
        manual_layout.addWidget(self.graph_manual)
        lbl_tip = QLabel(T("curve_tip"))
        lbl_tip.setStyleSheet("color: #6c7086; font-size: 11px;")
        lbl_tip.setAlignment(Qt.AlignCenter)
        manual_layout.addWidget(lbl_tip)

        self.box_node_edit = QWidget()
        node_layout = QHBoxLayout(self.box_node_edit)
        node_layout.setContentsMargins(0, 0, 0, 0)
        lbl_node_edit = QLabel("Punto Selezionato:")
        lbl_node_edit.setStyleSheet("color: #00e5ff;")
        
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(10.0, 100.0)
        self.spin_temp.setDecimals(1)
        self.spin_temp.setSingleStep(0.1)
        self.spin_temp.setSuffix(" °C")
        
        self.spin_pwm = QDoubleSpinBox()
        self.spin_pwm.setRange(0.0, 100.0)
        self.spin_pwm.setDecimals(1)
        self.spin_pwm.setSingleStep(0.1)
        self.spin_pwm.setSuffix(" %")
        
        node_layout.addWidget(lbl_node_edit)
        node_layout.addWidget(self.spin_temp)
        node_layout.addWidget(self.spin_pwm)
        manual_layout.addWidget(self.box_node_edit)

        self.graph_manual.node_selected.connect(self.on_node_selected)
        self.spin_temp.valueChanged.connect(self.on_spinbox_changed)
        self.spin_pwm.valueChanged.connect(self.on_spinbox_changed)
        main_layout.addWidget(self.box_manual)

        self.box_fixed = QWidget()
        fixed_layout = QHBoxLayout(self.box_fixed)
        fixed_layout.setContentsMargins(0, 5, 0, 0)
        lbl_p_fixed = QLabel(T("p_fixed"))
        lbl_p_fixed.setFixedWidth(100)
        
        self.slider_p_fixed = QSlider(Qt.Horizontal)
        self.slider_p_fixed.setRange(0, 100)
        self.slider_p_fixed.setValue(100)
        self.val_p_fixed = QLabel("100 %")
        self.val_p_fixed.setFixedWidth(45)
        self.slider_p_fixed.valueChanged.connect(lambda v: self.val_p_fixed.setText(f"{v} %"))
        
        fixed_layout.addWidget(lbl_p_fixed)
        fixed_layout.addWidget(self.slider_p_fixed)
        fixed_layout.addWidget(self.val_p_fixed)
        main_layout.addWidget(self.box_fixed)

        self.update_graph_auto()
        self.update_ui_mode()

    def create_slider(self, min_v, max_v, def_v):
        s = QSlider(Qt.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(def_v)
        return s

    def make_row(self, widget, label):
        container = QWidget()
        l = QHBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(widget)
        l.addWidget(label)
        label.setFixedWidth(55)
        return container

    def on_node_selected(self, temp, pwm):
        self.box_node_edit.show()
        self.spin_temp.blockSignals(True)
        self.spin_pwm.blockSignals(True)
        self.spin_temp.setValue(temp)
        self.spin_pwm.setValue(pwm)
        self.spin_temp.blockSignals(False)
        self.spin_pwm.blockSignals(False)

    def on_spinbox_changed(self):
        new_t = self.spin_temp.value()
        new_p = self.spin_pwm.value()
        safe_t, safe_p = self.graph_manual.update_selected_node_from_spinbox(new_t, new_p)
        if safe_t is not None and safe_p is not None:
            self.spin_temp.blockSignals(True)
            self.spin_temp.setValue(safe_t)
            self.spin_temp.blockSignals(False)

    def get_state(self):
        mode = "fixed"
        if self.radio_auto.isChecked(): mode = "auto"
        elif self.radio_manual.isChecked(): mode = "manual"
        return {
            "sensor": self.combo_sensors.currentData(),
            "mode": mode,
            "hyst_en": self.chk_hysteresis.isChecked(),
            "hyst_sec": int(self.spin_hysteresis.value()),
            "t_min": self.slider_t_min.value(),
            "t_max": self.slider_t_max.value(),
            "p_min": self.slider_p_min.value(),
            "p_max": self.slider_p_max.value(),
            "gamma": self.slider_gamma.value(),
            "points": self.graph_manual.points,
            "p_fixed": self.slider_p_fixed.value()
        }

    def set_state(self, state_dict):
        if not state_dict: return
        s_id = state_dict.get("sensor")
        if s_id:
            index = self.combo_sensors.findData(s_id)
            if index >= 0: self.combo_sensors.setCurrentIndex(index)

        mode = state_dict.get("mode", "auto")
        if mode == "fixed": self.radio_fixed.setChecked(True)
        elif mode == "manual": self.radio_manual.setChecked(True)
        else: self.radio_auto.setChecked(True)

        self.chk_hysteresis.setChecked(state_dict.get("hyst_en", False))
        self.spin_hysteresis.setValue(state_dict.get("hyst_sec", 5))

        self.slider_p_fixed.setValue(state_dict.get("p_fixed", 100))
        self.slider_t_min.setValue(state_dict.get("t_min", 35))
        self.slider_t_max.setValue(state_dict.get("t_max", 45))
        self.slider_p_min.setValue(state_dict.get("p_min", 0))
        self.slider_p_max.setValue(state_dict.get("p_max", 100))
        self.slider_gamma.setValue(state_dict.get("gamma", 10))
        
        if "points" in state_dict:
            self.graph_manual.points = [list(p) for p in state_dict["points"]]
        else:
            self.graph_manual.points = [[25.0, 20.0], [45.0, 40.0], [70.0, 100.0]]
            
        self.graph_manual.selected_idx = -1
        self.box_node_edit.hide()
        self.graph_auto.update()
        self.graph_manual.update()
        self.update_ui_mode()
        self.temp_history.clear()

    def update_ui_mode(self):
        mode = "fixed"
        if self.radio_auto.isChecked(): mode = "auto"
        elif self.radio_manual.isChecked(): mode = "manual"
        self.box_auto.setVisible(mode == "auto")
        self.box_manual.setVisible(mode == "manual")
        self.box_fixed.setVisible(mode == "fixed")
        if mode != "manual":
            self.box_node_edit.hide()
            self.graph_manual.selected_idx = -1

    def update_graph_auto(self):
        self.graph_auto.update_curve(
            self.slider_t_min.value(), self.slider_t_max.value(),
            self.slider_p_min.value(), self.slider_p_max.value(),
            self.slider_gamma.value() / 10.0, self.last_known_temp
        )

    def save_channel_name(self):
        global_config["channels_names"][str(self.channel_id)] = self.edit_name.text()
        save_config(global_config)

    def rename_current_sensor(self):
        s_id = self.combo_sensors.currentData()
        if not s_id: return
        current_name = self.combo_sensors.currentText()
        new_name, ok = QInputDialog.getText(self, T("dialog_ren_title"), T("dialog_ren_msg"), QLineEdit.Normal, current_name)
        if ok and new_name.strip():
            global_config["sensors"][s_id] = new_name.strip()
            save_config(global_config)
            self.refresh_sensors()

    def refresh_sensors(self):
        current_selection = self.combo_sensors.currentData()
        self.combo_sensors.clear()
        for s_id, hardware_label in self.engine.get_available_sensors().items():
            display_name = global_config["sensors"].get(s_id, hardware_label)
            self.combo_sensors.addItem(display_name, s_id)
        if current_selection:
            index = self.combo_sensors.findData(current_selection)
            if index >= 0: self.combo_sensors.setCurrentIndex(index)

    def process_telemetry(self, temps_dict, rpms_dict, is_controlling):
        """Elabora le metriche hardware in tempo reale per restituire i comandi PWM."""
        sensor_id = self.combo_sensors.currentData()
        raw_temp = temps_dict.get(sensor_id)
        rpm = rpms_dict.get(self.channel_id, 0)
        pwm_val_byte = None
        current_pwm_percent = 0
        working_temp = raw_temp

        self.lbl_rpm.setText(f"Speed: {rpm} RPM")

        if raw_temp is not None:
            if self.chk_hysteresis.isChecked():
                max_samples = int(self.spin_hysteresis.value())
                self.temp_history.append(raw_temp)
                if len(self.temp_history) > max_samples:
                    self.temp_history.pop(0)
                working_temp = sum(self.temp_history) / len(self.temp_history)
            else:
                self.temp_history.clear()
                working_temp = raw_temp

        # Aggiornamento UI Temperatura (Identico per Curve e Regime Fisso)
        if working_temp is not None:
            self.last_known_temp = working_temp
            self.lbl_temp.setText(f"Temp: {working_temp:.1f} °C")
        else:
            self.lbl_temp.setText(f"Temp: {T('err_sensor')}")

        if self.radio_fixed.isChecked():
            current_pwm_percent = self.slider_p_fixed.value()
            pwm_val_byte = int(current_pwm_percent * 2.55)
        else:
            if working_temp is not None:
                if self.radio_auto.isChecked():
                    pwm_val_byte = self.engine.calculate_pwm_auto(
                        working_temp, self.slider_t_min.value(), self.slider_t_max.value(),
                        self.slider_p_min.value(), self.slider_p_max.value(), self.slider_gamma.value() / 10.0
                    )
                elif self.radio_manual.isChecked():
                    pwm_val_byte = self.engine.calculate_pwm_manual(working_temp, self.graph_manual.points)
                current_pwm_percent = int((pwm_val_byte / 255.0) * 100)

        if pwm_val_byte is not None:
            self.lbl_pwm.setText(f"Power: {current_pwm_percent} %")
            if working_temp is not None:
                self.graph_auto.update_curve(self.slider_t_min.value(), self.slider_t_max.value(), self.slider_p_min.value(), self.slider_p_max.value(), self.slider_gamma.value() / 10.0, working_temp)
                self.graph_manual.update_telemetry(working_temp, current_pwm_percent)
            if is_controlling: return pwm_val_byte
        return None

class ProcessMappingDialog(QDialog):
    """Componente per l'interfaccia di assegnazione tra processi del sistema operativo e profili termici."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("proc_title"))
        self.resize(450, 300)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.refresh_list()
        layout.addWidget(self.list_widget)

        add_layout = QHBoxLayout()
        self.txt_process = QLineEdit()
        self.txt_process.setPlaceholderText(T("proc_ph"))

        self.combo_profiles = QComboBox()
        self.combo_profiles.addItems(global_config.get("profiles", {}).keys())

        self.btn_add = QPushButton(T("btn_add"))
        self.btn_add.clicked.connect(self.add_mapping)

        add_layout.addWidget(self.txt_process, stretch=2)
        add_layout.addWidget(QLabel(" ➡️ "))
        add_layout.addWidget(self.combo_profiles, stretch=1)
        add_layout.addWidget(self.btn_add)
        layout.addLayout(add_layout)

        self.btn_remove = QPushButton(T("btn_remove"))
        self.btn_remove.setStyleSheet("background-color: #ff3333; color: #ffffff;")
        self.btn_remove.clicked.connect(self.remove_mapping)
        layout.addWidget(self.btn_remove)

    def refresh_list(self):
        self.list_widget.clear()
        process_map = global_config.get("process_profiles", {})
        for proc, prof in process_map.items():
            self.list_widget.addItem(f"{proc} ➡️ {prof}")

    def add_mapping(self):
        proc = self.txt_process.text().strip()
        prof = self.combo_profiles.currentText()
        if proc and prof:
            if "process_profiles" not in global_config:
                global_config["process_profiles"] = {}
            global_config["process_profiles"][proc] = prof
            save_config(global_config)
            self.txt_process.clear()
            self.refresh_list()

    def remove_mapping(self):
        selected = self.list_widget.currentItem()
        if selected:
            text = selected.text()
            proc = text.split(" ➡️ ")[0]
            if proc in global_config.get("process_profiles", {}):
                del global_config["process_profiles"][proc]
                save_config(global_config)
                self.refresh_list()

class SecurityTabWidget(QWidget):
    """Componente per l'interfaccia degli allarmi hardware di sistema (Fail-Safe)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        lbl_title = QLabel(T("sec_title"))
        lbl_title.setStyleSheet("font-size: 20px; color: #ff3333; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl_title)

        info_txt = QLabel(T("sec_info"))
        info_txt.setWordWrap(True)
        info_txt.setStyleSheet("color: #a6adc8; margin-bottom: 15px; font-size: 13px;")
        layout.addWidget(info_txt)

        self.sec_channels = {}
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        sec_layout = QVBoxLayout(container)
        layout.addWidget(scroll)

        for i in range(1, 5):
            ch_name = global_config["channels_names"].get(str(i), f"{T('channel')} {i}")
            group = QGroupBox(f"{ch_name}")
            glayout = QFormLayout(group)

            box_rpm = QHBoxLayout()
            chk_rpm = QCheckBox(T("sec_rpm"))
            spin_rpm = QSpinBox()
            spin_rpm.setRange(0, 5000)
            spin_rpm.setSuffix(" RPM")
            box_rpm.addWidget(chk_rpm)
            box_rpm.addWidget(spin_rpm)
            box_rpm.addStretch()
            glayout.addRow("", box_rpm)

            box_temp = QHBoxLayout()
            chk_temp = QCheckBox(T("sec_temp"))
            spin_temp = QSpinBox()
            spin_temp.setRange(20, 110)
            spin_temp.setSuffix(" °C")
            box_temp.addWidget(chk_temp)
            box_temp.addWidget(spin_temp)
            box_temp.addStretch()
            glayout.addRow("", box_temp)

            box_power = QHBoxLayout()
            chk_power = QCheckBox(T("sec_pwm"))
            spin_power = QSpinBox()
            spin_power.setRange(0, 100)
            spin_power.setSuffix(" %")
            box_power.addWidget(chk_power)
            box_power.addWidget(spin_power)
            box_power.addStretch()
            glayout.addRow("", box_power)

            self.sec_channels[str(i)] = {
                "chk_rpm": chk_rpm, "spin_rpm": spin_rpm,
                "chk_temp": chk_temp, "spin_temp": spin_temp,
                "chk_power": chk_power, "spin_power": spin_power
            }
            sec_layout.addWidget(group)

        action_group = QGroupBox(T("sec_global"))
        alayout = QVBoxLayout(action_group)

        self.chk_sound = QCheckBox(T("sec_sound"))
        self.chk_osd_alert = QCheckBox(T("sec_osd_flash"))
        self.chk_osd_alert.setChecked(True)

        box_cmd = QHBoxLayout()
        self.chk_cmd = QCheckBox(T("sec_cmd"))
        self.txt_cmd = QLineEdit()
        self.txt_cmd.setPlaceholderText("systemctl poweroff")
        box_cmd.addWidget(self.chk_cmd)
        box_cmd.addWidget(self.txt_cmd)

        alayout.addWidget(self.chk_sound)
        alayout.addWidget(self.chk_osd_alert)
        alayout.addLayout(box_cmd)

        btn_save_sec = QPushButton(T("sec_save"))
        btn_save_sec.setStyleSheet("background-color: #ff3333; color: #ffffff; font-size: 14px; font-weight: bold; margin-top: 10px;")
        btn_save_sec.clicked.connect(self.save_security)
        alayout.addWidget(btn_save_sec)

        layout.addWidget(action_group)
        self.load_security()

    def save_security(self):
        sec_config = {"channels": {}, "actions": {}}
        for ch_id, widgets in self.sec_channels.items():
            sec_config["channels"][ch_id] = {
                "rpm_en": widgets["chk_rpm"].isChecked(),
                "rpm_val": widgets["spin_rpm"].value(),
                "temp_en": widgets["chk_temp"].isChecked(),
                "temp_val": widgets["spin_temp"].value(),
                "power_en": widgets["chk_power"].isChecked(),
                "power_val": widgets["spin_power"].value()
            }
        sec_config["actions"] = {
            "sound_en": self.chk_sound.isChecked(),
            "osd_en": self.chk_osd_alert.isChecked(),
            "cmd_en": self.chk_cmd.isChecked(),
            "cmd_val": self.txt_cmd.text()
        }
        global_config["security"] = sec_config
        save_config(global_config)
        QMessageBox.information(self, "Sicurezza", T("sec_saved_msg"))

    def load_security(self):
        sec_config = global_config.get("security", {})
        ch_config = sec_config.get("channels", {})
        for ch_id, widgets in self.sec_channels.items():
            saved = ch_config.get(ch_id, {})
            widgets["chk_rpm"].setChecked(saved.get("rpm_en", False))
            widgets["spin_rpm"].setValue(saved.get("rpm_val", 500))
            widgets["chk_temp"].setChecked(saved.get("temp_en", False))
            widgets["spin_temp"].setValue(saved.get("temp_val", 55))
            widgets["chk_power"].setChecked(saved.get("power_en", False))
            widgets["spin_power"].setValue(saved.get("power_val", 20))

        actions = sec_config.get("actions", {})
        self.chk_sound.setChecked(actions.get("sound_en", False))
        self.chk_osd_alert.setChecked(actions.get("osd_en", True))
        self.chk_cmd.setChecked(actions.get("cmd_en", False))
        self.txt_cmd.setText(actions.get("cmd_val", ""))

class MeltdownDialog(QDialog):
    """Finestra popup modale di avviso critico attivata dal sistema Fail-Safe."""
    def __init__(self, messages, actions_sec, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(550, 300)

        self.cmd_en = actions_sec.get("cmd_en", False)
        self.cmd_val = actions_sec.get("cmd_val", "")
        self.countdown = 10 

        layout = QVBoxLayout(self)

        bg = QFrame()
        bg.setStyleSheet("background-color: rgba(30, 30, 46, 250); border: 4px solid #ff3333; border-radius: 12px;")
        bg_layout = QVBoxLayout(bg)

        title = QLabel(T("alarm_critical_title"))
        title.setStyleSheet("color: #ff3333; font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        bg_layout.addWidget(title)

        msg_text = "\n".join(messages)
        lbl_msg = QLabel(msg_text)
        lbl_msg.setStyleSheet("color: #cdd6f4; font-size: 16px;")
        lbl_msg.setAlignment(Qt.AlignCenter)
        lbl_msg.setWordWrap(True)
        bg_layout.addWidget(lbl_msg)

        self.lbl_timer = QLabel("")
        self.lbl_timer.setStyleSheet("color: #00e5ff; font-size: 18px; font-weight: bold;")
        self.lbl_timer.setAlignment(Qt.AlignCenter)
        bg_layout.addWidget(self.lbl_timer)

        self.btn_action = QPushButton()
        self.btn_action.setStyleSheet("background-color: #ff3333; color: #ffffff; font-size: 18px; font-weight: bold; padding: 15px;")
        self.btn_action.clicked.connect(self.on_button_click)
        bg_layout.addWidget(self.btn_action)

        layout.addWidget(bg)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        if self.cmd_en and self.cmd_val:
            self.btn_action.setText(T("alarm_cancel_exec").format(s=self.countdown))
            self.lbl_timer.setText(T("alarm_exec_in").format(s=self.countdown))
            self.timer.start(1000)
        else:
            self.btn_action.setText(T("alarm_close_verify"))
            self.lbl_timer.hide()

        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def update_timer(self):
        self.countdown -= 1
        if self.countdown <= 0:
            self.timer.stop()
            self.execute_command()
        else:
            self.lbl_timer.setText(T("alarm_exec_in").format(s=self.countdown))
            self.btn_action.setText(T("alarm_cancel_exec").format(s=self.countdown))

    def execute_command(self):
        try:
            subprocess.Popen(self.cmd_val, shell=True)
        except Exception as e:
            print(f"Errore comando emergenza: {e}")
        self.accept()

    def on_button_click(self):
        self.timer.stop()
        self.accept()

class OSDConfigTabWidget(QWidget):
    """Componente per l'interfaccia di personalizzazione e configurazione dell'overlay OSD."""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        layout = QVBoxLayout(self)

        lbl_title = QLabel(T("osd_title"))
        lbl_title.setStyleSheet("font-size: 20px; color: #00e5ff; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl_title)

        info_txt = QLabel(T("osd_info"))
        info_txt.setWordWrap(True)
        info_txt.setStyleSheet("color: #a6adc8; margin-bottom: 5px; font-size: 13px;")
        layout.addWidget(info_txt)

        hotkey_info = QLabel(T("osd_hotkey"))
        hotkey_info.setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 10px; border-radius: 5px; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(hotkey_info)

        global_group = QGroupBox(T("osd_global"))
        g_layout = QHBoxLayout(global_group)

        self.main_window.chk_osd = QCheckBox(T("osd_show"))
        self.main_window.chk_osd.setStyleSheet("font-size: 13px; font-weight: bold; color: #00e5ff;")
        self.main_window.chk_osd.setChecked(global_config.get("osd_export", False))
        self.main_window.chk_osd.toggled.connect(self.main_window.toggle_osd)

        self.main_window.combo_osd_scale = QComboBox()
        self.main_window.combo_osd_scale.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
        self.main_window.combo_osd_scale.setFixedWidth(80)
        current_scale = global_config.get("osd_scale", 1.0)
        self.main_window.combo_osd_scale.setCurrentText(f"{int(current_scale * 100)}%")
        self.main_window.combo_osd_scale.currentTextChanged.connect(self.main_window.change_osd_scale)

        g_layout.addWidget(self.main_window.chk_osd)
        g_layout.addWidget(QLabel(T("osd_scale")))
        g_layout.addWidget(self.main_window.combo_osd_scale)
        g_layout.addStretch()
        layout.addWidget(global_group)

        aesthetic_group = QGroupBox(T("osd_aesthetic"))
        a_layout = QFormLayout(aesthetic_group)

        opacity_layout = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 255)
        self.slider_opacity.setFixedWidth(180)
        self.lbl_opacity_val = QLabel()
        opacity_layout.addWidget(self.slider_opacity)
        opacity_layout.addWidget(self.lbl_opacity_val)
        opacity_layout.addStretch()
        self.slider_opacity.valueChanged.connect(self.update_aesthetic)

        self.spin_max_rows = QSpinBox()
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
        self.lbl_current_font = QLabel("Font: Predefinito")
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

        sensors_group = QGroupBox(T("osd_sensors_group"))
        s_layout = QVBoxLayout(sensors_group)
        s_layout.setContentsMargins(0, 5, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        list_layout = QVBoxLayout(container)

        self.osd_items = {}

        for i in range(1, 5):
            comp_id = f"ch_{i}"
            desc = f"Aquaero: {T('channel')} {i}"
            placeholder = f"{T('channel')} {i}"
            self._add_sensor_row(list_layout, comp_id, desc, placeholder)

        sys_sensors = self.main_window.engine.get_available_system_sensors()
        for comp_id, label in sys_sensors.items():
            self._add_sensor_row(list_layout, comp_id, label, f"Es. {label}")

        s_layout.addWidget(scroll)

        btn_save = QPushButton(T("osd_save"))
        btn_save.setStyleSheet("background-color: #00e5ff; color: #11111b; font-size: 14px; font-weight: bold; margin-top: 10px;")
        btn_save.clicked.connect(self.save_osd_config)
        s_layout.addWidget(btn_save)

        layout.addWidget(sensors_group)
        self.load_osd_config()

    def _add_sensor_row(self, layout, comp_id, desc, placeholder):
        row = QHBoxLayout()
        chk = QCheckBox(desc)
        chk.setToolTip(comp_id)
        txt_name = QLineEdit()
        txt_name.setPlaceholderText(placeholder)

        row.addWidget(chk, stretch=2)
        row.addWidget(txt_name, stretch=3)
        layout.addLayout(row)

        self.osd_items[comp_id] = {"chk": chk, "txt": txt_name}

    def update_aesthetic(self):
        opacity = self.slider_opacity.value()
        max_rows = self.spin_max_rows.value()
        self.lbl_opacity_val.setText(str(opacity))

        self.main_window.osd_window.set_customization(opacity=opacity, max_rows=max_rows)

        conf = global_config.get("osd_config", {})
        conf["opacity"] = opacity
        conf["max_rows"] = max_rows
        global_config["osd_config"] = conf
        save_config(global_config)

    def pick_color(self, target):
        color = QColorDialog.getColor(Qt.white, self, "Seleziona Colore")
        if color.isValid():
            hex_c = color.name()
            conf = global_config.get("osd_config", {})

            # Applica il colore selezionato alla preview quadrata a fianco del bottone
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
            save_config(global_config)

    def pick_font(self):
        current_font = self.main_window.osd_window.custom_font or QFont()
        ok, font = QFontDialog.getFont(current_font, self)
        if ok:
            self.main_window.osd_window.set_customization(font=font)
            self.lbl_current_font.setText(f"Font: {font.family()}")

            conf = global_config.get("osd_config", {})
            conf["font_family"] = font.family()
            conf["font_size"] = font.pointSize()
            conf["font_bold"] = font.bold()
            conf["font_italic"] = font.italic()
            global_config["osd_config"] = conf
            save_config(global_config)

    def save_osd_config(self):
        conf = global_config.get("osd_config", {})
        for comp_id, widgets in self.osd_items.items():
            conf[comp_id] = {
                "enabled": widgets["chk"].isChecked(),
                "custom_name": widgets["txt"].text().strip()
            }
        global_config["osd_config"] = conf
        save_config(global_config)
        QMessageBox.information(self, "OSD", T("osd_saved_msg"))

    def load_osd_config(self):
        conf = global_config.get("osd_config", {})

        for comp_id, widgets in self.osd_items.items():
            saved = conf.get(comp_id, {})
            default_state = True if comp_id.startswith("ch_") else False
            widgets["chk"].setChecked(saved.get("enabled", default_state))
            widgets["txt"].setText(saved.get("custom_name", ""))

        opacity = conf.get("opacity", 220)
        self.slider_opacity.blockSignals(True)
        self.slider_opacity.setValue(opacity)
        self.slider_opacity.blockSignals(False)
        self.lbl_opacity_val.setText(str(opacity))

        max_rows = conf.get("max_rows", 8)
        self.spin_max_rows.blockSignals(True)
        self.spin_max_rows.setValue(max_rows)
        self.spin_max_rows.blockSignals(False)

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
            opacity=opacity,
            c_names=c_names,
            c_values=c_values,
            c_badges=c_badges,
            font=custom_font,
            max_rows=max_rows
        )

class OpenAquaeroUI(QMainWindow):
    """Architettura principale dell'interfaccia utente (Controller Principale)."""
    def __init__(self):
        super().__init__()
        self.engine = AquaeroEngine()
        self.setWindowTitle(T("app_title"))
        self.resize(900, 950) 
        self.updating_combo = False
        self.alarm_triggered = False 

        self.autostart_dir = os.path.expanduser("~/.config/autostart")
        self.desktop_file_path = os.path.join(self.autostart_dir, "openaquaero.desktop")

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("openaquaero", self.style().standardIcon(QStyle.SP_ComputerIcon)))

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

        self.hw_thread = HardwareWorker(self.engine)
        self.hw_thread.telemetry_ready.connect(self.on_telemetry_received)
        self.hw_thread.start()
        self.is_controlling = True

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_h_layout = QHBoxLayout(central_widget)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(70)
        sidebar_container.setStyleSheet("background-color: #11111b; border-right: 2px solid #313244;")

        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 15) 
        sidebar_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet("border: none; outline: none;")

        item_fan = QListWidgetItem("🎛️")
        item_fan.setFont(QFont("Arial", 22))
        item_fan.setTextAlignment(Qt.AlignCenter)
        item_fan.setToolTip(T("sidebar_fan"))

        item_sec = QListWidgetItem("🛡️") # O l'icona che hai scelto
        item_sec.setFont(QFont("Arial", 22))
        item_sec.setTextAlignment(Qt.AlignCenter)
        item_sec.setToolTip(T("sidebar_sec"))
        item_sec.setForeground(QColor("#ff3333"))

        item_osd = QListWidgetItem("🖥️")
        item_osd.setFont(QFont("Arial", 22))
        item_osd.setTextAlignment(Qt.AlignCenter)
        item_osd.setToolTip(T("sidebar_osd"))

        self.sidebar.addItem(item_fan)
        self.sidebar.addItem(item_sec)
        self.sidebar.addItem(item_osd)
        self.sidebar.setCurrentRow(0)

        sidebar_layout.addWidget(self.sidebar)

        self.btn_info_sidebar = QPushButton("ℹ️")
        self.btn_info_sidebar.setFont(QFont("Arial", 20))
        self.btn_info_sidebar.setToolTip("Info & Licenza")
        self.btn_info_sidebar.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #a6adc8; padding: 10px 0; }
            QPushButton:hover { color: #00e5ff; }
            QPushButton:pressed { color: #73f0ff; }
        """)
        self.btn_info_sidebar.clicked.connect(self.show_about_dialog)

        sidebar_layout.addWidget(self.btn_info_sidebar)

        self.stack = QStackedWidget()

        fan_page = QWidget()
        self.main_layout = QVBoxLayout(fan_page)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.build_fan_control_ui()
        self.stack.addWidget(fan_page)

        self.security_tab = SecurityTabWidget()
        self.stack.addWidget(self.security_tab)

        self.osd_tab = OSDConfigTabWidget(self)
        self.stack.addWidget(self.osd_tab)

        main_h_layout.addWidget(sidebar_container)
        main_h_layout.addWidget(self.stack)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)

        self.refresh_profile_list()
        self.combo_profiles.currentIndexChanged.connect(self.load_selected_profile)
        self.load_last_profile()

        self.active_auto_profile = None
        self.pre_auto_profile = None
        self.process_timer = QTimer(self)
        self.process_timer.timeout.connect(self.check_running_processes)
        self.process_timer.start(5000)

        self.dirty_timer = QTimer(self)
        self.dirty_timer.timeout.connect(self.check_dirty_state)
        self.dirty_timer.start(500)

    # --- METODI IPC ---
    def setup_command_server(self):
        self.server = CommandServer(self)
        QLocalServer.removeServer("OpenAquaero_Server")
        self.server.listen("OpenAquaero_Server")
        self.server.command_received.connect(self.handle_external_command)

    def handle_external_command(self, cmd):
        if cmd == "--toggle-osd":
            self.toggle_osd_from_tray()
        elif cmd == "--cycle-position":
            self.cycle_osd_position()

    def cycle_osd_position(self):
        current_pos = global_config["osd_config"].get("position_index", 0)
        new_pos = (current_pos + 1) % 9
        global_config["osd_config"]["position_index"] = new_pos
        save_config(global_config)

        if self.osd_window.isVisible():
            # Il layout manager di Qt muoverà il widget internamente in modo fluido,
            # eliminando del tutto la necessità di fare hide() e show() (Zero Flickering).
            self.update_osd_position(force=True)

    def update_osd_position(self, force=False):
        if not self.osd_window.isVisible() and not force: return

        pos_idx = global_config["osd_config"].get("position_index", 0)

        # Matrice di allineamento Qt: La soluzione definitiva per Wayland/X11.
        # Deleghiamo a Qt l'allineamento del widget interno rispetto alla finestra fullscreen.
        # I margini (10*s) impostati in osd_widget.py verranno rispettati automaticamente,
        # garantendo una distanza dai bordi dello schermo perfetta ed elegante.
        alignments = [
            Qt.AlignTop | Qt.AlignLeft,       # 0
            Qt.AlignTop | Qt.AlignHCenter,    # 1
            Qt.AlignTop | Qt.AlignRight,      # 2
            Qt.AlignVCenter | Qt.AlignLeft,   # 3
            Qt.AlignVCenter | Qt.AlignHCenter,# 4
            Qt.AlignVCenter | Qt.AlignRight,  # 5
            Qt.AlignBottom | Qt.AlignLeft,    # 6
            Qt.AlignBottom | Qt.AlignHCenter, # 7
            Qt.AlignBottom | Qt.AlignRight    # 8
        ]

        screen = QApplication.primaryScreen().geometry()

        # Estendiamo la superficie trasparente sull'intero schermo fisico
        if self.osd_window.geometry() != screen:
            self.osd_window.setGeometry(screen)

        # Riposizioniamo istantaneamente l'interfaccia OSD
        self.osd_window.layout.setAlignment(self.osd_window.bg_widget, alignments[pos_idx])
    # ------------------------------------------

    def build_fan_control_ui(self):
        lbl_main_title = QLabel(T("fan_tab_title"))
        lbl_main_title.setStyleSheet("font-size: 22px; color: #00e5ff; font-weight: bold; margin-bottom: 5px;")
        self.main_layout.addWidget(lbl_main_title)

        top_bar = QHBoxLayout()
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["it", "en", "de", "fr", "es"])
        self.combo_lang.setCurrentText(global_config.get("lang", "it"))
        self.combo_lang.currentTextChanged.connect(self.change_language)

        info_layout.addWidget(self.combo_lang)

        profile_group = QGroupBox(T("profile_group"))
        profile_layout = QHBoxLayout()
        self.combo_profiles = QComboBox()

        self.btn_save_current = QPushButton("💾")
        self.btn_save_current.setToolTip("Salva le modifiche al profilo corrente")
        self.btn_save_current.setFixedWidth(40)
        self.btn_save_current.clicked.connect(self.save_current_profile)

        self.btn_delete_profile = QPushButton("✖")
        self.btn_delete_profile.setToolTip("Elimina il profilo selezionato")
        self.btn_delete_profile.setFixedWidth(40)
        self.btn_delete_profile.clicked.connect(self.delete_current_profile)

        self.txt_new_profile = QLineEdit()
        self.txt_new_profile.setPlaceholderText(T("placeholder"))
        self.btn_save_profile = QPushButton(T("save_btn"))
        self.btn_save_profile.setStyleSheet("background-color: #00e5ff; color: #11111b;")
        self.btn_save_profile.clicked.connect(self.save_new_profile)

        profile_layout.addWidget(self.combo_profiles)
        profile_layout.addWidget(self.btn_save_current)
        profile_layout.addWidget(self.btn_delete_profile)
        profile_layout.addWidget(QLabel("   |   "))
        profile_layout.addWidget(self.txt_new_profile)
        profile_layout.addWidget(self.btn_save_profile)
        profile_group.setLayout(profile_layout)

        top_bar.addWidget(profile_group, stretch=4)
        top_bar.addLayout(info_layout, stretch=1)
        self.main_layout.addLayout(top_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        self.channels_layout = QVBoxLayout(container)
        self.main_layout.addWidget(scroll)

        self.channels = []
        for i in range(1, 5):
            cw = ChannelControlWidget(i, self.engine)
            self.channels_layout.addWidget(cw)
            self.channels.append(cw)

        bottom_controls = QHBoxLayout()
        self.btn_master = QPushButton(T("suspend_btn"))
        self.btn_master.setCheckable(True)
        self.btn_master.setChecked(True)
        # Stato di base coerente con il Verde Acqua principale
        self.btn_master.setStyleSheet("background-color: #00e5ff; color: #11111b; border: none; padding: 12px; font-size: 15px; font-weight: bold; border-radius: 6px;")
        self.btn_master.toggled.connect(self.toggle_master)

        self.chk_autostart = QCheckBox(T("autostart"))
        self.chk_autostart.setStyleSheet("font-size: 13px;")
        self.chk_autostart.setChecked(os.path.exists(self.desktop_file_path))

        self.chk_minimized = QCheckBox(T("start_min"))
        self.chk_minimized.setStyleSheet("font-size: 13px;")
        self.chk_minimized.setChecked(global_config.get("autostart_min", False))
        self.chk_minimized.setEnabled(self.chk_autostart.isChecked())

        self.chk_autostart.toggled.connect(self.on_autostart_toggled)
        self.chk_minimized.toggled.connect(self.toggle_autostart)

        bottom_controls.addWidget(self.btn_master)

        autostart_layout = QVBoxLayout()
        autostart_layout.addWidget(self.chk_autostart)
        autostart_layout.addWidget(self.chk_minimized)

        self.osd_window = AquaeroOSD()
        if global_config.get("osd_export", False):
            self.osd_window.show()
            QTimer.singleShot(100, self.update_osd_position)

        autoswitch_layout = QHBoxLayout()
        # Modificato per collegarsi al dizionario
        self.chk_autoswitch = QCheckBox(T("autoswitch"))
        self.chk_autoswitch.setStyleSheet("font-size: 13px;")
        self.chk_autoswitch.setChecked(global_config.get("autoswitch_enabled", False))
        self.chk_autoswitch.toggled.connect(lambda v: self._save_simple_config("autoswitch_enabled", v))

        self.btn_autoswitch_settings = QPushButton("⚙️")
        self.btn_autoswitch_settings.setFixedWidth(40)
        self.btn_autoswitch_settings.clicked.connect(self.open_autoswitch_settings)

        autoswitch_layout.addWidget(self.chk_autoswitch)
        autoswitch_layout.addWidget(self.btn_autoswitch_settings)
        autoswitch_layout.addStretch()

        autostart_layout.addLayout(autoswitch_layout)

        bottom_controls.addLayout(autostart_layout)
        self.main_layout.addLayout(bottom_controls)

    def check_dirty_state(self):
        """Valuta differenze tra stato hardware in UI e JSON per sbloccare l'azione di salvataggio."""
        p_name = self.combo_profiles.currentText()
        if not p_name or p_name not in global_config["profiles"]:
            return

        if p_name == "Default":
            self.btn_delete_profile.setEnabled(False)
            self.btn_delete_profile.setStyleSheet("background-color: #313244; color: #585b70; font-size: 16px; padding: 5px;")
        else:
            self.btn_delete_profile.setEnabled(True)
            self.btn_delete_profile.setStyleSheet("background-color: #313244; color: #ff3333; font-size: 16px; font-weight: bold; padding: 5px;")

        saved_profile_data = global_config["profiles"][p_name]
        current_profile_data = {}
        for ch in self.channels:
            current_profile_data[str(ch.channel_id)] = ch.get_state()

        current_safe = json.loads(json.dumps(current_profile_data))
        is_dirty = (saved_profile_data != current_safe)

        self.btn_save_current.setEnabled(is_dirty)
        if is_dirty:
            self.btn_save_current.setStyleSheet("background-color: #00e5ff; color: #11111b; font-size: 16px; padding: 5px;")
        else:
            self.btn_save_current.setStyleSheet("background-color: #313244; color: #6c7086; font-size: 16px; padding: 5px;")

    def save_current_profile(self):
        p_name = self.combo_profiles.currentText()
        if not p_name: return
        profile_data = {}
        for ch in self.channels:
            profile_data[str(ch.channel_id)] = ch.get_state()
        global_config["profiles"][p_name] = profile_data
        save_config(global_config)
        self.check_dirty_state()

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
        profile_data = {}
        for ch in self.channels: profile_data[str(ch.channel_id)] = ch.get_state()
        global_config["profiles"][p_name] = profile_data
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

    def change_osd_scale(self, text):
        val = float(text.replace("%", "")) / 100.0
        self._save_simple_config("osd_scale", val)
        self.osd_window.set_scale(val)
        QTimer.singleShot(50, self.update_osd_position)

    def show_about_dialog(self):
        msg = QMessageBox(self)
        msg.setWindowTitle(T("info_btn"))
        msg.setTextFormat(Qt.RichText)
        msg.setText(
            f"<h3>OpenAquaero 2.2</h3>"
            f"<p><b>{T('author_role')}</b> Raffaele Schiavone</p>"
            f"<p><b>Codice:</b> AI assisted by Google Gemini</p>"
            f"<p>Un'alternativa open-source, nativa e leggera per gestire Aquaero 6LT su Linux.</p>"
            f"<hr>"
            f"<p><b>Supporto Hardware:</b> Sviluppato e testato nativamente per <b>Aquacomputer Aquaero 6 LT</b>.<br>"
            f"La compatibilità con modelli Aquaero precedenti non è garantita.</p>"
            f"<hr>"
            f"<p>Rilasciato sotto licenza <b>GNU GPLv3</b>.<br>"
            f"Il software è liberamente modificabile, distribuibile e aperto ai contributi della community.</p>"
        )
        msg.exec()
    def change_language(self, lang):
        if global_config.get("lang") != lang:
            global_config["lang"] = lang
            save_config(global_config)
            reply = QMessageBox.question(self, T("info_btn"), T("lang_prompt"), QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.force_quit_and_restart()
            else:
                QMessageBox.information(self, "Lingua / Language", T("lang_restart"))

    def force_quit_and_restart(self):
        self.hw_thread.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

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
            exec_cmd = "/usr/bin/openaquaero --minimized" if minimized else "/usr/bin/openaquaero"
            desktop_content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Exec={exec_cmd}\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "Name=OpenAquaero\n"
                "Comment=Aquaero Thermal Control\n"
                "Categories=System;HardwareSettings;\n"
            )
            with open(self.desktop_file_path, "w") as f:
                f.write(desktop_content)
            st = os.stat(self.desktop_file_path)
            os.chmod(self.desktop_file_path, st.st_mode | stat.S_IEXEC)
        else:
            if os.path.exists(self.desktop_file_path):
                os.remove(self.desktop_file_path)

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden(): self.showNormal()
            else: self.hide()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("OpenAquaero", T("tray_msg"), QSystemTrayIcon.Information, 2000)

    def force_quit(self):
        self.hw_thread.stop()
        QApplication.quit()

    def toggle_master(self, checked):
        """Sospende le routine di controllo hardware. Alterna gli stili di attività o standby senza layout shift."""
        self.is_controlling = checked
        self.hw_thread.active_control = checked
        if checked:
            self.btn_master.setText(T("suspend_btn"))
            self.btn_master.setStyleSheet("background-color: #00e5ff; color: #11111b; border: none; padding: 12px; font-size: 15px; font-weight: bold; border-radius: 6px;")
        else:
            self.btn_master.setText(T("resume_btn"))
            # Sfondo verde acqua e scritta scura per mantenere assoluta coerenza visiva
            self.btn_master.setStyleSheet("background-color: #00e5ff; color: #11111b; border: none; padding: 12px; font-size: 15px; font-weight: bold; border-radius: 6px;")

    def _save_simple_config(self, key, value):
        global_config[key] = value
        save_config(global_config)

    def open_autoswitch_settings(self):
        dialog = ProcessMappingDialog(self)
        dialog.exec()

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
            self.tray_icon.showMessage("OpenAquaero", T("tray_prof_activated").format(p=p_name), QSystemTrayIcon.Information, 1500)
        else:
            self.updating_combo = False

    def check_running_processes(self):
        if not self.chk_autoswitch.isChecked():
            return

        process_map = global_config.get("process_profiles", {})
        running_target = None
        detected_proc = None

        for proc_name, prof_name in process_map.items():
            try:
                res = subprocess.run(["pgrep", "-f", proc_name], capture_output=True)
                if res.returncode == 0:
                    running_target = prof_name
                    detected_proc = proc_name
                    break
            except Exception:
                pass

        if running_target and self.active_auto_profile != running_target:
            if self.active_auto_profile is None:
                self.pre_auto_profile = self.combo_profiles.currentText()
            self.load_profile_by_name(running_target)
            self.active_auto_profile = running_target
            self.tray_icon.showMessage("Auto-Switch", T("tray_proc_detected").format(proc=detected_proc, prof=running_target), QSystemTrayIcon.Information, 2000)

        elif not running_target and self.active_auto_profile is not None:
            if self.pre_auto_profile:
                self.load_profile_by_name(self.pre_auto_profile)
            self.active_auto_profile = None
            self.tray_icon.showMessage("Auto-Switch", T("tray_proc_ended"), QSystemTrayIcon.Information, 2000)

    def toggle_osd_from_tray(self):
        current_state = self.chk_osd.isChecked()
        self.chk_osd.setChecked(not current_state)

    def toggle_osd(self, checked):
        self._save_simple_config("osd_export", checked)
        if checked:
            self.osd_window.show()
            self.update_osd_position()
        else:
            self.osd_window.hide()

    def check_security_alarms(self, temps, rpms, pwm_commands):
        """Motore iterativo per l'innesco di allarmi critici utente."""
        sec_config = global_config.get("security", {})
        if not sec_config: return

        channels_sec = sec_config.get("channels", {})
        actions_sec = sec_config.get("actions", {})

        alarm_triggered_this_tick = False
        alarm_messages = []

        for ch in self.channels:
            ch_id_str = str(ch.channel_id)
            c_sec = channels_sec.get(ch_id_str, {})

            if c_sec.get("rpm_en"):
                current_rpm = rpms.get(ch.channel_id, 0)
                if current_rpm <= c_sec.get("rpm_val", 0):
                    alarm_triggered_this_tick = True
                    alarm_messages.append(f"Canale {ch_id_str}: RPM critici ({current_rpm} RPM)")

            if c_sec.get("temp_en"):
                sensor_id = ch.combo_sensors.currentData()
                current_temp = temps.get(sensor_id)
                if current_temp is not None and current_temp >= c_sec.get("temp_val", 999):
                    alarm_triggered_this_tick = True
                    alarm_messages.append(f"Canale {ch_id_str}: Temperatura critica ({current_temp:.1f} °C)")

            if c_sec.get("power_en"):
                current_pwm = pwm_commands.get(ch.channel_id, 0)
                current_pwm_percent = int((current_pwm / 255.0) * 100) if current_pwm else 0
                if current_pwm_percent <= c_sec.get("power_val", 0):
                    alarm_triggered_this_tick = True
                    alarm_messages.append(f"Canale {ch_id_str}: Crollo di Potenza ({current_pwm_percent}%)")

        if alarm_triggered_this_tick and not self.alarm_triggered:
            self.alarm_triggered = True

            if actions_sec.get("osd_en") and self.osd_window.isVisible():
                self.osd_window.bg_widget.setStyleSheet(
                    "background-color: rgba(200, 0, 0, 235); border-radius: 12px; border: 3px solid #ffffff;"
                )

            if actions_sec.get("sound_en"):
                default_alarm = "/usr/share/sounds/freedesktop/stereo/suspend-error.oga"
                fallback_alarm = "/usr/share/sounds/freedesktop/stereo/dialog-error.oga"

                if os.path.exists(default_alarm):
                    subprocess.Popen(["paplay", default_alarm])
                elif os.path.exists(fallback_alarm):
                    subprocess.Popen(["paplay", fallback_alarm])
                else:
                    subprocess.Popen(["paplay", "/usr/share/sounds/ocean/stereo/dialog-warning.oga"])

            self.tray_icon.showMessage("🚨 EMERGENZA LOOP 🚨", " | ".join(alarm_messages), QSystemTrayIcon.Critical, 5000)

            if not hasattr(self, 'meltdown_dialog') or not self.meltdown_dialog.isVisible():
                self.meltdown_dialog = MeltdownDialog(alarm_messages, actions_sec, None)
                self.meltdown_dialog.show()

        elif not alarm_triggered_this_tick and self.alarm_triggered:
            self.alarm_triggered = False
            if self.osd_window.isVisible():
                self.osd_window.apply_scaling()

    def on_telemetry_received(self, data):
        temps = data['temps']
        rpms = data['rpms']
        sys_data = data.get('system', {})
        new_pwm_commands = {}
        osd_data = []

        osd_conf = global_config.get("osd_config", {})

        if self.chk_osd.isChecked():
            for s_id, conf in osd_conf.items():
                if s_id.startswith("sys_") and conf.get("enabled"):
                    val = sys_data.get(s_id)
                    if val is not None:
                        custom_name = conf.get("custom_name")
                        default_name = self.engine.sys_sensors_meta.get(s_id, {}).get('label', s_id)
                        name = custom_name if custom_name else default_name
                        
                        s_type = self.engine.sys_sensors_meta.get(s_id, {}).get('type', 'temp')
                        
                        if s_type == 'load':
                            osd_data.append({'name': name, 'pwm': int(val)})
                        else:
                            osd_data.append({'name': name, 'temp': val})

        for ch in self.channels:
            pwm_val = ch.process_telemetry(temps, rpms, self.is_controlling)
            if pwm_val is not None:
                new_pwm_commands[ch.channel_id] = pwm_val

            if self.chk_osd.isChecked():
                ch_id = f"ch_{ch.channel_id}"
                ch_conf = osd_conf.get(ch_id, {"enabled": True, "custom_name": ""})
                
                if ch_conf.get("enabled", True):
                    sensor_id = ch.combo_sensors.currentData()
                    t = temps.get(sensor_id) if sensor_id else 0.0
                    if t is None: t = 0.0
                    r = rpms.get(ch.channel_id, 0)
                    p = int((pwm_val / 255.0) * 100) if pwm_val is not None else 0
                    
                    ch_name = ch_conf.get("custom_name")
                    if not ch_name: ch_name = ch.edit_name.text()
                    
                    osd_data.append({'name': ch_name, 'temp': t, 'rpm': r, 'pwm': p})

        if self.is_controlling:
            self.hw_thread.pwm_commands = new_pwm_commands

        if self.chk_osd.isChecked() and osd_data:
            self.osd_window.update_data(osd_data)
            self.update_osd_position()

        self.check_security_alarms(temps, rpms, new_pwm_commands)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if len(sys.argv) > 1 and sys.argv[1] in ["--toggle-osd", "--cycle-position"]:
        if send_remote_command(sys.argv[1]):
            sys.exit(0)
            
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(MODERN_STYLE)
    win = OpenAquaeroUI()
    win.setup_command_server()

    if "--minimized" not in sys.argv:
        win.show()

    sys.exit(app.exec())
