#!/usr/bin/env python
"""
Import November 2025 pilot JSONs into Supabase `replay_snapshots`.

Usage:
  python scripts/import_pilot_to_supabase.py [--dir data/pilots/nov-2025] [--dry-run]

Requires env vars:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY

JSONs placed in data/pilots/nov-2025/ are NOT committed to the repo
(.gitignore covers /data/). Run this locally with your pilot data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from centinel.core.rules.common import (
    extract_department,
)


def _get_supabase_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key or "PROYECTO" in url:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars.")
        sys.exit(1)
    try:
        import supabase as sb_pkg
        return sb_pkg.create_client(url, key)
    except ImportError:
        print("ERROR: pip install supabase")
        sys.exit(1)


def _infer_captured_at(path: Path, raw: dict) -> str:
    """Try to extract timestamp from JSON content or filename."""
    for key in ("captura_at", "captured_at", "timestamp", "fecha", "date", "ts"):
        val = raw.get(key)
        if val:
            try:
                return datetime.fromisoformat(str(val).replace("Z", "+00:00")).isoformat()
            except Exception:
                pass
    # Fall back to file mtime
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()


def import_pilots(source_dir: Path, dry_run: bool = False) -> None:
    json_files = sorted(source_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {source_dir}")
        return

    client = None if dry_run else _get_supabase_client()

    inserted = 0
    skipped = 0
    for path in json_files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  SKIP {path.name}: {exc}")
            skipped += 1
            continue

        captured_at = _infer_captured_at(path, raw)
        dept_code = extract_department(raw) or None

        row = {
            "captured_at": captured_at,
            "dept_code": dept_code,
            "raw_json": raw,
            "source": "nov2025",
        }

        if dry_run:
            print(f"  DRY-RUN {path.name}: captured_at={captured_at} dept={dept_code}")
            inserted += 1
            continue

        try:
            result = client.table("replay_snapshots").insert(row).execute()
            if result.data:
                print(f"  OK {path.name}: id={result.data[0].get('id')} dept={dept_code}")
                inserted += 1
            else:
                print(f"  WARN {path.name}: no data returned")
                skipped += 1
        except Exception as exc:
            print(f"  ERROR {path.name}: {exc}")
            skipped += 1

    print(f"\nDone: {inserted} inserted, {skipped} skipped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Nov-2025 pilot JSONs to Supabase replay_snapshots.")
    parser.add_argument("--dir", default="data/pilots/nov-2025", help="Folder with pilot JSONs.")
    parser.add_argument("--dry-run", action="store_true", help="Parse files but do not insert.")
    args = parser.parse_args()

    source_dir = Path(args.dir)
    if not source_dir.exists():
        print(f"Directory not found: {source_dir}")
        sys.exit(1)

    import_pilots(source_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
