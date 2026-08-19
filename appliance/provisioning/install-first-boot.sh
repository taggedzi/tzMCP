#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "install-first-boot must run as root" >&2
    exit 1
fi

install -D -m 755 appliance/provisioning/first-boot.sh /usr/local/libexec/tzmcp-first-boot
install -D -m 644 appliance/files/tzmcp-first-boot.service /etc/systemd/system/tzmcp-first-boot.service
install -D -m 644 appliance/files/tzmcp.desktop /usr/share/applications/tzmcp.desktop
systemctl daemon-reload
systemctl enable tzmcp-first-boot.service
