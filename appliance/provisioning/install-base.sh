#!/bin/sh
set -eu

export DEBIAN_FRONTEND=noninteractive
apt-get update
# Keep Xfce's file manager, settings, panel, and terminal for inspection and
# troubleshooting. Avoid full desktop/server bundles and recommended extras.
apt-get install -y --no-install-recommends \
    xfce4 xfce4-terminal lightdm lightdm-gtk-greeter \
    xserver-xorg-core xserver-xorg-input-libinput xserver-xorg-video-vmware \
    dbus-x11 x11-xserver-utils fonts-dejavu-core fonts-noto-core \
    ristretto parole mousepad pulseaudio pavucontrol gstreamer1.0-pulseaudio \
    libnss3-tools python3.12-venv python3-tk \
    virtualbox-guest-utils virtualbox-guest-x11 \
    ca-certificates curl gnupg sudo procps util-linux cloud-guest-utils \
    unattended-upgrades
systemctl set-default graphical.target
systemctl enable lightdm
echo "/usr/sbin/lightdm" > /etc/X11/default-display-manager

# Use Mozilla's signed DEB repository so Firefox continues to receive updates
# without bundling Snap's GNOME, Mesa, and theme runtime images.
install -d -m 755 /etc/apt/keyrings
curl --fail --silent --show-error --location \
    https://packages.mozilla.org/apt/repo-signing-key.gpg \
    --output /etc/apt/keyrings/packages.mozilla.org.asc
fingerprint=$(gpg --batch --show-keys --with-colons \
    /etc/apt/keyrings/packages.mozilla.org.asc | awk -F: '$1 == "fpr" {print $10; exit}')
[ "$fingerprint" = 35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3 ] || {
    echo "Mozilla APT signing key fingerprint mismatch" >&2
    exit 1
}
chmod 644 /etc/apt/keyrings/packages.mozilla.org.asc
printf '%s\n' \
    'deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main' \
    > /etc/apt/sources.list.d/mozilla.list
printf '%s\n' \
    'Package: *' 'Pin: origin packages.mozilla.org' 'Pin-Priority: 1000' \
    '' 'Package: firefox' 'Pin: release o=Ubuntu' 'Pin-Priority: -1' \
    > /etc/apt/preferences.d/mozilla
printf '%s\n' \
    'Unattended-Upgrade::Origins-Pattern {' \
    '    "site=packages.mozilla.org";' \
    '};' > /etc/apt/apt.conf.d/52-tzmcp-firefox-updates
apt-get update
apt-get install -y --no-install-recommends firefox
[ -x /usr/lib/firefox/firefox ] || { echo "Mozilla Firefox DEB was not installed" >&2; exit 1; }

# The server installer seeds snapd even though no appliance feature needs it.
if command -v snap >/dev/null 2>&1; then
    snap remove --purge firefox 2>/dev/null || true
fi
apt-get purge -y snapd
