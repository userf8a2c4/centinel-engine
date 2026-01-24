"""Utilidades para construir payloads de anclaje y hash raíz."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(payload: Any) -> bytes:
    """Serializa JSON en forma canónica para hashing."""
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def hash_bytes(payload: bytes) -> str:
    """Calcula SHA-256 sobre bytes."""
    return hashlib.sha256(payload).hexdigest()


def summarize_value(value: Any) -> dict[str, Any]:
    """Resumen estable de valores complejos para diffs."""
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": len(value),
            "hash": hash_bytes(canonical_json_bytes(value)),
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "hash": hash_bytes(canonical_json_bytes(value)),
        }
    return {"type": type(value).__name__, "value": value}


def build_diff_summary(
    previous_payload: dict[str, Any] | None, current_payload: dict[str, Any]
) -> dict[str, Any]:
    """Genera un resumen de diffs entre snapshots."""
    if previous_payload is None:
        return {"change_count": 0, "changes": []}

    changes: list[dict[str, Any]] = []
    if not isinstance(previous_payload, dict) or not isinstance(current_payload, dict):
        if previous_payload != current_payload:
            changes.append(
                {
                    "path": "$",
                    "before": summarize_value(previous_payload),
                    "after": summarize_value(current_payload),
                }
            )
        return {"change_count": len(changes), "changes": changes}

    keys = sorted(set(previous_payload.keys()) | set(current_payload.keys()))
    for key in keys:
        before = previous_payload.get(key)
        after = current_payload.get(key)
        if before != after:
            changes.append(
                {
                    "path": f"$.{key}",
                    "before": summarize_value(before),
                    "after": summarize_value(after),
                }
            )

    return {"change_count": len(changes), "changes": changes}


def compute_anchor_root(
    snapshot_payload: dict[str, Any],
    diff_summary: dict[str, Any],
    rules_payload: dict[str, Any],
) -> dict[str, str]:
    """Computa hashes raíz y componentes para anclaje."""
    raw_bytes = canonical_json_bytes(snapshot_payload)
    diff_bytes = canonical_json_bytes(diff_summary)
    rules_bytes = canonical_json_bytes(rules_payload)
    root_hash = hash_bytes(raw_bytes + b"|" + diff_bytes + b"|" + rules_bytes)
    return {
        "root_hash": root_hash,
        "raw_hash": hash_bytes(raw_bytes),
        "diffs_hash": hash_bytes(diff_bytes),
        "rules_hash": hash_bytes(rules_bytes),
    }
