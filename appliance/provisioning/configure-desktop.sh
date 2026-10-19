#!/bin/sh
set -eu

install -D -m 755 /tmp/tzmcp-first-boot /usr/local/libexec/tzmcp-first-boot
install -D -m 644 /tmp/tzmcp-first-boot.service /etc/systemd/system/tzmcp-first-boot.service
install -D -m 644 /tmp/tzmcp.desktop /usr/share/applications/tzmcp.desktop
install -D -m 644 /tmp/tzmcp.desktop /etc/xdg/autostart/tzmcp.desktop
install -D -m 755 /tmp/tzmcp-display-mode /usr/local/bin/tzmcp-display-mode
install -D -m 644 /tmp/tzmcp-display-mode.desktop /etc/xdg/autostart/tzmcp-display-mode.desktop
install -d -m 755 /etc/lightdm/lightdm.conf.d
printf '%s\n' '[Seat:*]' 'autologin-user=tzmcp' 'user-session=xfce' \
    > /etc/lightdm/lightdm.conf.d/50-tzmcp.conf
# Do not autostart the GUI until storage growth and CA initialization finish.
install -d -m 755 /etc/systemd/system/lightdm.service.d
printf '%s\n' '[Unit]' 'Requires=tzmcp-first-boot.service' 'After=tzmcp-first-boot.service' \
    > /etc/systemd/system/lightdm.service.d/10-tzmcp-first-boot.conf
systemctl daemon-reload
systemctl enable lightdm
systemctl enable tzmcp-first-boot.service
