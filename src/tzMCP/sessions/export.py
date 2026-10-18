"""Allow-list, deterministic ZIP64 session export.

Capture files and logs are streamed in bounded chunks. The archive hash is
also streamed. Small generated metadata may stay in memory.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

import yaml

from tzMCP.sessions.log_sanitizer import StreamingLogSanitizer, sanitize_log
from tzMCP.sessions.models import SessionRecord, SessionState
from tzMCP.sessions.storage import SessionStorage


EXPORT_CHUNK_BYTES = 1024 * 1024
_MANIFEST_NAME = "SHA256SUMS"
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


class SessionExportError(RuntimeError):
    """Raised when a session cannot be safely exported."""


@dataclass(frozen=True)
class ExportResult:
    archive_path: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class _MemoryMember:
    name: str
    data: bytes


@dataclass(frozen=True)
class _FileMember:
    name: str
    path: Path
    sanitize: bool
    size: int


def _safe_member(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SessionExportError(f"Unsafe archive member name: {name!r}")
    return path.as_posix()


def hash_file_sha256(path: Path, chunk_bytes: int | None = None) -> str:
    """Hash a file without reading it all into memory."""
    if chunk_bytes is None:
        chunk_bytes = EXPORT_CHUNK_BYTES
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_bytes)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _zip_info(name: str, file_size: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=_ZIP_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.file_size = file_size
    return info


class SessionExporter:
    def __init__(self, storage: SessionStorage):
        self.storage = storage

    def _file_members(self, root: Path, member_root: str, sanitize: bool) -> list[_FileMember]:
        if not root.exists():
            return []
        resolved_root = root.resolve()
        members: list[_FileMember] = []
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise SessionExportError(f"Symlink is not exportable: {path}")
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SessionExportError(f"Special or multiply-linked file is not exportable: {path}")
            if not path.resolve().is_relative_to(resolved_root):
                raise SessionExportError(f"Path escaped export root: {path}")
            member = _safe_member(f"{member_root}/{relative}")
            members.append(_FileMember(member, path, sanitize, info.st_size))
        return members

    def _collect_members(self, record: SessionRecord, versions: dict[str, str] | None) -> list[_FileMember | _MemoryMember]:
        if record.state not in (SessionState.ENDED, SessionState.INTERRUPTED):
            raise SessionExportError("Only ended or interrupted sessions can be exported")
        session_root = self.storage.session_dir(record.session_id)
        prefix = record.session_id
        members: list[_FileMember | _MemoryMember] = []
        members.extend(self._file_members(session_root / "capture", f"{prefix}/capture", sanitize=False))
        members.extend(self._file_members(session_root / "logs", f"{prefix}/logs", sanitize=True))
        config = session_root / "metadata" / "capture-config.yaml"
        if config.is_symlink() or not config.is_file():
            raise SessionExportError("Session configuration snapshot is missing or unsafe")
        effective_config = yaml.safe_load(config.read_bytes()) or {}
        if isinstance(effective_config, dict):
            effective_config.pop("save_dir", None)
        else:
            effective_config = {}
        # save_dir points into the VM's private session tree. Keep the
        # effective capture rules, but never publish that absolute guest path.
        members.append(
            _MemoryMember(
                f"{prefix}/capture-config.yaml",
                yaml.safe_dump(effective_config, sort_keys=False).encode("utf-8"),
            )
        )
        session_data = {
            "schema_version": 1,
            "session_id": record.session_id,
            "state": record.state.value,
            "started_at": record.started_at,
            "ended_at": record.ended_at,
            "exported_at": record.exported_at,
            "capture_count": record.capture_count,
            "capture_bytes": record.capture_bytes,
            "warnings": record.warnings,
            "errors": [sanitize_log(error.encode("utf-8")).decode("utf-8") for error in record.errors],
            "versions": versions or {},
            "effective_config": effective_config,
        }
        members.append(
            _MemoryMember(
                f"{prefix}/session.json",
                (json.dumps(session_data, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            )
        )
        members.sort(key=lambda member: member.name)
        # Session IDs start with a digit, so every payload name sorts before
        # SHA256SUMS. Hashes can be finalized while those members are written.
        if any(member.name >= _MANIFEST_NAME for member in members):
            raise SessionExportError("Export member name sorts after SHA256SUMS")
        return members

    def export(self, record: SessionRecord, output_dir: Path, versions: dict[str, str] | None = None) -> ExportResult:
        members = self._collect_members(record, versions)
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"{record.session_id}.zip"
        if archive.exists():
            raise SessionExportError(f"Export already exists: {archive}")
        fd, temporary = tempfile.mkstemp(prefix=f"{record.session_id}.", suffix=".partial", dir=output_dir)
        os.close(fd)
        try:
            digests: list[tuple[str, str]] = []
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive_file:
                for member in members:
                    digests.append((member.name, _write_member(archive_file, member)))
                manifest = "".join(f"{digest}  {name}\n" for name, digest in digests).encode("ascii")
                _write_bytes(archive_file, _MANIFEST_NAME, manifest)
            read_fd = os.open(temporary, os.O_RDONLY)
            try:
                try:
                    os.fsync(read_fd)
                except OSError:
                    # Some Windows filesystems reject fsync on a read-only
                    # handle; close and atomically rename still provide the
                    # supported durability boundary there.
                    pass
            finally:
                os.close(read_fd)
            os.replace(temporary, archive)
        except Exception as exc:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise SessionExportError(f"Could not write session export: {exc}") from exc
        return ExportResult(archive, hash_file_sha256(archive), archive.stat().st_size)


def _write_member(archive: zipfile.ZipFile, member: _FileMember | _MemoryMember) -> str:
    if isinstance(member, _MemoryMember):
        return _write_bytes(archive, member.name, member.data)
    return _write_file(archive, member)


def _write_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> str:
    info = _zip_info(name, len(data))
    with archive.open(info, "w", force_zip64=len(data) > zipfile.ZIP64_LIMIT) as dest:
        dest.write(data)
    return hashlib.sha256(data).hexdigest()


def _write_file(archive: zipfile.ZipFile, member: _FileMember) -> str:
    # Sanitized logs change size as they are written. ZIP64 keeps that stream
    # inside the large-archive format even when the raw file looked small.
    force_zip64 = member.sanitize or member.size > zipfile.ZIP64_LIMIT
    declared_size = 0 if member.sanitize else member.size
    info = _zip_info(member.name, declared_size)
    digest = hashlib.sha256()
    with archive.open(info, "w", force_zip64=force_zip64) as dest:
        for chunk in _iter_member_bytes(member):
            dest.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def _iter_member_bytes(member: _FileMember) -> Iterator[bytes]:
    if not member.sanitize:
        with member.path.open("rb") as handle:
            while True:
                chunk = handle.read(EXPORT_CHUNK_BYTES)
                if not chunk:
                    break
                yield chunk
        return
    sanitizer = StreamingLogSanitizer()
    try:
        with member.path.open("rb") as handle:
            while True:
                chunk = handle.read(EXPORT_CHUNK_BYTES)
                if not chunk:
                    break
                yield from sanitizer.iter_feed(chunk)
            yield from sanitizer.iter_finish()
    finally:
        sanitizer.close()
