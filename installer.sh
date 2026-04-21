#!/bin/bash
# OpenAquaero - Installatore Universale Linux (v2.2.1)

if [ "$EUID" -ne 0 ]; then
  echo "ERRORE: Per installare OpenAquaero nel sistema, esegui lo script come root (es. sudo ./installer.sh)"
  exit 1
fi

echo "=> Creazione delle directory di sistema..."
mkdir -p /usr/lib/openaquaero
mkdir -p /usr/share/applications
mkdir -p /usr/share/icons/hicolor/512x512/apps

echo "=> Copia dei file sorgente Python in /usr/lib..."
cp engine.py /usr/lib/openaquaero/
cp openaquaero.py /usr/lib/openaquaero/
cp osd_widget.py /usr/lib/openaquaero/
chmod 644 /usr/lib/openaquaero/*.py

echo "=> Creazione dell'eseguibile globale in /usr/bin..."
cat << 'EOF' > /usr/bin/openaquaero
#!/bin/bash
exec python3 /usr/lib/openaquaero/openaquaero.py "$@"
EOF
chmod 755 /usr/bin/openaquaero

echo "=> Generazione dinamica del lanciatore .desktop..."
cat << 'EOF' > /usr/share/applications/openaquaero.desktop
[Desktop Entry]
Name=OpenAquaero
Comment=Software di controllo nativo per Aquaero 6 LT
Exec=/usr/bin/openaquaero
Icon=openaquaero
Terminal=false
Type=Application
Categories=System;HardwareSettings;
EOF
chmod 644 /usr/share/applications/openaquaero.desktop

echo "=> Installazione dell'icona..."
if [ -f "openaquaero.png" ]; then
    cp openaquaero.png /usr/share/icons/hicolor/512x512/apps/openaquaero.png
    chmod 644 /usr/share/icons/hicolor/512x512/apps/openaquaero.png
else
    echo "ATTENZIONE: File openaquaero.png non trovato nella cartella corrente. Icona saltata."
fi

echo "=> Configurazione delle regole udev per i futuri riavvi..."
cat << 'EOF' > /etc/udev/rules.d/99-aquaero.rules
SUBSYSTEM=="hwmon", ACTION=="add", ATTRS{name}=="aquaero", RUN+="/bin/sh -c 'chmod a+w /sys/class/hwmon/%k/pwm*'"
EOF
chmod 644 /etc/udev/rules.d/99-aquaero.rules

echo "=> Applicazione immediata dei permessi hardware..."
AQUAERO_FOUND=0
for hwmon in /sys/class/hwmon/hwmon*; do
    if [ -f "$hwmon/name" ] && grep -q "aquaero" "$hwmon/name"; then
        chmod a+w "$hwmon"/pwm* 2>/dev/null
        echo "   Permessi di scrittura concessi su: $hwmon"
        AQUAERO_FOUND=1
    fi
done

if [ "$AQUAERO_FOUND" -eq 0 ]; then
    echo "   ATTENZIONE: Nessun Aquaero rilevato attualmente nel sistema."
fi

echo "=> Aggiornamento della cache delle icone del Desktop Environment..."
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor > /dev/null 2>&1
fi

echo "=> Installazione completata con successo! OpenAquaero è ora nel tuo menu delle applicazioni."
