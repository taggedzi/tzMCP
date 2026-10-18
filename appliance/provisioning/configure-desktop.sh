#!/bin/sh
set -eu

install -D -m 755 /tmp/tzmcp-first-boot /usr/local/libexec/tzmcp-first-boot
install -D -m 644 /tmp/tzmcp-first-boot.service /etc/systemd/system/tzmcp-first-boot.service
install -D -m 644 /tmp/tzmcp.desktop /usr/share/applications/tzmcp.desktop
install -D -m 755 /tmp/tzmcp-display-mode /usr/local/bin/tzmcp-display-mode
install -D -m 644 /tmp/tzmcp-display-mode.desktop /etc/xdg/autostart/tzmcp-display-mode.desktop
install -d -m 755 /etc/lightdm/lightdm.conf.d
printf '%s\n' '[Seat:*]' 'autologin-user=tzmcp' 'user-session=xfce' \
    > /etc/lightdm/lightdm.conf.d/50-tzmcp.conf
systemctl daemon-reload
systemctl enable lightdm
systemctl enable tzmcp-first-boot.service
