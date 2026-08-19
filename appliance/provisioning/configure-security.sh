#!/bin/sh
set -eu

systemctl disable --now ssh.service || true
systemctl mask ssh.service || true
rm -f /etc/ssh/ssh_host_*
install -d -m 755 /etc/systemd/system/getty@.service.d
printf '%s\n' '[Service]' 'ExecStart=' 'ExecStart=-/sbin/agetty --autologin tzmcp --noclear %I $TERM' \
    > /etc/systemd/system/getty@.service.d/tzmcp-autologin.conf
