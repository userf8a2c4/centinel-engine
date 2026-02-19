#!/usr/bin/env python3
"""Build a reproducible evidence bundle for third-party verification."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def merkle_root(hex_hashes: list[str]) -> str:
    if not hex_hashes:
        return hashlib.sha256(b"").hexdigest()
    level = [bytes.fromhex(h) for h in sorted(hex_hashes)]
    while len(level) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            nxt.append(hashlib.sha256(left + right).digest())
        level = nxt
    return level[0].hex()


def build_bundle(input_dir: Path, output_path: Path, include_glob: str = "*.json") -> dict[str, Any]:
    files = sorted(p for p in input_dir.rglob(include_glob) if p.is_file())
    file_entries = []
    hashes = []
    for path in files:
        rel = path.relative_to(input_dir).as_posix()
        digest = sha256_file(path)
        hashes.append(digest)
        file_entries.append({"path": rel, "sha256": digest})

    bundle = {
        "schema_version": "1.0",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "include_glob": include_glob,
        "file_count": len(file_entries),
        "files": file_entries,
        "merkle_root_sha256": merkle_root(hashes),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    return bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a reproducible evidence bundle")
    parser.add_argument("--input-dir", required=True, help="Directory to index")
    parser.add_argument("--output", required=True, help="Output bundle JSON path")
    parser.add_argument("--glob", default="*.json", help="Glob pattern (default: *.json)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = build_bundle(Path(args.input_dir), Path(args.output), args.glob)
    print(f"bundle_created={args.output}")
    print(f"file_count={bundle['file_count']}")
    print(f"merkle_root_sha256={bundle['merkle_root_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
