#!/bin/sh
set -eu

DATA_DIR=${TZMCP_DATA_DIR:-/var/lib/tzmcp}
ACCOUNT=${TZMCP_ACCOUNT:-tzmcp}
CA_DIR="$DATA_DIR/ca/mitmproxy"
CERT="$CA_DIR/mitmproxy-ca-cert.pem"
KEY="$CA_DIR/mitmproxy-ca.pem"
LOG_DIR="$DATA_DIR/logs"

if [ "$(id -u)" -ne 0 ]; then
    echo "first-boot must run as root" >&2
    exit 1
fi
if ! id "$ACCOUNT" >/dev/null 2>&1; then
    echo "missing appliance account: $ACCOUNT" >&2
    exit 1
fi

install -d -o "$ACCOUNT" -g "$ACCOUNT" -m 700 \
    "$DATA_DIR" "$DATA_DIR/config" "$DATA_DIR/sessions" "$DATA_DIR/runtime" \
    "$DATA_DIR/export-ready" "$DATA_DIR/ca" "$CA_DIR" "$LOG_DIR"

if [ ! -s "$CERT" ] || [ ! -s "$KEY" ]; then
    rm -f -- "$CERT" "$KEY"
    runuser -u "$ACCOUNT" -- env \
        TZMCP_APPLIANCE=1 TZMCP_DATA_DIR="$DATA_DIR" \
        timeout 30s mitmdump -q \
        --set "confdir=$CA_DIR" \
        --listen-host 127.0.0.1 --listen-port 18080 \
        >"$LOG_DIR/first-boot-ca.log" 2>&1 &
    proxy_pid=$!
    found=0
    i=0
    while [ "$i" -lt 300 ]; do
        if [ -s "$CERT" ] && [ -s "$KEY" ]; then
            found=1
            break
        fi
        sleep 0.1
        i=$((i + 1))
    done
    kill "$proxy_pid" 2>/dev/null || true
    wait "$proxy_pid" 2>/dev/null || true
    if [ "$found" -ne 1 ]; then
        echo "mitmproxy did not generate its CA" >&2
        exit 1
    fi
fi

chown "$ACCOUNT:$ACCOUNT" "$CERT" "$KEY"
chmod 600 "$CERT" "$KEY"
if [ "$(stat -c '%a' "$CERT")" != "600" ] || [ "$(stat -c '%a' "$KEY")" != "600" ]; then
    echo "CA permissions are not owner-only" >&2
    exit 1
fi

touch "$DATA_DIR/.first-boot-complete"
chown "$ACCOUNT:$ACCOUNT" "$DATA_DIR/.first-boot-complete"
chmod 600 "$DATA_DIR/.first-boot-complete"
