"""Zero-cost external transparency anchoring.

The local hash chain proves *internal consistency* but not *immutability*:
an attacker with disk access can rewrite a snapshot and recompute every
downstream hash. Defeating that requires an anchor the server operator
does not control.

This module provides a zero-cost anchor that needs no paid blockchain,
no infrastructure, and no organization to operate:

  1. Compute a SHA-256 Merkle root over the entire chain of snapshot
     hashes — a single fingerprint of all evidence so far.
  2. Append a signed, timestamped checkpoint to an append-only
     transparency log (`data/transparency/transparency_log.jsonl`).
  3. Optionally stamp the checkpoint with OpenTimestamps, which anchors
     it into the Bitcoin blockchain for free via public calendar servers
     — only if the optional `opentimestamps` package is installed
     (graceful degradation otherwise).

Even without OpenTimestamps the log is valuable: committed to a public
Git repository it inherits Git/GitHub's external, operator-independent
timestamps. A single person with zero budget can run this.

Bilingüe: anclaje de transparencia de costo cero. No requiere blockchain
de pago ni infraestructura; cualquier persona puede operarlo.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..hasher import collect_snapshot_metadata

_LOGGER = logging.getLogger("centinel.transparency")

_DEFAULT_LOG_DIR = Path("data") / "transparency"
_LOG_FILENAME = "transparency_log.jsonl"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_merkle_root(leaf_hashes: List[str]) -> Optional[str]:
    """Compute a SHA-256 Merkle root over ordered leaf hashes.

    Returns None for an empty input. Odd levels duplicate the last node
    (standard Bitcoin-style construction) so the root is deterministic
    and independently reproducible by any auditor.
    """
    if not leaf_hashes:
        return None
    level = [bytes.fromhex(h) for h in leaf_hashes]
    if len(level) == 1:
        return level[0].hex()
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def _resolve_log_dir() -> Path:
    return _DEFAULT_LOG_DIR


def build_transparency_checkpoint(snapshot_root: Path) -> Dict[str, Any]:
    """Build a checkpoint summarizing the entire chain at this moment.

    The checkpoint is deterministic: same chain state produces the same
    merkle_root, so independent mirrors can be compared for divergence.
    """
    entries = collect_snapshot_metadata(snapshot_root)
    leaf_hashes = [e.expected_hash for e in entries]
    merkle_root = compute_merkle_root(leaf_hashes)
    return {
        "version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "chain_length": len(entries),
        "first_hash": leaf_hashes[0] if leaf_hashes else None,
        "last_hash": leaf_hashes[-1] if leaf_hashes else None,
        "merkle_root": merkle_root,
        "merkle_algorithm": "sha256",
    }


def _checkpoint_digest(checkpoint: Dict[str, Any]) -> str:
    """Stable digest of a checkpoint, used as its identity and sign target."""
    signable = {k: v for k, v in sorted(checkpoint.items()) if k != "operator_signature"}
    payload = json.dumps(signable, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha256_hex(payload.encode("utf-8"))


def _maybe_sign(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    """Attach an Ed25519 operator signature if a key is configured.

    Reuses the same custody key as snapshot signing. Signing failure is
    non-fatal for the transparency log itself (the log's value comes from
    being append-only and externally timestamped), but it is recorded.
    """
    try:
        from .custody import sign_hash_record

        signed = sign_hash_record({"checkpoint_digest": _checkpoint_digest(checkpoint)})
        checkpoint["operator_signature"] = signed.get("operator_signature")
    except FileNotFoundError:
        checkpoint["operator_signature"] = None
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("transparency_checkpoint_sign_failed error=%s", exc)
        checkpoint["operator_signature"] = None
    return checkpoint


def _maybe_opentimestamps(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    """Stamp the checkpoint digest into Bitcoin via OpenTimestamps (free).

    Only runs if the optional `opentimestamps` package is installed and
    network egress is permitted. Pure graceful degradation: absence of
    the library or network simply omits the proof — the log still works.
    """
    if os.getenv("CENTINEL_DISABLE_OPENTIMESTAMPS", "").strip().lower() in ("1", "true", "yes"):
        checkpoint["opentimestamps"] = {"status": "disabled_by_env"}
        return checkpoint
    try:
        import opentimestamps  # type: ignore  # noqa: F401
        from opentimestamps.core.timestamp import Timestamp  # type: ignore
        from opentimestamps.calendar import RemoteCalendar  # type: ignore

        digest_hex = _checkpoint_digest(checkpoint)
        timestamp = Timestamp(bytes.fromhex(digest_hex))
        calendar = RemoteCalendar("https://alice.btc.calendar.opentimestamps.org")
        calendar.submit(timestamp.msg)
        checkpoint["opentimestamps"] = {
            "status": "submitted",
            "digest": digest_hex,
            "calendar": "alice.btc.calendar.opentimestamps.org",
        }
    except ImportError:
        checkpoint["opentimestamps"] = {"status": "library_not_installed"}
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("opentimestamps_stamp_failed error=%s", exc)
        checkpoint["opentimestamps"] = {"status": "failed", "error": str(exc)}
    return checkpoint


def append_transparency_checkpoint(
    snapshot_root: Path,
    *,
    log_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build, sign, optionally OTS-stamp, and append a checkpoint.

    The append is durable: the file handle is fsync'd and the parent
    directory is fsync'd so the appended line survives a crash. The log
    is append-only by contract — callers must never rewrite prior lines.
    """
    target_dir = log_dir or _resolve_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / _LOG_FILENAME

    checkpoint = build_transparency_checkpoint(snapshot_root)
    checkpoint = _maybe_sign(checkpoint)
    checkpoint = _maybe_opentimestamps(checkpoint)
    checkpoint["checkpoint_digest"] = _checkpoint_digest(checkpoint)

    line = json.dumps(checkpoint, ensure_ascii=False, sort_keys=True) + "\n"
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    dir_fd = os.open(str(target_dir), os.O_DIRECTORY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)

    _LOGGER.info(
        "transparency_checkpoint_appended chain_length=%s merkle_root=%s ots=%s",
        checkpoint["chain_length"],
        checkpoint["merkle_root"],
        checkpoint.get("opentimestamps", {}).get("status"),
    )
    return checkpoint


def read_transparency_log(log_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read all checkpoints from the append-only transparency log."""
    target_dir = log_dir or _resolve_log_dir()
    log_path = target_dir / _LOG_FILENAME
    if not log_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for raw in log_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            _LOGGER.warning("transparency_log_corrupt_line skipped")
    return out
