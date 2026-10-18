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

# An imported VDI can be expanded before its first boot. Grow only the mounted
# ext4 root partition; never select another disk by enumeration or guesswork.
root_device=$(readlink -f "$(findmnt -n -o SOURCE /)")
root_type=$(findmnt -n -o FSTYPE /)
[ "$root_type" = ext4 ] || { echo "expected ext4 root filesystem" >&2; exit 1; }
[ -b "$root_device" ] || { echo "root is not a block device" >&2; exit 1; }
root_name=${root_device##*/}
partition=$(cat "/sys/class/block/$root_name/partition")
parent=$(lsblk -n -o PKNAME "$root_device")
case "$partition" in ''|*[!0-9]*) echo "invalid root partition" >&2; exit 1 ;; esac
case "$parent" in ''|*[!A-Za-z0-9_-]*) echo "invalid root disk" >&2; exit 1 ;; esac
[ -b "/dev/$parent" ] || { echo "root parent is not a block device" >&2; exit 1; }
if growth=$(growpart "/dev/$parent" "$partition" 2>&1); then
    printf '%s\n' "$growth"
else
    growth_status=$?
    case "$growth_status:$growth" in
        1:NOCHANGE:*) ;; # Already uses the available space.
        *) printf '%s\n' "$growth" >&2; exit "$growth_status" ;;
    esac
fi
resize2fs "$root_device"

install -d -o "$ACCOUNT" -g "$ACCOUNT" -m 700 \
    "$DATA_DIR" "$DATA_DIR/config" "$DATA_DIR/sessions" "$DATA_DIR/runtime" \
    "$DATA_DIR/browser-profiles" \
    "$DATA_DIR/export-ready" "$DATA_DIR/ca" "$CA_DIR" "$LOG_DIR"

if [ ! -s "$CERT" ] || [ ! -s "$KEY" ]; then
    rm -f -- "$CERT" "$KEY"
    runuser -u "$ACCOUNT" -- env \
        TZMCP_APPLIANCE=1 TZMCP_DATA_DIR="$DATA_DIR" \
        timeout 30s /opt/tzmcp/venv/bin/mitmdump -q \
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
