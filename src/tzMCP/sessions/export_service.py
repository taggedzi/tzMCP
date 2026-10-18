"""Local archive creation and constrained host-helper coordination."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from tzMCP.sessions.export import ExportResult, SessionExporter, hash_file_sha256
from tzMCP.sessions.models import SessionRecord
from tzMCP.sessions.storage import SessionStorage


ARCHIVE_NAME = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}\.zip$", re.ASCII)


class ExportServiceError(RuntimeError):
    """Raised when local export or helper publication fails."""


class ExportService:
    def __init__(self, storage: SessionStorage, helper: Path | str = "/usr/local/libexec/tzmcp-export-helper"):
        self.exporter = SessionExporter(storage)
        self.export_root = storage.root.parent / "export-ready"
        self.helper = str(helper)

    def create_local_archive(self, record: SessionRecord, versions: dict[str, str] | None = None) -> ExportResult:
        try:
            existing = self.export_root / f"{record.session_id}.zip"
            if existing.is_file():
                return ExportResult(existing, hash_file_sha256(existing), existing.stat().st_size)
            return self.exporter.export(record, self.export_root, versions)
        except Exception as exc:
            raise ExportServiceError(str(exc)) from exc

    def publish(self, result: ExportResult) -> dict[str, object]:
        archive = result.archive_path.resolve()
        if archive.parent != self.export_root.resolve() or not ARCHIVE_NAME.fullmatch(archive.name):
            raise ExportServiceError("Archive is outside the controlled export root")
        completed = subprocess.run(["sudo", self.helper, archive.name], check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise ExportServiceError((completed.stderr or completed.stdout or "Export helper failed").strip())
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ExportServiceError("Export helper returned invalid JSON") from exc
        if response.get("ok") is not True:
            raise ExportServiceError(str(response.get("error", "Export helper reported failure")))
        return response
