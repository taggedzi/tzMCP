#!/bin/sh
set -eu

ACCOUNT=tzmcp
install -d -o root -g root -m 755 /opt/tzmcp
if ! id "$ACCOUNT" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash --groups audio,video "$ACCOUNT"
fi
python3.12 -m venv /opt/tzmcp/venv
/opt/tzmcp/venv/bin/pip install --no-cache-dir --upgrade pip
wheel_count=$(find /tmp -maxdepth 1 -type f -name '*.whl' | wc -l)
[ "$wheel_count" -eq 1 ] || { echo "expected exactly one wheel in /tmp" >&2; exit 1; }
wheel_path=$(find /tmp -maxdepth 1 -type f -name '*.whl' -print -quit)
/opt/tzmcp/venv/bin/pip install --no-cache-dir "$wheel_path"
ln -sfn /opt/tzmcp/venv/bin/tzmcp-gui /usr/local/bin/tzmcp-gui
chown -R root:root /opt/tzmcp
