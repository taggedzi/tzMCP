#!/bin/sh
set -eu

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    xfce4 xfce4-terminal lightdm lightdm-gtk-greeter \
    xserver-xorg-core xserver-xorg-input-libinput xserver-xorg-video-vmware \
    snapd libnss3-tools python3.12-venv python3-tk \
    virtualbox-guest-utils virtualbox-guest-x11 \
    python3-pip ca-certificates curl sudo util-linux cloud-guest-utils
systemctl set-default graphical.target
systemctl enable lightdm
echo "/usr/sbin/lightdm" > /etc/X11/default-display-manager

# Ubuntu 24.04 supplies Firefox as a Snap. Install it after the base package
# transaction so snapd's seed/watchdog lifecycle cannot make the whole APT
# operation appear to fail without a useful application-level error.
systemctl enable --now snapd.socket snapd.service || true
snap wait system seed.loaded || true
installed=0
attempt=1
while [ "$attempt" -le 3 ]; do
    if snap install firefox; then
        installed=1
        break
    fi
    sleep 10
    attempt=$((attempt + 1))
done
[ "$installed" -eq 1 ] || { echo "Firefox snap installation failed" >&2; snap changes || true; exit 1; }
