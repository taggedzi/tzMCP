"""Allow-list, deterministic ZIP64 session export."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from tzMCP.sessions.models import SessionRecord, SessionState
from tzMCP.sessions.storage import SessionStorage


SENSITIVE_LOG = re.compile(
    r"(?i)(authorization|proxy-authorization|cookie|set-cookie)\s*[:=]\s*[^\r\n]+"
)
SENSITIVE_QUERY = re.compile(r"(?i)([?&](?:token|access_token|api_key|apikey|password|secret)=)[^&#\s]+")


class SessionExportError(RuntimeError):
    """Raised when a session cannot be safely exported."""


@dataclass(frozen=True)
class ExportResult:
    archive_path: Path
    sha256: str
    size: int


def _safe_member(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SessionExportError(f"Unsafe archive member name: {name!r}")
    return path.as_posix()


def sanitize_log(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="replace")
    text = SENSITIVE_LOG.sub(lambda match: f"{match.group(1)}: [REDACTED]", text)
    text = SENSITIVE_QUERY.sub(r"\1[REDACTED]", text)
    return text.encode("utf-8")


class SessionExporter:
    def __init__(self, storage: SessionStorage):
        self.storage = storage

    def _files_under(self, root: Path, member_root: str) -> dict[str, bytes]:
        if not root.exists():
            return {}
        resolved_root = root.resolve()
        payload: dict[str, bytes] = {}
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
            payload[member] = sanitize_log(path.read_bytes()) if member_root.endswith("/logs") else path.read_bytes()
        return payload

    def build_payload(self, record: SessionRecord, versions: dict[str, str] | None = None) -> dict[str, bytes]:
        if record.state not in (SessionState.ENDED, SessionState.INTERRUPTED):
            raise SessionExportError("Only ended or interrupted sessions can be exported")
        session_root = self.storage.session_dir(record.session_id)
        prefix = record.session_id
        payload = self._files_under(session_root / "capture", f"{prefix}/capture")
        payload.update(self._files_under(session_root / "logs", f"{prefix}/logs"))
        config = session_root / "metadata" / "capture-config.yaml"
        if config.is_symlink() or not config.is_file():
            raise SessionExportError("Session configuration snapshot is missing or unsafe")
        config_member = f"{prefix}/capture-config.yaml"
        payload[config_member] = config.read_bytes()
        effective_config = yaml.safe_load(payload[config_member]) or {}
        if isinstance(effective_config, dict):
            effective_config.pop("save_dir", None)
        else:
            effective_config = {}
        session_data: dict[str, Any] = {
            "schema_version": 1,
            "session_id": record.session_id,
            "state": record.state.value,
            "started_at": record.started_at,
            "ended_at": record.ended_at,
            "exported_at": record.exported_at,
            "capture_count": record.capture_count,
            "capture_bytes": record.capture_bytes,
            "warnings": record.warnings,
            "errors": record.errors,
            "versions": versions or {},
            "effective_config": effective_config,
        }
        payload[f"{prefix}/session.json"] = (json.dumps(session_data, indent=2, sort_keys=True) + "\n").encode("utf-8")
        return dict(sorted(payload.items()))

    def export(self, record: SessionRecord, output_dir: Path, versions: dict[str, str] | None = None) -> ExportResult:
        payload = self.build_payload(record, versions)
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        archive = output_dir / f"{record.session_id}.zip"
        if archive.exists():
            raise SessionExportError(f"Export already exists: {archive}")
        hashes = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in payload.items()).encode("ascii")
        member_data = dict(payload)
        member_data["SHA256SUMS"] = hashes
        fd, temporary = tempfile.mkstemp(prefix=f"{record.session_id}.", suffix=".partial", dir=output_dir)
        os.close(fd)
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive_file:
                for name in sorted(member_data):
                    info = zipfile.ZipInfo(name)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.date_time = (1980, 1, 1, 0, 0, 0)
                    archive_file.writestr(info, member_data[name])
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
        return ExportResult(archive, hashlib.sha256(archive.read_bytes()).hexdigest(), archive.stat().st_size)
