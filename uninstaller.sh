#!/bin/bash
# OpenAquaero - Uninstaller Universale Linux

# Controllo privilegi di root
if [ "$EUID" -ne 0 ]; then
  echo "ERRORE: Per disinstallare OpenAquaero, esegui lo script come root (es. sudo ./uninstaller.sh)"
  exit 1
fi

echo "=> Rimozione dei file eseguibili e librerie..."
rm -rf /usr/lib/openaquaero
rm -f /usr/bin/openaquaero

echo "=> Rimozione del lanciatore e dell'icona..."
rm -f /usr/share/applications/openaquaero.desktop
rm -f /usr/share/icons/hicolor/512x512/apps/openaquaero.png

echo "=> Rimozione delle regole udev..."
rm -f /etc/udev/rules.d/99-aquaero.rules

echo "=> Aggiornamento dei demoni di sistema e cache..."
udevadm control --reload-rules
udevadm trigger

if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor > /dev/null 2>&1
fi

echo "=> Disinstallazione di sistema completata!"
echo "Nota: I tuoi profili personali in ~/.config/openaquaero non sono stati eliminati."
