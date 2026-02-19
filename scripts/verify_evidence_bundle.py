#!/usr/bin/env python3
"""Verify evidence bundle integrity and report deterministic pass/fail."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


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


def verify(bundle_path: Path, base_dir: Path) -> tuple[bool, list[str]]:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    hashes: list[str] = []

    for entry in bundle.get("files", []):
        rel = entry["path"]
        expected = entry["sha256"]
        path = base_dir / rel
        if not path.exists():
            errors.append(f"missing_file:{rel}")
            continue
        got = sha256_file(path)
        hashes.append(got)
        if got != expected:
            errors.append(f"hash_mismatch:{rel}")

    if len(bundle.get("files", [])) != bundle.get("file_count"):
        errors.append("file_count_mismatch")

    got_root = merkle_root(hashes)
    if got_root != bundle.get("merkle_root_sha256"):
        errors.append("merkle_root_mismatch")

    return (len(errors) == 0, errors)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a reproducible evidence bundle")
    parser.add_argument("--bundle", required=True, help="Bundle JSON path")
    parser.add_argument("--base-dir", required=True, help="Base directory for files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ok, errors = verify(Path(args.bundle), Path(args.base_dir))
    if ok:
        print("verification=PASS")
        return 0
    print("verification=FAIL")
    for err in errors:
        print(err)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
