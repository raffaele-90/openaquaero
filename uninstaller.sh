#!/bin/bash
# AquaControl - Universal Linux Uninstaller (5.0.0)

if [ "$EUID" -ne 0 ]; then
  echo "ERROR: run this uninstaller as root (e.g. sudo ./uninstaller.sh)"
  exit 1
fi

echo "=> Stopping and disabling services..."
systemctl disable --now aquacontrold.service 2>/dev/null || true
systemctl --global disable aquacontrol-agent.service 2>/dev/null || true

echo "=> Removing files..."
rm -rf /usr/lib/aquacontrol
rm -f /usr/bin/aquacontrol
rm -f /etc/systemd/system/aquacontrold.service
rm -f /etc/systemd/user/aquacontrol-agent.service
rm -f /usr/share/applications/aquacontrol.desktop
rm -f /usr/share/icons/hicolor/512x512/apps/aquacontrol.png

echo "=> Reloading system state..."
systemctl daemon-reload
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1
fi

echo ""
echo "=> Uninstall complete."
echo ""

read -r -p "Also remove all configuration and profiles, and the 'aquacontrol' group? [y/N] " ANSWER
case "$ANSWER" in
    [yY]|[yY][eE][sS])
        rm -rf /var/lib/aquacontrol
        groupdel aquacontrol 2>/dev/null || true
        echo "=> Full cleanup done."
        ;;
    *)
        echo "=> Kept your configuration in /var/lib/aquacontrol and the 'aquacontrol' group."
        ;;
esac
