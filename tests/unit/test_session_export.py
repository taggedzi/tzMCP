import hashlib
import json
import os
import random
import zipfile
from pathlib import Path

import pytest

from tzMCP.gui_bits.config_manager import Config
from tzMCP.sessions.export import SessionExportError, SessionExporter
from tzMCP.sessions.export_service import ExportService
from tzMCP.sessions.log_sanitizer import SANITIZER_RAM_LIMIT, StreamingLogSanitizer, sanitize_log
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


def test_exported_capture_config_omits_absolute_guest_save_path(tmp_path):
    manager, record = _ended_session(tmp_path)
    result = SessionExporter(manager.storage).export(record, tmp_path / "exports")

    with zipfile.ZipFile(result.archive_path) as archive:
        config = archive.read(f"{record.session_id}/capture-config.yaml")
        session = archive.read(f"{record.session_id}/session.json")

    assert b"save_dir:" not in config
    assert str(manager.storage.session_dir(record.session_id)).encode() not in config
    assert b"save_dir" not in session
    assert str(manager.storage.session_dir(record.session_id)).encode() not in session


def test_export_sanitizes_session_error_fields(tmp_path):
    manager, record = _ended_session(tmp_path)
    record.errors.append(
        "Proxy failed at https://example.test/?token=secret; Cookie: session=secret"
    )
    manager.storage.write_state(record)

    result = SessionExporter(manager.storage).export(record, tmp_path / "exports")

    with zipfile.ZipFile(result.archive_path) as archive:
        session = json.loads(archive.read(f"{record.session_id}/session.json"))

    assert session["errors"] == [
        "Proxy failed at https://example.test/?token=[REDACTED] Cookie: [REDACTED]"
    ]
    assert "secret" not in str(session["errors"])


def test_failed_host_publication_stays_retryable_after_restart(tmp_path):
    manager, record = _ended_session(tmp_path)
    service = ExportService(manager.storage, helper=tmp_path / "helper")
    archive = service.create_local_archive(record, {"tzMCP": "test"})
    assert not manager.active_path.exists()

    restarted = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    pending = restarted.list_pending_exports()
    assert [item.session_id for item in pending] == [record.session_id]
    assert pending[0].state is SessionState.ENDED
    retry = ExportService(restarted.storage, helper=tmp_path / "helper").create_local_archive(pending[0])

    assert retry.archive_path == archive.archive_path
    assert retry.sha256 == archive.sha256
    assert retry.archive_path.read_bytes() == archive.archive_path.read_bytes()
    restarted.complete_export(record.session_id, retry.archive_path.name, retry.size, retry.sha256)
    assert restarted.list_pending_exports() == []
    follow_up = restarted.create_session(Config(save_dir=tmp_path / "unused"))
    assert follow_up.state is SessionState.NEW


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


def _sanitize_stream(data: bytes, parts: list[bytes]) -> bytes:
    sanitizer = StreamingLogSanitizer()
    try:
        pieces = [part for chunk in parts for part in sanitizer.iter_feed(chunk)]
        pieces.extend(sanitizer.iter_finish())
    finally:
        sanitizer.close()
    return b"".join(pieces)


def _chunkings(data: bytes) -> list[list[bytes]]:
    splits = [[data]]
    if not data:
        return splits
    if len(data) <= 48:
        splits.append([data[index : index + 1] for index in range(len(data))])
        for cut in range(len(data) + 1):
            splits.append([piece for piece in (data[:cut], data[cut:]) if piece])
    else:
        for size in (1, 3, 7, 64):
            splits.append([data[index : index + size] for index in range(0, len(data), size)])
    return splits


def test_streaming_log_sanitizer_matches_full_buffer():
    samples = [
        b"",
        b"plain line\n",
        b"Authorization: Bearer secret https://example.test/?token=secret\n",
        b"Cookie:\n",
        b"Cookie: \n",
        b"Cookie: a\n",
        b"cookie\n: secret\n",
        b"cookie: \nsecret\n",
        b"cookie \n : x\n",
        b"set-cookie: secret\n",
        b"proxy-authorization: secret\n",
        b"AuThOrIzAtIoN: secret\n",
        b"Proxy failed at https://example.test/?token=secret; Cookie: session=secret",
        b"?token=abc&secret=def\n",
        b"?access_token=abc\n",
        b"?token=cookie:secret",
        b"cookie: ?token=abc\n",
        b"prefix ?token=abc suffix\n",
        "cookie: café\n".encode(),
        b"cookie: \xffsecret\n",
        b"cookie   =   secret\n",
        b"see cookie:\tsecret\r\nnext\n",
        b"notcookie\n: z",
        b"authorization",
        b"proxy-authorizat",
        b"proxy-authorization\nx\n",
        b"set-cookie\nx\n",
        "?apı_key=SECRET\n".encode(),
        "?apİ_key=SECRET\n".encode(),
        "&ſecret=SECRET\n".encode(),
        b"?tok",
        b"?token=",
    ]
    rng = random.Random(25)
    alphabet = "abc \t\r\n?&=:#Authorizationcookieset-proxy"
    for _ in range(20):
        samples.append("".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120))).encode())
        samples.append(bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 40))))
    for data in samples:
        expected = sanitize_log(data)
        for parts in _chunkings(data):
            assert _sanitize_stream(data, parts) == expected


def test_streaming_log_sanitizer_seeded_differential(monkeypatch):
    # Small buffers exercise spool rollover without large fixtures. Keep the
    # seed and failing input in the assertion so failures are reproducible.
    monkeypatch.setattr("tzMCP.sessions.log_sanitizer.SANITIZER_RAM_LIMIT", 64)
    rng = random.Random(17)
    tokens = [
        "cookie", "authorization", "set-cookie", "proxy-authorization",
        " " * 80, "\n" * 90, "\n", "\r", ":", "=", "x", "\t",
        "?token=", "&secret=", "?apı_key=", "?apİ_key=", "&ſecret=", "é",
    ]
    for case in range(1000):
        data = "".join(rng.choices(tokens, k=rng.randrange(1, 25))).encode()
        size = rng.randrange(1, 200)
        parts = [data[index : index + size] for index in range(0, len(data), size)]
        assert _sanitize_stream(data, parts) == sanitize_log(data), (
            f"seed=17 case={case} chunk_size={size} input={data!r}"
        )


def _assert_bounded_stream(data: bytes) -> None:
    sanitizer = StreamingLogSanitizer()
    try:
        pieces = []
        for index in range(0, len(data), 4096):
            pieces.extend(sanitizer.iter_feed(data[index : index + 4096]))
        pieces.extend(sanitizer.iter_finish())
    finally:
        sanitizer.close()
    assert b"".join(pieces) == sanitize_log(data)
    # The two stages do not retain the whole input. A full-buffer bug is far above this cap.
    assert sanitizer.peak_buffered_chars <= SANITIZER_RAM_LIMIT * 2 + 128


def test_streaming_log_sanitizer_bounds_memory_across_chunk_gaps():
    secret = b"A" * (SANITIZER_RAM_LIMIT * 3)
    gap = b" " * (SANITIZER_RAM_LIMIT + 128)
    _assert_bounded_stream(b"Authorization: Bearer " + secret + b"\nnext ?token=" + secret + b" end\n")
    _assert_bounded_stream(b"cookie" + gap + b": secret\n")
    _assert_bounded_stream(b"cookie" + gap + b"x\n")
    _assert_bounded_stream(b"cookie" + gap)
    _assert_bounded_stream(b"cookie:" + gap)
    _assert_bounded_stream(b"cookie:" + b"\n" * (SANITIZER_RAM_LIMIT + 32) + b"secret\n")
    _assert_bounded_stream(b"cookie: " + b"\n" * (SANITIZER_RAM_LIMIT + 32))


def _assert_chunked_stream(data: bytes, cuts: tuple[int, ...] = ()) -> None:
    """Match sanitize_log across chunk sizes and explicit boundary cuts."""
    expected = sanitize_log(data)
    parts_list = [[data]]
    # Small sizes still split multibyte characters. 3-byte steps across a full
    # RAM-sized gap copy the pending buffer often enough to dominate the suite.
    for size in (64, 1024, 4096):
        parts_list.append([data[index : index + size] for index in range(0, len(data), size)])
    for cut in cuts:
        if 0 < cut < len(data):
            parts_list.append([data[:cut], data[cut:]])
            parts_list.append([data[: cut - 1], data[cut - 1 : cut], data[cut:]])
    for parts in parts_list:
        assert _sanitize_stream(data, parts) == expected
    _assert_bounded_stream(data)


def test_streaming_query_unicode_case_holds_at_buffer_boundary():
    # Dotless ı, capital İ, and long s are case-equivalents under (?i), not str.lower().
    edge = b"x" * (SANITIZER_RAM_LIMIT - 4)
    samples = [
        edge + "?apı_key=SECRET\n".encode(),
        edge + "?apİ_key=SECRET\n".encode(),
        edge + "&ſecret=SECRET\n".encode(),
        edge + "?token=apı_key&ſecret=SECRET\n".encode(),
    ]
    for data in samples:
        secret_at = data.rfind(b"SECRET")
        assert secret_at > SANITIZER_RAM_LIMIT
        _assert_chunked_stream(data, cuts=(SANITIZER_RAM_LIMIT - 4, SANITIZER_RAM_LIMIT, secret_at))
        assert b"SECRET" not in sanitize_log(data)


def test_streaming_nested_keyword_replay_keeps_following_records():
    newline_gap = b"\n" * (SANITIZER_RAM_LIMIT + 100)
    space_gap = b" " * (SANITIZER_RAM_LIMIT + 100)
    audit = b"x\nIMPORTANT AUDIT EVENT\n"
    samples = [
        b"proxy-authorization" + newline_gap + audit,
        b"set-cookie" + newline_gap + audit,
        b"proxy-authorization" + space_gap + audit,
        b"set-cookie" + space_gap + b"x\nCookie: SECRET\nIMPORTANT AUDIT EVENT\n",
        b"proxy-authorization" + newline_gap + b"x\nAuthorization: SECRET\nIMPORTANT AUDIT EVENT\n",
        b"x" * (SANITIZER_RAM_LIMIT - 4)
        + "?apı_key=SECRET\n".encode()
        + b"proxy-authorization"
        + newline_gap
        + b"set-cookie"
        + space_gap
        + "?apİ_key=SECRET&ſecret=HIDDEN\nIMPORTANT AUDIT EVENT\n".encode(),
    ]
    for data in samples:
        assert b"IMPORTANT AUDIT EVENT" in sanitize_log(data)
        keyword_end = data.find(b"\n") if data.startswith(b"proxy-") or data.startswith(b"set-") else SANITIZER_RAM_LIMIT
        _assert_chunked_stream(data, cuts=(keyword_end, SANITIZER_RAM_LIMIT, len(data) - 24))


def test_export_streams_media_and_archive_hash(monkeypatch, tmp_path):
    manager, record = _ended_session(tmp_path)
    root = tmp_path / "sessions" / record.session_id
    payload = b"frame-" * 20000
    (root / "capture" / "image.bin").write_bytes(payload)
    log = b"before Authorization: super-secret-token\nplain\n"
    (root / "logs" / "proxy.log").write_bytes(log)
    reads: list[int] = []
    real_open = Path.open
    real_read_bytes = Path.read_bytes

    def tracking_open(self, mode="r", *args, **kwargs):
        handle = real_open(self, mode, *args, **kwargs)
        if "b" not in mode or self.name not in {"image.bin", "proxy.log"}:
            return handle

        class _Tracking:
            def read(self, size=-1):
                if size is None or size < 0:
                    raise AssertionError(f"unbounded read of {self}")
                chunk = handle.read(size)
                reads.append(len(chunk))
                return chunk

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                handle.close()
                return False

        return _Tracking()

    def guarded_read_bytes(self, *args, **kwargs):
        if self.suffix == ".zip" or "capture" in self.parts or self.suffix == ".log":
            raise AssertionError(f"read_bytes used on {self}")
        return real_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracking_open)
    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr("tzMCP.sessions.export.EXPORT_CHUNK_BYTES", 1024)

    import tzMCP.sessions.export as export_module

    result = SessionExporter(manager.storage).export(record, tmp_path / "exports", {"tzMCP": "test"})
    assert reads, "capture and log were not streamed"
    assert max(reads) <= 1024
    assert sum(size for size in reads if size) >= len(payload)
    with zipfile.ZipFile(result.archive_path) as archive:
        assert archive.read(f"{record.session_id}/capture/image.bin") == payload
        redacted = archive.read(f"{record.session_id}/logs/proxy.log")
        assert b"super-secret-token" not in redacted
        assert b"Authorization: [REDACTED]" in redacted
        manifest = archive.read("SHA256SUMS").decode("ascii")
        for line in manifest.splitlines():
            expected, name = line.split("  ", 1)
            assert name != "SHA256SUMS"
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
    assert result.sha256 == export_module.hash_file_sha256(result.archive_path, chunk_bytes=1024)
    assert result.size == result.archive_path.stat().st_size


def test_repeated_export_is_deterministic(tmp_path):
    manager, record = _ended_session(tmp_path)
    exporter = SessionExporter(manager.storage)
    first = exporter.export(record, tmp_path / "one")
    second = exporter.export(record, tmp_path / "two")
    assert first.sha256 == second.sha256
    assert first.size == second.size
    assert first.archive_path.read_bytes() == second.archive_path.read_bytes()


def test_existing_archive_is_not_replaced(tmp_path):
    manager, record = _ended_session(tmp_path)
    exporter = SessionExporter(manager.storage)
    first = exporter.export(record, tmp_path / "exports")
    snapshot = first.archive_path.read_bytes()
    capture = tmp_path / "sessions" / record.session_id / "capture" / "image.bin"
    original = capture.read_bytes()
    with pytest.raises(SessionExportError, match="already exists"):
        exporter.export(record, tmp_path / "exports")
    assert first.archive_path.read_bytes() == snapshot
    assert capture.read_bytes() == original


def test_read_failure_removes_partial_and_keeps_sources(monkeypatch, tmp_path):
    manager, record = _ended_session(tmp_path)
    capture = tmp_path / "sessions" / record.session_id / "capture" / "image.bin"
    capture.write_bytes(b"image-data-that-crosses-a-chunk-boundary")
    original = capture.read_bytes()
    exports = tmp_path / "exports"
    exports.mkdir()
    prior = exports / "earlier-session.zip"
    prior.write_bytes(b"prior-archive")
    monkeypatch.setattr("tzMCP.sessions.export.EXPORT_CHUNK_BYTES", 8)
    real_open = Path.open

    def failing_open(self, mode="r", *args, **kwargs):
        handle = real_open(self, mode, *args, **kwargs)
        if self.name != "image.bin" or "b" not in mode:
            return handle

        class _FailAfter:
            def __init__(self):
                self._reads = 0

            def read(self, size=-1):
                self._reads += 1
                if self._reads > 1:
                    raise OSError("simulated read failure")
                return handle.read(size)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                handle.close()
                return False

        return _FailAfter()

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(SessionExportError, match="Could not write session export"):
        SessionExporter(manager.storage).export(record, exports)
    assert capture.read_bytes() == original
    assert prior.read_bytes() == b"prior-archive"
    assert list(exports.glob("*.partial")) == []
    assert not (exports / f"{record.session_id}.zip").exists()


def test_publish_failure_removes_partial_and_keeps_sources(monkeypatch, tmp_path):
    manager, record = _ended_session(tmp_path)
    capture = tmp_path / "sessions" / record.session_id / "capture" / "image.bin"
    original = capture.read_bytes()
    exports = tmp_path / "exports"

    def fail_replace(*_args, **_kwargs):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("tzMCP.sessions.export.os.replace", fail_replace)
    with pytest.raises(SessionExportError, match="simulated replace failure"):
        SessionExporter(manager.storage).export(record, exports)
    assert capture.read_bytes() == original
    assert list(exports.glob("*.partial")) == []
    assert not (exports / f"{record.session_id}.zip").exists()
