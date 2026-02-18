#!/usr/bin/env python3
# Cli Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations

"""CLI para normalización, hashing y resúmenes de snapshots.

CLI for snapshot normalization, hashing, and summaries.
"""

import argparse
import hashlib
import json
import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from centinel.core.hashchain import compute_hash
from scripts.logging_utils import configure_logging, log_event
from centinel.core.normalize import normalize_snapshot, snapshot_to_canonical_json

logger = configure_logging(__name__)


@dataclass(frozen=True)
class SnapshotInput:
    """Snapshot crudo y sus metadatos mínimos.

    Raw snapshot and minimal metadata.
    """

    path: Path
    timestamp: str
    raw: Dict[str, Any]


@dataclass(frozen=True)
class NormalizedSnapshot:
    """Snapshot normalizado con su representación canónica.

    Normalized snapshot with its canonical representation.
    """

    name: str
    canonical_json: str


def load_snapshots(data_dir: Path) -> List[SnapshotInput]:
    """Carga snapshots crudos desde un directorio.

    Load raw snapshots from a directory.
    """
    files = sorted(data_dir.glob("*.json"))
    snapshots: List[SnapshotInput] = []
    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        timestamp = raw.get("timestamp") or raw.get("timestamp_utc") or path.stem
        snapshots.append(SnapshotInput(path=path, timestamp=timestamp, raw=raw))
    return snapshots


def normalize_snapshots(
    snapshots: List[SnapshotInput],
    department: str,
    year: int,
) -> List[NormalizedSnapshot]:
    """Normaliza snapshots para análisis reproducible.

    Normalize snapshots for reproducible analysis.
    """
    normalized: List[NormalizedSnapshot] = []
    max_snapshots = 19
    for index, snapshot in enumerate(snapshots[:max_snapshots]):
        normalized_snapshot = normalize_snapshot(
            snapshot.raw,
            department,
            snapshot.timestamp,
            year=year,
        )
        if normalized_snapshot is None:
            log_event(
                logger,
                logging.ERROR,
                "normalize_snapshot_skipped",
                reason="invalid_cne_payload",
                snapshot_name=snapshot.path.stem,
            )
            continue
        canonical_json = snapshot_to_canonical_json(normalized_snapshot)
        normalized.append(
            NormalizedSnapshot(
                name=snapshot.path.stem,
                canonical_json=canonical_json,
            )
        )
    if len(snapshots) > max_snapshots:
        log_event(
            logger,
            logging.WARNING,
            "normalize_snapshot_limit",
            processed=max_snapshots,
            skipped=len(snapshots) - max_snapshots,
        )
    return normalized


def write_normalized_outputs(
    normalized: List[NormalizedSnapshot],
    output_dir: Path,
) -> List[Path]:
    """Escribe snapshots normalizados en disco.

    Write normalized snapshots to disk.
    """
    normalized_dir = output_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    output_paths: List[Path] = []
    for item in normalized:
        out_path = normalized_dir / f"{item.name}.json"
        out_path.write_text(item.canonical_json + "\n", encoding="utf-8")
        output_paths.append(out_path)
    return output_paths


def write_hashchain(
    normalized: List[NormalizedSnapshot],
    output_dir: Path,
) -> Tuple[Path, List[Dict[str, Optional[str]]]]:
    """Genera y guarda la cadena de hashes.

    Generate and store the hash chain.
    """
    hash_entries: List[Dict[str, Optional[str]]] = []
    previous_hash: Optional[str] = None
    hashes_dir = output_dir / "hashes"
    hashes_dir.mkdir(parents=True, exist_ok=True)

    for item in normalized:
        current_hash = compute_hash(item.canonical_json, previous_hash)
        hash_entries.append(
            {
                "snapshot": item.name,
                "hash": current_hash,
                "previous_hash": previous_hash,
            }
        )
        (hashes_dir / f"{item.name}.sha256").write_text(current_hash + "\n", encoding="utf-8")
        previous_hash = current_hash

    chain_path = output_dir / "hashchain.json"
    chain_path.write_text(
        json.dumps(hash_entries, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return chain_path, hash_entries


def _safe_int(value: Any, default: int = 0) -> int:
    """Convierte a entero de forma segura con default.

    Safely convert to integer with a default fallback.
    """
    try:
        if value is None:
            return default
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return default


def _apply_benford(votos_lista: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Evalúa rápidamente una señal Benford de primer dígito.

    Quickly evaluate a first-digit Benford signal.
    """
    if len(votos_lista) < 10:
        return None

    first_digits = []
    for candidate in votos_lista:
        votos_str = str(candidate.get("votos", "")).strip()
        if votos_str and votos_str not in ["0", "None"]:
            first_digits.append(int(votos_str[0]))

    if not first_digits:
        return None

    counts = Counter(first_digits)
    total = len(first_digits)
    dist_1 = (counts[1] / total) * 100
    is_anomaly = dist_1 < 20.0
    return {"is_anomaly": is_anomaly, "prop_1": dist_1}


def audit_snapshots(snapshots: List[SnapshotInput]) -> List[Dict[str, Any]]:
    """Detecta anomalías simples entre snapshots.

    Detect simple anomalies across snapshots.
    """
    peak_votes: Dict[str, Dict[str, Any]] = {}
    anomalies: List[Dict[str, Any]] = []

    for snapshot in snapshots:
        raw = snapshot.raw
        votos_actuales = raw.get("votos") or raw.get("candidates") or []

        for candidate in votos_actuales:
            candidate_id = str(candidate.get("id") or candidate.get("nombre") or "unknown")
            current_votes = _safe_int(candidate.get("votos"))

            if candidate_id in peak_votes:
                if current_votes < peak_votes[candidate_id]["value"]:
                    diff = current_votes - peak_votes[candidate_id]["value"]
                    anomalies.append(
                        {
                            "file": snapshot.path.name,
                            "type": "NEGATIVE_DELTA",
                            "entity": candidate_id,
                            "loss": diff,
                        }
                    )

            if candidate_id not in peak_votes or current_votes > peak_votes[candidate_id]["value"]:
                peak_votes[candidate_id] = {
                    "value": current_votes,
                    "file": snapshot.path.name,
                }

        benford = _apply_benford(votos_actuales)
        if benford and benford["is_anomaly"]:
            anomalies.append(
                {
                    "file": snapshot.path.name,
                    "type": "BENFORD_ANOMALY",
                    "prop_1": round(benford["prop_1"], 2),
                }
            )

    return anomalies


def write_anomalies(anomalies: List[Dict[str, Any]], output_dir: Path) -> Path:
    """Guarda las anomalías detectadas en JSON.

    Persist detected anomalies as JSON.
    """
    anomalies_path = output_dir / "anomalies.json"
    anomalies_path.write_text(
        json.dumps(anomalies, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return anomalies_path


def _sha256_file(path: Path) -> str:
    """Calcula el SHA-256 de un archivo en disco.

    Compute the SHA-256 of a file on disk.
    """
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_registry(paths: List[Path], output_dir: Path) -> Path:
    """Genera un registro con hashes SHA-256 de outputs.

    Generate a registry with SHA-256 hashes of outputs.
    """
    entries = [{"path": str(path), "sha256": _sha256_file(path)} for path in sorted(paths, key=lambda p: str(p))]
    registry_path = output_dir / "registry.json"
    registry_path.write_text(
        json.dumps(entries, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return registry_path


def build_status(
    snapshots: List[SnapshotInput],
    normalized: List[NormalizedSnapshot],
    hash_entries: List[Dict[str, Optional[str]]],
    anomalies: List[Dict[str, Any]],
    output_dir: Path,
    data_dir: Path,
) -> Dict[str, Any]:
    """Construye el resumen de estado del pipeline CLI.

    Build the CLI pipeline status summary.
    """
    latest_snapshot = snapshots[-1].path.name if snapshots else None
    latest_timestamp = snapshots[-1].timestamp if snapshots else None
    head_hash = hash_entries[-1]["hash"] if hash_entries else None

    anomaly_types = Counter([a["type"] for a in anomalies])

    return {
        "inputs": {
            "data_dir": str(data_dir),
            "snapshot_count": len(snapshots),
            "latest_snapshot": latest_snapshot,
            "latest_timestamp": latest_timestamp,
        },
        "outputs": {
            "output_dir": str(output_dir),
            "normalized_dir": str(output_dir / "normalized"),
            "hashchain": str(output_dir / "hashchain.json"),
            "anomalies": str(output_dir / "anomalies.json"),
            "registry": str(output_dir / "registry.json"),
        },
        "hashchain": {
            "length": len(hash_entries),
            "head": head_hash,
        },
        "anomalies": {
            "count": len(anomalies),
            "by_type": dict(sorted(anomaly_types.items())),
        },
        "normalized": {
            "count": len(normalized),
            "snapshots": [item.name for item in normalized],
        },
    }


def write_status(status: Dict[str, Any], output_dir: Path) -> Path:
    """Escribe el estado del pipeline en disco.

    Write the pipeline status to disk.
    """
    status_path = output_dir / "status.json"
    status_path.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return status_path


def run_pipeline(args: argparse.Namespace) -> None:
    """Ejecuta el pipeline completo del CLI.

    Run the full CLI pipeline.
    """
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshots = load_snapshots(data_dir)
    normalized = normalize_snapshots(snapshots, args.department, args.year)

    normalized_paths = write_normalized_outputs(normalized, output_dir)
    hashchain_path, hash_entries = write_hashchain(normalized, output_dir)
    anomalies = audit_snapshots(snapshots)
    anomalies_path = write_anomalies(anomalies, output_dir)

    status = build_status(
        snapshots,
        normalized,
        hash_entries,
        anomalies,
        output_dir,
        data_dir,
    )
    status_path = write_status(status, output_dir)
    registry_path = write_registry(
        normalized_paths + [hashchain_path, anomalies_path, status_path],
        output_dir,
    )

    summary = {
        "normalized": len(normalized_paths),
        "hashchain": str(hashchain_path),
        "anomalies": len(anomalies),
        "status": str(status_path),
        "registry": str(registry_path),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def show_status(args: argparse.Namespace) -> None:
    """Imprime el estado del pipeline guardado.

    Print the saved pipeline status.
    """
    status_path = Path(args.output_dir) / "status.json"
    if not status_path.exists():
        raise SystemExit(f"No existe status.json en {status_path.parent}. " "Ejecuta 'run' primero.")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    print(json.dumps(status, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos principal.

    Build the main argument parser.
    """
    parser = argparse.ArgumentParser(
        description="CLI para ejecutar el pipeline Proyecto C.E.N.T.I.N.E.L. y consultar estado."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Ejecuta el pipeline completo.")
    run_parser.add_argument(
        "--data-dir",
        default="data",
        help="Directorio con snapshots JSON crudos.",
    )
    run_parser.add_argument(
        "--output-dir",
        default="reports/pipeline",
        help="Directorio donde se registran outputs deterministas.",
    )
    run_parser.add_argument(
        "--department",
        default="Francisco Morazán",
        help="Departamento a usar en la normalización.",
    )
    run_parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="Año electoral para metadatos.",
    )
    run_parser.set_defaults(func=run_pipeline)

    status_parser = subparsers.add_parser("status", help="Imprime el resumen de estado en JSON.")
    status_parser.add_argument(
        "--output-dir",
        default="reports/pipeline",
        help="Directorio donde se guardó status.json.",
    )
    status_parser.set_defaults(func=show_status)

    return parser


def main() -> None:
    """Punto de entrada principal del script.

    Main script entry point.
    """
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
