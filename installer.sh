#!/bin/bash
# AquaControl - Universal Linux Installer (5.0.0)
# Per distro NON-Arch o installazione manuale. Su Arch usare il pacchetto (PKGBUILD).
# Qui, a differenza del PKGBUILD, possiamo agire sul sistema (gruppo, utente, servizi).

if [ "$EUID" -ne 0 ]; then
  echo "ERROR: run this installer as root (e.g. sudo ./installer.sh)"
  exit 1
fi

echo "=> Configuring group and shared state..."
# Gruppo del socket demone <-> GUI/agent e cartella condivisa (root legge, gruppo scrive).
getent group aquacontrol >/dev/null 2>&1 || groupadd -r aquacontrol
install -dm2770 -o root -g aquacontrol /var/lib/aquacontrol

if [ -n "$SUDO_USER" ]; then
    usermod -aG aquacontrol "$SUDO_USER"
    echo "   User '$SUDO_USER' added to the 'aquacontrol' group."
else
    echo "   WARNING: run via sudo to auto-add your user, or add it manually:"
    echo "     sudo usermod -aG aquacontrol YOUR_USERNAME"
fi

echo "=> Removing legacy 4.0.2 configuration..."
# Rete per chi installa la 5.0 senza passare dal vecchio uninstaller: la regola sudoers
# NOPASSWD (il buco chiuso in 5.0) e le vecchie udev 0666 (in 5.0 l'hardware lo tocca solo
# root, e lasciare device scrivibili da tutti sarebbe un declassamento di sicurezza).
rm -f /etc/sudoers.d/99-aquacontrol-shutdown
rm -f /etc/udev/rules.d/99-aquaero.rules

echo "=> Installing files to /usr/lib/aquacontrol..."
# rm preventivo: elimina eventuali moduli di una vecchia installazione manuale (NON tocca
# /var/lib/aquacontrol, dove sta la config).
rm -rf /usr/lib/aquacontrol
install -dm755 /usr/lib/aquacontrol
install -m644 ./*.py /usr/lib/aquacontrol/
cp -r assets /usr/lib/aquacontrol/
find /usr/lib/aquacontrol/assets -type d -exec chmod 755 {} +
find /usr/lib/aquacontrol/assets -type f -exec chmod 644 {} +

echo "=> Installing GUI launcher..."
cat > /usr/bin/aquacontrol <<'EOF'
#!/bin/bash
exec python3 /usr/lib/aquacontrol/main.py "$@"
EOF
chmod 755 /usr/bin/aquacontrol

echo "=> Installing systemd services..."
install -dm755 /etc/systemd/system /etc/systemd/user
# Servizio di SISTEMA (demone root).
cat > /etc/systemd/system/aquacontrold.service <<'EOF'
[Unit]
Description=AquaControl Hardware Daemon (root)
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/lib/aquacontrol/aquacontrold.py
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
EOF

# Servizio UTENTE (agent di sessione). Unita' --user: nessun "User=".
cat > /etc/systemd/user/aquacontrol-agent.service <<'EOF'
[Unit]
Description=AquaControl Session Agent (alarm reaction, login diagnostics)
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/lib/aquacontrol/aquacontrol-agent.py
Restart=on-failure

[Install]
WantedBy=graphical-session.target
EOF

echo "=> Installing desktop entry and icon..."
install -dm755 /usr/share/applications /usr/share/icons/hicolor/512x512/apps
cat > /usr/share/applications/aquacontrol.desktop <<'EOF'
[Desktop Entry]
Name=AquaControl
Comment=Control suite for Aquaero 6 LT and Farbwerk 360
Exec=/usr/bin/aquacontrol
Icon=aquacontrol
Terminal=false
Type=Application
Categories=System;HardwareSettings;
EOF
chmod 644 /usr/share/applications/aquacontrol.desktop
install -m644 aquacontrol.png /usr/share/icons/hicolor/512x512/apps/

echo "=> Enabling services..."
systemctl daemon-reload
# Sistema: subito. Utente: --global lo attiva per ogni utente al prossimo login
# (--now non e' applicabile a --global).
systemctl enable --now aquacontrold.service
systemctl --global enable aquacontrol-agent.service

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1
fi

echo ""
echo "=> Installation complete."
echo "   The group membership and the session agent take effect after a re-login."
echo ""

# Gruppo e servizio --user diventano operativi solo al nuovo login: proponiamo il reboot.
read -r -p "Reboot now to apply everything? [y/N] " ANSWER
case "$ANSWER" in
    [yY]|[yY][eE][sS])
        echo "Rebooting..."
        systemctl reboot
        ;;
    *)
        echo "OK. Please log out and back in (or reboot) later to finish."
        ;;
esac
