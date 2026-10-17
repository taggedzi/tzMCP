import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
from types import SimpleNamespace
import uuid

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts/release/sanitize-appliance.py"
spec = importlib.util.spec_from_file_location("appliance_sanitizer", SCRIPT)
sanitizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sanitizer)


def _disk():
    image = bytearray(65536)
    image[:12] = b"boot prefix!"
    image[512:520] = b"EFI PART"
    struct.pack_into("<Q", image, 512 + 72, 2)
    struct.pack_into("<II", image, 512 + 80, 1, 128)
    image[1024:1040] = uuid.UUID(sanitizer.LINUX_FILESYSTEM).bytes_le
    struct.pack_into("<QQ", image, 1024 + 32, 16, 31)
    image[8192 + 64:8192 + 81] = b"retained-app-code"
    image[8192 + 1234:8192 + 1234 + len(sanitizer.MARKER)] = sanitizer.MARKER
    image[-8:] = b"GPT tail"
    return bytes(image)


def _bundle(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "disk.vmdk").write_bytes(_disk())
    (source / "appliance.ovf").write_text(
        f'<Envelope xmlns="{sanitizer.OVF}" xmlns:ovf="{sanitizer.OVF}">'
        '<References><File ovf:id="disk" ovf:href="disk.vmdk"/></References></Envelope>'
    )
    return source


def test_partition_bounds_are_validated_before_copying():
    image = _disk()
    assert sanitizer.root_partition(image, len(image)) == (8192, 8192)
    corrupt = bytearray(image)
    struct.pack_into("<QQ", corrupt, 1024 + 32, 16, 9000)
    with pytest.raises(ValueError, match="outside"):
        sanitizer.root_partition(corrupt, len(corrupt))


def test_truncated_filesystem_copy_is_rejected():
    with pytest.raises(ValueError, match="Truncated"):
        sanitizer.copy_bytes(io.BytesIO(b"short"), io.BytesIO(), 100)


def test_bundle_rejects_external_disk_references(tmp_path):
    source = _bundle(tmp_path)
    ovf = source / "appliance.ovf"
    ovf.write_text(ovf.read_text().replace('href="disk.vmdk"', 'href="../private.vmdk"'))
    with pytest.raises(ValueError, match="local VMDK basename"):
        sanitizer.inspect_bundle(source)


def test_sanitization_preserves_source_boot_data_and_live_content(tmp_path, monkeypatch):
    source = _bundle(tmp_path)
    output = tmp_path / "clean"
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    calls = []

    def fake_tool(args):
        calls.append(args)
        if args[:2] == ["qemu-img", "info"]:
            return json.dumps({"format": "vmdk", "virtual-size": len(_disk())})
        if args[:2] == ["qemu-img", "convert"]:
            shutil.copyfile(args[-2], args[-1])
        elif args[0] == "zerofree":
            path = Path(args[-1])
            path.write_bytes(path.read_bytes().replace(sanitizer.MARKER, bytes(len(sanitizer.MARKER))))
        elif args[:2] == ["qemu-img", "compare"]:
            assert Path(args[-2]).read_bytes() == Path(args[-1]).read_bytes()
        return ""

    monkeypatch.setattr(sanitizer, "run_tool", fake_tool)
    monkeypatch.setattr(sanitizer.shutil, "disk_usage", lambda _: SimpleNamespace(free=10**14))
    original_temporary = sanitizer.tempfile.TemporaryDirectory
    monkeypatch.setattr(sanitizer.tempfile, "TemporaryDirectory",
                        lambda **kwargs: original_temporary(dir=tmp_path, **kwargs))

    result = sanitizer.sanitize(source, output)

    assert {p.name: p.read_bytes() for p in source.iterdir()} == before
    expected = _disk().replace(sanitizer.MARKER, bytes(len(sanitizer.MARKER)))
    assert (output / "disk.vmdk").read_bytes() == expected
    assert (output / "appliance.ovf").read_bytes() == before["appliance.ovf"]
    assert result["byte_compare_passed"] and result["raw_build_account_markers"] == 0
    assert len([args for args in calls if args[0] == "e2fsck"]) == 2
    for line in (output / "appliance.mf").read_text().splitlines():
        member, digest = line.removeprefix("SHA256(").split(")= ")
        assert hashlib.sha256((output / member).read_bytes()).hexdigest() == digest


def test_existing_output_is_never_overwritten(tmp_path):
    source = _bundle(tmp_path)
    output = tmp_path / "existing"
    output.mkdir()
    evidence = output / "evidence.txt"
    evidence.write_bytes(b"keep")
    with pytest.raises(ValueError, match="new directory"):
        sanitizer.sanitize(source, output)
    assert evidence.read_bytes() == b"keep"
