"""Read-only post-shutdown VMDK residue audit; decode on the Linux temp drive."""
import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import uuid
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('image', type=Path)
parser.add_argument('report', type=Path)
parser.add_argument('--keep-work', action='store_true', help='Keep generated raw copy for diagnosis')
args = parser.parse_args()
image = args.image.resolve(strict=True)
report_path = args.report.resolve()
if not image.is_file() or report_path.exists() or report_path == image:
    parser.error('Input must be a regular image and report must be a new file')
if os.name != 'posix':
    parser.error('Run this build tool under Linux or WSL')
report_path.parent.mkdir(parents=True, exist_ok=True)
work = Path(tempfile.mkdtemp(prefix="tzmcp-disk-audit-"))
if not args.keep_work:
    atexit.register(shutil.rmtree, work)

def digest_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()

source_digest = digest_file(image)
info = json.loads(subprocess.run(['qemu-img', 'info', '--output=json', str(image)],
                               capture_output=True, text=True, check=True).stdout)
virtual_bytes = info['virtual-size']
if type(virtual_bytes) is not int or not 0 < virtual_bytes <= 128 * 1024**3:
    raise ValueError('Unsupported virtual disk size')
header = work / "header.bin"
subprocess.run(["qemu-img", "dd", "-f", "vmdk", f"if={image}", f"of={header}", "bs=512", "count=64"], check=True)
data = header.read_bytes()
if data[512:520] != b"EFI PART":
    raise ValueError('Expected GPT image')
table_sector = struct.unpack_from("<Q", data, 512 + 72)[0]
count, size = struct.unpack_from("<II", data, 512 + 80)
if not (1 <= count <= 4096 and 128 <= size <= 4096 and table_sector >= 2
        and table_sector * 512 + count * size <= len(data)):
    raise ValueError('Unsupported GPT entry table')
partitions = []
for index in range(count):
    entry = data[table_sector * 512 + index * size:table_sector * 512 + (index + 1) * size]
    if len(entry) < size or not any(entry[:16]):
        continue
    first, last = struct.unpack_from("<QQ", entry, 32)
    if first > last or first < 34 or (last + 1) * 512 > virtual_bytes:
        raise ValueError('GPT partition lies outside the disk data area')
    partitions.append({"type": str(uuid.UUID(bytes_le=entry[:16])), "offset": first * 512, "size": (last - first + 1) * 512})
roots = [p for p in partitions if p["type"] == "0fc63daf-8483-4772-8e79-3d69d8477de4"]
if len(roots) != 1:
    raise ValueError('Expected exactly one Linux filesystem partition')
partition = roots[0]
if shutil.disk_usage(work).free <= partition['size'] + 10 * 1024**3:
    raise OSError('Insufficient temporary space')
filesystem = work / "root.ext4"
opts = {'driver': 'raw', 'offset': partition['offset'], 'size': partition['size'],
        'file': {'driver': 'vmdk', 'file': {'driver': 'file', 'filename': str(image)}}}
convert = ["qemu-img", "convert", "json:" + json.dumps(opts), "-O", "raw"]
subprocess.run([*convert, str(filesystem)], check=True)
def debug(command):
    result = subprocess.run(["debugfs", "-R", command, str(filesystem)], capture_output=True, text=True, check=True)
    return result.stdout
report = {"image": image.name, "image_sha256": source_digest, "partitions": partitions,
          "decoded_filesystem": str(filesystem), "temporary_copy_removed_on_exit": not args.keep_work,
          "checks": {}}
for path in ("/etc/passwd", "/etc/passwd-", "/etc/shadow", "/etc/shadow-", "/etc/group", "/etc/group-", "/etc/gshadow", "/etc/gshadow-", "/var/backups/passwd.bak", "/var/backups/shadow.bak", "/etc/sudoers.d/90-cloud-init-users"):
    content = debug(f"cat {path}")
    report["checks"][path] = {"exists": bool(content), "build_account_present": "tzmcp-build" in content}
for path in ("/home", "/root", "/var/lib/tzmcp", "/var/lib/cloud", "/var/log/installer", "/tmp", "/var/tmp", "/etc/ssh", "/var/log"):
    report["checks"][path] = debug(f"ls -l -p {path}")
report["finalizer_sha256"] = __import__('hashlib').sha256(debug('cat /usr/local/sbin/tzmcp-finalize-image').encode()).hexdigest()
def entries(path):
    for line in debug(f'ls -l -p {path}').splitlines():
        fields = line.split('/')
        if len(fields) >= 7 and fields[1] != '0' and fields[5] not in ('', '.', '..'):
            yield fields
nonempty_logs = {}
def inspect_logs(path):
    for fields in entries(path):
        child = f'{path}/{fields[5]}'
        if fields[2].startswith('04'):
            inspect_logs(child)
        elif fields[2].startswith('10') and int(fields[6] or 0):
            nonempty_logs[child] = int(fields[6])
inspect_logs('/var/log')
report['identity'] = {
    'machine_id_empty': not debug('cat /etc/machine-id').strip(),
    'dbus_id_is_machine_id_symlink': 'Fast link dest: "/etc/machine-id"' in debug('stat /var/lib/dbus/machine-id'),
    'random_seed_absent': not debug('stat /var/lib/systemd/random-seed').strip(),
    'persistent_journal_entries': [f[5] for f in entries('/var/log/journal')],
}
report['nonempty_logs'] = nonempty_logs
def names(path):
    return {f[5] for f in entries(path)}

temporary_dirs = {'.X11-unix', '.ICE-unix', '.font-unix', '.XIM-unix'}
report['pristine_layout'] = {
    'only_runtime_home': names('/home') == {'tzmcp'},
    'runtime_home_is_skeleton': names('/home/tzmcp') <= {'.bashrc', '.bash_logout', '.profile'},
    'root_home_is_skeleton': names('/root') <= {'.bashrc', '.profile', '.bash_logout'},
    'no_runtime_ca_sessions_or_captures': not names('/var/lib/tzmcp'),
    'no_cloud_state': not names('/var/lib/cloud'),
    'no_account_backups': not names('/var/backups'),
    'no_ssh_host_keys': not any(n.startswith('ssh_host_') for n in names('/etc/ssh')),
    'no_temporary_data': names('/tmp') <= temporary_dirs and not names('/var/tmp')
                         and all(not names('/tmp/' + name) for name in temporary_dirs),
}
report['raw_scan_complete'] = False
report_path.write_text(json.dumps(report, indent=2) + '\n')
marker = b'tzmcp-build:'
occurrences = 0
tail = b''
with filesystem.open('rb') as handle:
    while block := handle.read(8 * 1024 * 1024):
        combined = tail + block
        occurrences += combined.count(marker)
        tail = combined[-(len(marker) - 1):]
report["raw_build_account_marker_occurrences"] = occurrences
report['raw_scan_complete'] = True
report['source_unchanged'] = digest_file(image) == source_digest
report['residue_checks_pass'] = (
    occurrences == 0
    and report['source_unchanged']
    and all(report['pristine_layout'].values())
    and not any(value['build_account_present'] for value in report['checks'].values() if isinstance(value, dict))
    and report['identity']['machine_id_empty']
    and report['identity']['dbus_id_is_machine_id_symlink']
    and report['identity']['random_seed_absent']
    and not report['identity']['persistent_journal_entries']
    and not nonempty_logs
)
report_path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"report": str(report_path), "credential_residue": [p for p, value in report["checks"].items() if isinstance(value, dict) and value["build_account_present"]], "raw_build_account_marker_occurrences": occurrences, "filesystem": str(filesystem)}))
raise SystemExit(0 if report['residue_checks_pass'] else 1)
