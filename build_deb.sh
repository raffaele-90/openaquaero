#!/bin/bash
#
# build_deb.sh
# Crea il pacchetto .deb di AquaControl 5.0 (Debian/Ubuntu/Mint).

set -e

PKGNAME="aquacontrol"
PKGVER="5.0.0"
ARCH="all"
BUILD_DIR="${PKGNAME}_${PKGVER}_${ARCH}"

echo "==> Pulizia di build precedenti..."
rm -rf "${BUILD_DIR}"
rm -f "${BUILD_DIR}.deb"

echo "==> Creazione della struttura delle directory..."
mkdir -p "${BUILD_DIR}/usr/lib/${PKGNAME}"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/512x512/apps"
mkdir -p "${BUILD_DIR}/usr/lib/systemd/system"   # servizio di sistema (demone root)
mkdir -p "${BUILD_DIR}/usr/lib/systemd/user"     # servizio utente (agent di sessione)
mkdir -p "${BUILD_DIR}/DEBIAN"

echo "==> Copia dei file sorgenti Python e Assets..."
cp *.py "${BUILD_DIR}/usr/lib/${PKGNAME}/"
cp -r assets "${BUILD_DIR}/usr/lib/${PKGNAME}/"
find "${BUILD_DIR}/usr/lib/${PKGNAME}/assets" -type d -exec chmod 755 {} +
find "${BUILD_DIR}/usr/lib/${PKGNAME}/assets" -type f -exec chmod 644 {} +

echo "==> Generazione del wrapper eseguibile..."
cat << 'EOF' > "${BUILD_DIR}/usr/bin/${PKGNAME}"
#!/bin/bash
exec python3 /usr/lib/aquacontrol/main.py "$@"
EOF
chmod 755 "${BUILD_DIR}/usr/bin/${PKGNAME}"

echo "==> Copia dell'icona..."
cp aquacontrol.png "${BUILD_DIR}/usr/share/icons/hicolor/512x512/apps/"
chmod 644 "${BUILD_DIR}/usr/share/icons/hicolor/512x512/apps/aquacontrol.png"

echo "==> Generazione del file .desktop..."
cat << EOF > "${BUILD_DIR}/usr/share/applications/${PKGNAME}.desktop"
[Desktop Entry]
Name=AquaControl
Comment=Control suite for Aquaero 6 LT and Farbwerk 360
Comment[it]=Suite di controllo per Aquaero 6 LT e Farbwerk 360
Comment[fr]=Suite de contrôle pour Aquaero 6 LT et Farbwerk 360
Comment[es]=Suite de control para Aquaero 6 LT y Farbwerk 360
Comment[de]=Steuerungssuite für Aquaero 6 LT und Farbwerk 360
Comment[ru]=Пакет управления для Aquaero 6 LT и Farbwerk 360
Comment[zh_CN]=Aquaero 6 LT 和 Farbwerk 360 控制套件
Exec=/usr/bin/${PKGNAME}
Icon=${PKGNAME}
Terminal=false
Type=Application
Categories=System;HardwareSettings;
EOF
chmod 644 "${BUILD_DIR}/usr/share/applications/${PKGNAME}.desktop"

echo "==> Generazione del servizio di sistema (demone root)..."
cat << 'EOF' > "${BUILD_DIR}/usr/lib/systemd/system/aquacontrold.service"
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
chmod 644 "${BUILD_DIR}/usr/lib/systemd/system/aquacontrold.service"

echo "==> Generazione del servizio utente (agent)..."
cat << 'EOF' > "${BUILD_DIR}/usr/lib/systemd/user/aquacontrol-agent.service"
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
chmod 644 "${BUILD_DIR}/usr/lib/systemd/user/aquacontrol-agent.service"

echo "==> Generazione del file DEBIAN/control..."

cat << EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PKGNAME}
Version: ${PKGVER}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-hid, python3-pyside6.qtcore, python3-pyside6.qtgui, python3-pyside6.qtwidgets, python3-pyside6.qtdbus
Recommends: pulseaudio-utils
Suggests: python3-pynvml
Maintainer: Raffaele Schiavone <raffaele-90@github.com>
Description: Control suite for Aquaero 6 LT and Farbwerk 360
 AquaControl is a native Linux control suite, written specifically for the
 Aquacomputer ecosystem, programmed around the logic of the Aquaero 6 LT
 and the Farbwerk 360.
EOF
chmod 644 "${BUILD_DIR}/DEBIAN/control"

echo "==> Generazione dello script DEBIAN/postinst..."
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e

# Ambiente condiviso demone(root) <-> GUI/agent(utente): gruppo 'aquacontrol' e
# /var/lib/aquacontrol come root:aquacontrol 2770 (setgid), dove il demone legge e
# GUI/agent scrivono lo stesso file di config, il log e il biglietto d'emergenza.
getent group aquacontrol >/dev/null 2>&1 || groupadd -r aquacontrol
install -dm2770 -o root -g aquacontrol /var/lib/aquacontrol

rm -f /etc/sudoers.d/99-aquacontrol-shutdown
rm -f /etc/udev/rules.d/99-aquaero.rules


if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    usermod -aG aquacontrol "$SUDO_USER" || true
    echo "User '$SUDO_USER' added to the 'aquacontrol' group (log out and back in to apply)."
else
    echo "NOTE: add your user to the 'aquacontrol' group manually, then log out and back in:"
    echo "  sudo usermod -aG aquacontrol YOUR_USERNAME"
fi

if [ -d /run/systemd/system ]; then
    systemctl daemon-reload || true
    systemctl enable --now aquacontrold.service || true
fi
systemctl --global enable aquacontrol-agent.service >/dev/null 2>&1 || true

update-desktop-database /usr/share/applications >/dev/null 2>&1 || true

exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

echo "==> Generazione dello script DEBIAN/prerm..."
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/prerm"
#!/bin/sh
set -e
# Prima della rimozione: ferma e disabilita i servizi.
if [ -d /run/systemd/system ]; then
    systemctl disable --now aquacontrold.service >/dev/null 2>&1 || true
fi
systemctl --global disable aquacontrol-agent.service >/dev/null 2>&1 || true
exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/prerm"

echo "==> Generazione dello script DEBIAN/postrm..."
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postrm"
#!/bin/sh
set -e

if [ "$1" = "purge" ]; then
    rm -rf /var/lib/aquacontrol
    if getent group aquacontrol >/dev/null 2>&1; then
        groupdel aquacontrol >/dev/null 2>&1 || true
    fi
fi
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postrm"

echo "==> Costruzione del pacchetto .deb..."
dpkg-deb --root-owner-group --build "${BUILD_DIR}"

echo "==> Pulizia della directory temporanea..."
rm -rf "${BUILD_DIR}"

echo "==> Completato! Pacchetto generato: ${BUILD_DIR}.deb"
