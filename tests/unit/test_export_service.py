import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tzMCP.sessions.export_service import ExportService, ExportServiceError


def test_publish_passes_only_controlled_archive_basename(monkeypatch, tmp_path):
    root = tmp_path / "sessions"
    service = ExportService(SimpleNamespace(root=root), helper="/helper")
    export_root = root.parent / "export-ready"
    export_root.mkdir()
    archive = export_root / "20260723T061800Z-aabbccdd.zip"
    archive.write_bytes(b"zip")
    result = SimpleNamespace(archive_path=archive, size=3, sha256="hash")
    calls = []
    monkeypatch.setattr(
        "tzMCP.sessions.export_service.subprocess.run",
        lambda command, **kwargs: (calls.append((command, kwargs)) or SimpleNamespace(returncode=0, stdout=json.dumps({"ok": True}), stderr="")),
    )
    assert service.publish(result)["ok"] is True
    assert calls[0][0] == ["sudo", "/helper", archive.name]


def test_publish_rejects_unsafe_archive_name(tmp_path):
    root = tmp_path / "sessions"
    service = ExportService(SimpleNamespace(root=root), helper="/helper")
    export_root = root.parent / "export-ready"
    export_root.mkdir()
    archive = export_root / "arbitrary.zip"
    archive.write_bytes(b"zip")
    with pytest.raises(ExportServiceError, match="controlled"):
        service.publish(SimpleNamespace(archive_path=archive, size=3, sha256="hash"))


def test_existing_archive_hash_does_not_buffer_the_file(monkeypatch, tmp_path):
    root = tmp_path / "sessions"
    service = ExportService(SimpleNamespace(root=root), helper="/helper")
    export_root = root.parent / "export-ready"
    export_root.mkdir()
    payload = b"zip-bytes" * 3000
    archive = export_root / "20260723T061800Z-aabbccdd.zip"
    archive.write_bytes(payload)
    reads: list[int] = []
    real_open = Path.open

    def tracking_open(self, mode="r", *args, **kwargs):
        handle = real_open(self, mode, *args, **kwargs)
        if self.suffix != ".zip" or "b" not in mode:
            return handle

        class _Tracking:
            def read(self, size=-1):
                if size is None or size < 0:
                    raise AssertionError("unbounded archive read")
                chunk = handle.read(size)
                reads.append(len(chunk))
                return chunk

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                handle.close()
                return False

        return _Tracking()

    def forbid_read_bytes(self, *args, **kwargs):
        raise AssertionError(f"read_bytes used on {self}")

    monkeypatch.setattr(Path, "open", tracking_open)
    monkeypatch.setattr(Path, "read_bytes", forbid_read_bytes)
    monkeypatch.setattr("tzMCP.sessions.export.EXPORT_CHUNK_BYTES", 128)
    record = SimpleNamespace(session_id="20260723T061800Z-aabbccdd")
    result = service.create_local_archive(record)
    assert result.sha256 == hashlib.sha256(payload).hexdigest()
    assert result.size == len(payload)
    assert reads
    assert max(reads) <= 128
