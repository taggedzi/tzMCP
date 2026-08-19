import hashlib
import zipfile

import pytest

from tzMCP.gui_bits.config_manager import Config
from tzMCP.sessions.export import SessionExportError, SessionExporter
from tzMCP.sessions.manager import SessionManager
from tzMCP.sessions.models import SessionState


def _ended_session(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    root = tmp_path / "sessions" / record.session_id
    (root / "capture" / "image.bin").write_bytes(b"image")
    (root / "logs" / "proxy.log").write_text(
        "Authorization: Bearer secret https://example.test/?token=secret\n", encoding="utf-8"
    )
    manager.transition(record.session_id, SessionState.RUNNING)
    manager.transition(record.session_id, SessionState.ENDED)
    return manager, manager.get(record.session_id)


def test_export_is_deterministic_and_manifest_covers_payload(tmp_path):
    manager, record = _ended_session(tmp_path)
    result = SessionExporter(manager.storage).export(record, tmp_path / "exports", {"tzMCP": "test"})
    with zipfile.ZipFile(result.archive_path) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        prefix = record.session_id + "/"
        assert prefix + "capture/image.bin" in names
        assert prefix + "capture-config.yaml" in names
        assert prefix + "session.json" in names
        assert "browser" not in " ".join(names)
        manifest = archive.read("SHA256SUMS").decode("ascii")
        for line in manifest.splitlines():
            expected, name = line.split("  ", 1)
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
        assert b"[REDACTED]" in archive.read(prefix + "logs/proxy.log")
        assert b"secret" not in archive.read(prefix + "logs/proxy.log")


def test_export_rejects_active_session_and_symlinks(tmp_path):
    manager, record = _ended_session(tmp_path)
    active = manager.create_session(Config(save_dir=tmp_path / "unused2"))
    with pytest.raises(SessionExportError, match="ended or interrupted"):
        SessionExporter(manager.storage).export(active, tmp_path / "exports")
    manager._release_active()
    root = tmp_path / "sessions" / record.session_id
    try:
        (root / "capture" / "link").symlink_to(root / "capture" / "image.bin")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(SessionExportError, match="Symlink"):
        SessionExporter(manager.storage).export(record, tmp_path / "exports")
