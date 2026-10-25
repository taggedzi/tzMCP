#!/bin/sh
set -eu

ACCOUNT=tzmcp
install -d -o root -g root -m 755 /opt/tzmcp
if ! id "$ACCOUNT" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash --groups audio,video "$ACCOUNT"
fi
python3.12 -m venv /opt/tzmcp/venv
/opt/tzmcp/venv/bin/pip install --no-cache-dir --upgrade pip
/opt/tzmcp/venv/bin/pip install --no-cache-dir uv==0.13.5
wheel_count=$(find /tmp -maxdepth 1 -type f -name '*.whl' | wc -l)
[ "$wheel_count" -eq 1 ] || { echo "expected exactly one wheel in /tmp" >&2; exit 1; }
wheel_path=$(find /tmp -maxdepth 1 -type f -name '*.whl' -print -quit)
/opt/tzmcp/venv/bin/python -m uv pip install --no-cache \
    --python /opt/tzmcp/venv/bin/python \
    --override /tmp/tzmcp-security-overrides.txt "$wheel_path"
ln -sfn /opt/tzmcp/venv/bin/tzMCP-gui /usr/local/bin/tzmcp-gui
chown -R root:root /opt/tzmcp

# PAM supplies /etc/environment to both the desktop and terminal sessions.
# Keep the image release label available after browser cleanup and GUI restarts.
python3 - <<'PY'
import os
from pathlib import Path
import re

version = os.environ.get('TZMCP_APPLIANCE_VERSION', 'development')
if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,63}', version) is None:
    raise ValueError('Invalid appliance release label')
environment = Path('/etc/environment')
lines = environment.read_text().splitlines() if environment.exists() else []
lines = [line for line in lines if not line.startswith('TZMCP_APPLIANCE_VERSION=')]
lines.append('TZMCP_APPLIANCE_VERSION=' + version)
environment.write_text('\n'.join(lines) + '\n')
PY
