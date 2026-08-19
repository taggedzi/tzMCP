#!/bin/sh
set -eu

[ "$(id -u)" -eq 0 ] || { echo "must run as root" >&2; exit 1; }
install -D -m 755 /tmp/tzmcp-export-helper /usr/local/libexec/tzmcp-export-helper
printf '%s\n' 'tzmcp ALL=(root) NOPASSWD: /usr/local/libexec/tzmcp-export-helper *' > /etc/sudoers.d/tzmcp-export
chmod 440 /etc/sudoers.d/tzmcp-export
visudo -cf /etc/sudoers.d/tzmcp-export
