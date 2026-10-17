#!/bin/sh
set -eu

install -D -m 755 /tmp/tzmcp-finalize-image /usr/local/sbin/tzmcp-finalize-image
rm -rf /home/tzmcp-build/.ssh /root/.ssh /tmp/* /var/tmp/*
rm -f /var/lib/tzmcp/.first-boot-complete
rm -rf /var/lib/tzmcp/ca /var/lib/tzmcp/sessions /var/lib/tzmcp/logs /var/lib/tzmcp/runtime
find /home -type f -name '.*history' -delete
rm -f /etc/machine-id
touch /etc/machine-id
apt-get clean
rm -rf /var/lib/apt/lists/*
