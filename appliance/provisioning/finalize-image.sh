#!/bin/sh
set -eu

stop_optional_unit() {
    # Missing server services are expected; a present service failing to stop
    # must still fail finalization so it cannot recreate scrubbed logs.
    if [ "$(systemctl show "$1" --property=LoadState --value)" != not-found ]; then
        systemctl stop "$1"
    fi
}

# This runs asynchronously after Packer's last SSH command has returned so the
# account used by Packer can be deleted without interrupting the provisioner.
if id tzmcp-build >/dev/null 2>&1; then
    pkill -KILL -u tzmcp-build 2>/dev/null || true
    userdel --remove --force tzmcp-build
fi
if getent passwd tzmcp-build >/dev/null; then
    echo "Packer build account remains in the image" >&2
    exit 1
fi
rm -rf /home/tzmcp-build /root/.ssh /root/snap /root/.cache
rm -f /etc/ssh/ssh_host_*
# userdel leaves account-database backups, including the temporary password
# hash. None of these build-time recovery copies belong in a release image.
rm -f /etc/passwd- /etc/shadow- /etc/group- /etc/gshadow- /etc/subuid- /etc/subgid-
rm -f /var/backups/passwd.bak* /var/backups/shadow.bak* \
    /var/backups/group.bak* /var/backups/gshadow.bak*
rm -f /etc/sudoers.d/90-cloud-init-users /root/.vboxclient-*.pid

# The appliance is not a cloud instance. Disable cloud-init before removing
# installer state that can contain the temporary build password hash.
touch /etc/cloud/cloud-init.disabled
rm -rf /var/lib/cloud /var/log/installer
rm -f /var/log/cloud-init.log /var/log/cloud-init-output.log

# Prevent shutdown or socket activation from recreating scrubbed build state.
stop_optional_unit rsyslog.service
systemctl stop syslog.socket 2>/dev/null || true
systemctl stop systemd-update-utmp.service systemd-random-seed.service
# agetty records its exit in wtmp; stop it before clearing the accounting file.
systemctl stop getty@tty1.service
for unit in sysstat.service sysstat-collect.timer sysstat-summary.timer; do
    stop_optional_unit "$unit"
done
# Shutdown can start the runlevel writer again. Runtime masks disappear on
# the appliance's first boot, restoring its normal accounting services.
systemctl mask --runtime getty@tty1.service systemd-update-utmp.service systemd-update-utmp-runlevel.service
systemctl mask --runtime sysstat.service sysstat-collect.service sysstat-summary.service \
    sysstat-collect.timer sysstat-summary.timer
# Close persistent journal files and keep subsequent shutdown messages in /run.
journalctl --relinquish-var
find /var/log -type f -exec truncate --size 0 {} +
find /var/log/journal -mindepth 1 -delete
rm -f /var/lib/systemd/random-seed

rm -f /etc/machine-id
touch /etc/machine-id
rm -f /var/lib/dbus/machine-id
ln -s /etc/machine-id /var/lib/dbus/machine-id
# Deleting credentials does not erase their old filesystem blocks. Overwrite
# free space before export so deleted installer/account data is not shipped.
# Commit the earlier deletes before allocating the fill file so their blocks
# are available for reuse rather than still pending a journal commit.
sync
python3 - <<'PY'
import errno
import os
from pathlib import Path

filler = Path('/var/tmp/tzmcp-zero-fill')
created = False
try:
    with filler.open('xb', buffering=0) as handle:
        created = True
        block = bytes(16 * 1024 * 1024)
        try:
            while True:
                handle.write(block)
        except OSError as exc:
            if exc.errno != errno.ENOSPC:
                raise
        os.sync()
finally:
    if created:
        filler.unlink(missing_ok=True)
        os.sync()
PY
sync
systemctl poweroff
