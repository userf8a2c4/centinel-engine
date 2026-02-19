#!/usr/bin/env python3
"""One-click external verification for a snapshot bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_structured(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {".json"}:
        return json.loads(path.read_text(encoding="utf-8"))

    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - defensive branch
            raise RuntimeError("PyYAML is required to parse YAML files") from exc
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        return parsed if isinstance(parsed, dict) else {}

    raise ValueError(f"Unsupported metadata format: {path}")


def extract_enabled_rules(payload: dict[str, Any]) -> list[str]:
    rules_payload = payload.get("rules") if isinstance(payload.get("rules"), dict) else payload
    enabled: list[str] = []
    for key, value in rules_payload.items():
        if key == "global_enabled":
            continue
        if isinstance(value, bool) and value:
            enabled.append(key)
        elif isinstance(value, dict) and value.get("enabled") is True:
            enabled.append(key)
    return sorted(enabled)


def verify(
    snapshot_path: Path,
    hash_record_path: Path,
    rules_path: Path,
    pipeline_version: str,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not re.match(r"^[A-Za-z0-9._-]+$", pipeline_version):
        errors.append("invalid_pipeline_version")

    snapshot_sha = sha256_file(snapshot_path)
    hash_record = load_structured(hash_record_path)
    rules_payload = load_structured(rules_path)

    manifest = hash_record.get("manifest", [])
    if not isinstance(manifest, list) or not manifest:
        errors.append("missing_manifest")
    else:
        match = None
        for item in manifest:
            if not isinstance(item, dict):
                continue
            if Path(item.get("file", "")).name == snapshot_path.name:
                match = item
                break
        if not match:
            errors.append("snapshot_not_found_in_manifest")
        elif match.get("sha256") != snapshot_sha:
            errors.append("snapshot_hash_mismatch")

    if not hash_record.get("chained_hash"):
        errors.append("missing_hashchain")

    enabled_rules = extract_enabled_rules(rules_payload)
    if not enabled_rules:
        errors.append("no_enabled_rules")

    declared_pipeline = hash_record.get("pipeline_version")
    if declared_pipeline and declared_pipeline != pipeline_version:
        errors.append("pipeline_version_mismatch")

    return (len(errors) == 0, errors)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify snapshot + hashchain + rules metadata")
    parser.add_argument("--snapshot", required=True, help="Snapshot file path")
    parser.add_argument("--hash-record", required=True, help="Hash record JSON path")
    parser.add_argument("--rules", required=True, help="Rules config JSON/YAML path")
    parser.add_argument("--pipeline-version", required=True, help="Pipeline version identifier")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ok, errors = verify(
        snapshot_path=Path(args.snapshot),
        hash_record_path=Path(args.hash_record),
        rules_path=Path(args.rules),
        pipeline_version=args.pipeline_version,
    )
    if ok:
        print("verification=PASS")
        return 0

    print("verification=FAIL")
    for err in errors:
        print(err)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
