"""Generate deterministic SHA-256 checksums for release artifacts."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    entries = []
    for artifact in args.artifacts:
        path = artifact.resolve()
        if not path.is_file():
            parser.error(f"artifact is not a regular file: {artifact}")
        if path == output:
            parser.error("checksum output cannot checksum itself")
        entries.append((path.name, digest(path)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(f"{checksum}  {name}\n" for name, checksum in sorted(entries)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
