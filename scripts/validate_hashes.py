"""Validación end-to-end de cadenas de hash.

Uso básico:
    python -m scripts.validate_hashes
    python -m scripts.validate_hashes --hashes-dir hashes --data-dir data
    python -m scripts.validate_hashes --sqlite-path reports/irreversibility_state.db
    python -m scripts.validate_hashes --anchor-hash <hash_anclado>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from centinel.paths import iter_all_hashes
from centinel.core.hashchain import compute_hash


@dataclass
class HashEntry:
    """Español: Clase HashEntry del módulo scripts/validate_hashes.py.

    English: HashEntry class defined in scripts/validate_hashes.py.
    """

    name: str
    stored_hash: str
    stored_current_hash: str | None = None
    source_dir: str | None = None


@dataclass
class ValidationResult:
    """Español: Clase ValidationResult del módulo scripts/validate_hashes.py.

    English: ValidationResult class defined in scripts/validate_hashes.py.
    """

    ok: bool
    error_snapshot: str | None = None
    root_hash: str | None = None


@dataclass
class AnchorResult:
    """Español: Clase AnchorResult del módulo scripts/validate_hashes.py.

    English: AnchorResult class defined in scripts/validate_hashes.py.
    """

    ok: bool
    message: str


def _load_hash_entries(hashes_dir: Path) -> list[HashEntry]:
    """Español: Carga entradas de hash desde subdirectorios por fuente.

    English: Load hash entries from per-source subdirectories.
    """
    entries: list[HashEntry] = []
    hash_files = iter_all_hashes(hash_root=hashes_dir)
    for hash_file in hash_files:
        raw = hash_file.read_text(encoding="utf-8").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None

        source_dir = hash_file.parent.name

        if isinstance(payload, dict):
            chained = payload.get("chained_hash") or payload.get("hash")
            current = payload.get("hash") if payload.get("chained_hash") else None
            if chained:
                entries.append(
                    HashEntry(
                        name=hash_file.stem,
                        stored_hash=str(chained),
                        stored_current_hash=str(current) if current else None,
                        source_dir=source_dir,
                    )
                )
            continue

        if raw:
            entries.append(HashEntry(name=hash_file.stem, stored_hash=raw, source_dir=source_dir))
    return entries


def _canonical_json(snapshot_path: Path) -> str:
    """Español: Función _canonical_json del módulo scripts/validate_hashes.py.

    English: Function _canonical_json defined in scripts/validate_hashes.py.
    """
    text = snapshot_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_hash_dir(hashes_dir: Path, data_dir: Path) -> ValidationResult:
    """Español: Función _validate_hash_dir del módulo scripts/validate_hashes.py.

    English: Function _validate_hash_dir defined in scripts/validate_hashes.py.
    """
    entries = _load_hash_entries(hashes_dir)
    if not entries:
        return ValidationResult(ok=False, error_snapshot="sin_hashes")

    from centinel.paths import SNAPSHOTS_SUBDIR

    previous_hash: str | None = None
    for entry in entries:
        source_dir = entry.source_dir or ""
        snapshot_path = data_dir / SNAPSHOTS_SUBDIR / source_dir / f"{entry.name}.json"
        if not snapshot_path.exists():
            return ValidationResult(ok=False, error_snapshot=entry.name)
        canonical_json = _canonical_json(snapshot_path)
        current_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        chained_hash = compute_hash(canonical_json, previous_hash)

        if entry.stored_current_hash and entry.stored_current_hash != current_hash:
            return ValidationResult(ok=False, error_snapshot=entry.name)

        if entry.stored_hash != chained_hash:
            return ValidationResult(ok=False, error_snapshot=entry.name)

        previous_hash = chained_hash

    return ValidationResult(ok=True, root_hash=previous_hash)


def _iter_sqlite_entries(connection: sqlite3.Connection) -> Iterable[dict]:
    """Español: Función _iter_sqlite_entries del módulo scripts/validate_hashes.py.

    English: Function _iter_sqlite_entries defined in scripts/validate_hashes.py.
    """
    return connection.execute("""
        SELECT department_code, timestamp_utc, table_name, hash, previous_hash
        FROM snapshot_index
        ORDER BY department_code, timestamp_utc
        """).fetchall()


def _load_canonical_snapshot(connection: sqlite3.Connection, table_name: str, snapshot_hash: str) -> str | None:
    """Español: Función _load_canonical_snapshot del módulo scripts/validate_hashes.py.

    English: Function _load_canonical_snapshot defined in scripts/validate_hashes.py.
    """
    row = connection.execute(
        f"SELECT canonical_json FROM {table_name} WHERE hash = ? LIMIT 1",  # nosec B608
        (snapshot_hash,),
    ).fetchone()
    if not row:
        return None
    return row["canonical_json"]


def _validate_sqlite(sqlite_path: Path) -> ValidationResult:
    """Español: Función _validate_sqlite del módulo scripts/validate_hashes.py.

    English: Function _validate_sqlite defined in scripts/validate_hashes.py.
    """
    if not sqlite_path.exists():
        return ValidationResult(ok=False, error_snapshot="sqlite_missing")

    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row

    previous_by_department: dict[str, str | None] = {}
    latest_hash: str | None = None

    try:
        for row in _iter_sqlite_entries(connection):
            department_code = row["department_code"]
            snapshot_hash = row["hash"]
            previous_hash = row["previous_hash"]
            table_name = row["table_name"]

            expected_previous = previous_by_department.get(department_code)
            if expected_previous != previous_hash:
                return ValidationResult(ok=False, error_snapshot=snapshot_hash)

            canonical_json = _load_canonical_snapshot(connection, table_name, snapshot_hash)
            if canonical_json is None:
                return ValidationResult(ok=False, error_snapshot=snapshot_hash)

            computed_hash = compute_hash(canonical_json, previous_hash)
            if computed_hash != snapshot_hash:
                return ValidationResult(ok=False, error_snapshot=snapshot_hash)

            previous_by_department[department_code] = snapshot_hash
            latest_hash = snapshot_hash
    finally:
        connection.close()

    if latest_hash is None:
        return ValidationResult(ok=False, error_snapshot="sqlite_empty")

    return ValidationResult(ok=True, root_hash=latest_hash)


def _find_anchor_record(anchor_dir: Path) -> dict | None:
    """Español: Función _find_anchor_record del módulo scripts/validate_hashes.py.

    English: Function _find_anchor_record defined in scripts/validate_hashes.py.
    """
    if not anchor_dir.exists():
        return None
    candidates = sorted(anchor_dir.glob("anchor_snapshot_*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        return None
    latest = candidates[-1]
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _verify_anchor(root_hash: str | None, anchor_hash: str | None, anchor_dir: Path) -> AnchorResult:
    """Español: Función _verify_anchor del módulo scripts/validate_hashes.py.

    English: Function _verify_anchor defined in scripts/validate_hashes.py.
    """
    if not root_hash:
        return AnchorResult(ok=False, message="Sin hash raíz para validar anclaje.")

    if anchor_hash:
        if anchor_hash == root_hash:
            return AnchorResult(ok=True, message="Hash raíz coincide con el anclado (manual).")
        return AnchorResult(ok=False, message="Hash raíz NO coincide con el anclado (manual).")

    anchor_record = _find_anchor_record(anchor_dir)
    if anchor_record and anchor_record.get("root_hash"):
        anchored = anchor_record.get("root_hash")
        if anchored == root_hash:
            return AnchorResult(ok=True, message="Hash raíz coincide con el anclado en logs.")
        return AnchorResult(ok=False, message="Hash raíz NO coincide con el anclado en logs.")

    return AnchorResult(
        ok=True,
        message=("Verificación de anclaje simulada (sin RPC/logs disponibles): " f"root_hash={root_hash}"),
    )


def main() -> None:
    """Español: Función main del módulo scripts/validate_hashes.py.

    English: Function main defined in scripts/validate_hashes.py.
    """
    parser = argparse.ArgumentParser(description="Valida la cadena de hashes usando hashes/ o SQLite.")
    parser.add_argument(
        "--hashes-dir",
        default="hashes",
        help="Directorio con archivos .sha256 (por defecto: hashes).",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directorio con snapshots JSON (por defecto: data).",
    )
    parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Ruta a SQLite para validar desde snapshot_index.",
    )
    parser.add_argument(
        "--anchor-hash",
        default=None,
        help="Hash raíz anclado para comparar manualmente.",
    )
    parser.add_argument(
        "--anchor-dir",
        default="logs/anchors",
        help="Directorio con registros de anclaje (por defecto: logs/anchors).",
    )

    args = parser.parse_args()

    if args.sqlite_path:
        result = _validate_sqlite(Path(args.sqlite_path))
    else:
        result = _validate_hash_dir(Path(args.hashes_dir), Path(args.data_dir))

    if not result.ok:
        print(f"Rotura en snapshot {result.error_snapshot}")
        return

    anchor_result = _verify_anchor(result.root_hash, args.anchor_hash, Path(args.anchor_dir))
    print(anchor_result.message)
    print("Cadena íntegra")


if __name__ == "__main__":
    main()
