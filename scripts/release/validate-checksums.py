"""Validate a SHA256SUMS file against its adjacent release artifacts."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    base = args.manifest.resolve().parent
    failures = []
    for line_number, line in enumerate(args.manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            failures.append(f"line {line_number}: malformed checksum entry")
            continue
        expected, name = parts
        path = (base / name.lstrip("* ")).resolve()
        if path.parent != base or not path.is_file():
            failures.append(f"line {line_number}: missing or unsafe artifact {name!r}")
        elif sha256(path) != expected.lower():
            failures.append(f"line {line_number}: checksum mismatch for {name!r}")
    if failures:
        parser.error("; ".join(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
