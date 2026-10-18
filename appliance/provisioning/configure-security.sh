#!/bin/sh
set -eu

systemctl disable --now ssh.service ssh.socket || true
systemctl mask ssh.service ssh.socket || true
rm -f /etc/ssh/ssh_host_*
install -d -m 755 /etc/systemd/system/getty@.service.d
# systemd expands $TERM when starting agetty; keep it literal while provisioning.
# shellcheck disable=SC2016
printf '%s\n' '[Service]' 'ExecStart=' 'ExecStart=-/sbin/agetty --autologin tzmcp --noclear %I $TERM' \
    > /etc/systemd/system/getty@.service.d/tzmcp-autologin.conf
