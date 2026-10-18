"""Zero unallocated ext4 blocks in a copy of a completed Packer OVF bundle.

Run under Linux/WSL with qemu-img, e2fsck, and zerofree. Live VM disks and
original build artifacts are never modified. Only the appliance's single-disk
GPT layout and Packer OVF references without explicit file sizes are supported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET

OVF = "http://schemas.dmtf.org/ovf/envelope/1"
LINUX_FILESYSTEM = "0fc63daf-8483-4772-8e79-3d69d8477de4"
MARKER = b"tzmcp-build:"
CHUNK_BYTES = 8 * 1024 * 1024


def run_tool(arguments: list[str]) -> str:
    result = subprocess.run(arguments, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{arguments[0]} failed ({result.returncode}): "
                           f"{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(CHUNK_BYTES):
            digest.update(block)
    return digest.hexdigest()


def root_partition(header: bytes, virtual_bytes: int) -> tuple[int, int]:
    if len(header) < 1024 or header[512:520] != b"EFI PART":
        raise ValueError("Expected a GPT disk")
    table = struct.unpack_from("<Q", header, 512 + 72)[0] * 512
    count, entry_bytes = struct.unpack_from("<II", header, 512 + 80)
    if not (1 <= count <= 4096 and 128 <= entry_bytes <= 4096):
        raise ValueError("Unsupported GPT entry table")
    table_end = table + count * entry_bytes
    if table < 1024 or table_end > len(header):
        raise ValueError("GPT table exceeds the inspected header")
    partitions = []
    roots = []
    for index in range(count):
        entry = header[table + index * entry_bytes:table + (index + 1) * entry_bytes]
        if not any(entry[:16]):
            continue
        first, last = struct.unpack_from("<QQ", entry, 32)
        start, end = first * 512, (last + 1) * 512
        if first > last or start < table_end or end > virtual_bytes - 512:
            raise ValueError("GPT partition lies outside the disk data area")
        partitions.append((start, end))
        if str(uuid.UUID(bytes_le=entry[:16])) == LINUX_FILESYSTEM:
            roots.append((start, end - start))
    ordered = sorted(partitions)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        raise ValueError("GPT partitions overlap")
    if len(roots) != 1:
        raise ValueError("Expected exactly one Linux filesystem partition")
    return roots[0]


def copy_bytes(source, target, length: int) -> None:
    remaining = length
    while remaining:
        block = source.read(min(CHUNK_BYTES, remaining))
        if not block:
            raise ValueError("Truncated filesystem image")
        if target.write(block) != len(block):
            raise OSError("Short write while copying filesystem image")
        remaining -= len(block)


def count_markers(path: Path) -> int:
    count, tail = 0, b""
    with path.open("rb") as handle:
        while block := handle.read(CHUNK_BYTES):
            combined = tail + block
            count += combined.count(MARKER)
            tail = combined[-(len(MARKER) - 1):]
    return count


def inspect_bundle(source: Path) -> tuple[Path, Path]:
    ovfs = list(source.glob("*.ovf"))
    disks = list(source.glob("*.vmdk"))
    if len(ovfs) != 1 or len(disks) != 1 or list(source.glob("*.vdi")):
        raise ValueError("Expected a completed single-disk OVF/VMDK bundle")
    ovf, disk = ovfs[0], disks[0]
    if any(path.is_symlink() or not path.is_file() for path in (ovf, disk)):
        raise ValueError("Bundle files must be regular files, not symlinks")
    files = ET.parse(ovf).findall(f"{{{OVF}}}References/{{{OVF}}}File")
    if len(files) != 1 or files[0].get(f"{{{OVF}}}href") != disk.name:
        raise ValueError("OVF must reference only the local VMDK basename")
    if files[0].get(f"{{{OVF}}}size") is not None:
        raise ValueError("Explicit OVF file sizes are unsupported; use Packer's default export")
    return ovf, disk


def sanitize(source: Path, output: Path) -> dict:
    source, output = source.resolve(strict=True), output.resolve()
    if output == source or output.is_relative_to(source) or output.exists():
        raise ValueError("Output must be a new directory outside the source bundle")
    ovf, disk = inspect_bundle(source)
    source_digest = digest_file(disk)
    info = json.loads(run_tool(["qemu-img", "info", "--output=json", str(disk)]))
    virtual_bytes = info["virtual-size"]
    if type(virtual_bytes) is not int or not 0 < virtual_bytes <= 128 * 1024**3:
        raise ValueError("Unsupported virtual disk size")
    if info.get("format") != "vmdk" or info.get("backing-filename"):
        raise ValueError("Expected a self-contained VMDK without a backing file")
    # Both raw files remain on the Linux temp drive, never the repo drive.
    with tempfile.TemporaryDirectory(prefix="tzmcp-sanitize-") as temporary:
        work = Path(temporary)
        if shutil.disk_usage(work).free < 2 * virtual_bytes + 10 * 1024**3:
            raise OSError("Temporary drive needs twice the virtual disk size plus 10 GiB")
        whole, root = work / "disk.raw", work / "root.ext4"
        print("Decoding completed build into temporary raw disk", flush=True)
        run_tool(["qemu-img", "convert", "-f", "vmdk", "-O", "raw", str(disk), str(whole)])
        if whole.stat().st_size != virtual_bytes:
            raise ValueError("Decoded virtual disk size mismatch")
        with whole.open("rb") as handle:
            offset, length = root_partition(handle.read(2 * 1024 * 1024), virtual_bytes)
            handle.seek(offset)
            with root.open("xb") as target:
                copy_bytes(handle, target, length)
                target.flush()
                os.fsync(target.fileno())
        print("Checking and zeroing the unmounted filesystem copy", flush=True)
        run_tool(["e2fsck", "-f", "-n", str(root)])
        run_tool(["zerofree", str(root)])
        run_tool(["e2fsck", "-f", "-n", str(root)])
        with root.open("rb") as handle, whole.open("r+b") as target:
            target.seek(offset)
            copy_bytes(handle, target, length)
            target.flush()
            os.fsync(target.fileno())
        markers = count_markers(whole)
        if markers:
            raise ValueError(f"Sanitized image still contains {markers} build-account markers")
        if digest_file(disk) != source_digest:
            raise ValueError("Source VMDK changed while sanitizing")
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
        sanitized_disk = output / disk.name
        print("Writing and comparing the sanitized streamOptimized VMDK", flush=True)
        run_tool(["qemu-img", "convert", "-f", "raw", "-O", "vmdk",
                  "-o", "subformat=streamOptimized", str(whole), str(sanitized_disk)])
        run_tool(["qemu-img", "compare", "-f", "raw", "-F", "vmdk",
                  str(whole), str(sanitized_disk)])
        shutil.copyfile(ovf, output / ovf.name)
        hashes = {name: digest_file(output / name) for name in (ovf.name, disk.name)}
        manifest = "".join(f"SHA256({name})= {value}\n" for name, value in sorted(hashes.items()))
        (output / ovf.with_suffix(".mf").name).write_text(manifest, encoding="ascii")
        report = {"source_disk": disk.name, "source_sha256": source_digest,
                  "sanitized_sha256": hashes[disk.name], "virtual_bytes": virtual_bytes,
                  "root_offset": offset, "root_bytes": length,
                  "filesystem_checks_passed": True, "raw_build_account_markers": markers,
                  "byte_compare_passed": True,
                  "sanitizer_sha256": digest_file(Path(__file__))}
        (output / "sanitization.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ovf_directory", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("Run this build tool under Linux or WSL")
    for tool in ("qemu-img", "e2fsck", "zerofree"):
        if shutil.which(tool) is None:
            parser.error(f"Required build tool is missing from PATH: {tool}")
    print(json.dumps(sanitize(args.ovf_directory, args.output_directory), indent=2))


if __name__ == "__main__":
    main()
