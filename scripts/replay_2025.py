import argparse
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from scripts import analyze_rules
from scripts.cli import load_snapshots, normalize_snapshots, write_normalized_outputs


@contextmanager
def _chdir(path: Path) -> Iterable[None]:
    current = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_key(candidate: Dict[str, Any]) -> int:
    return int(candidate.get("slot") or 0)


def _build_candidate_lookup(
    candidates: List[Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    lookup: Dict[int, Dict[str, Any]] = {}
    for candidate in candidates:
        slot = _candidate_key(candidate)
        lookup[slot] = candidate
    return lookup


def _diff_totals(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, int]:
    totals_prev = previous.get("totals", {})
    totals_curr = current.get("totals", {})
    fields = [
        "registered_voters",
        "total_votes",
        "valid_votes",
        "null_votes",
        "blank_votes",
    ]
    return {
        field: int(totals_curr.get(field, 0)) - int(totals_prev.get(field, 0))
        for field in fields
    }


def _diff_candidates(
    previous: Dict[str, Any],
    current: Dict[str, Any],
) -> List[Dict[str, Any]]:
    prev_candidates = _build_candidate_lookup(previous.get("candidates", []))
    curr_candidates = _build_candidate_lookup(current.get("candidates", []))
    slots = sorted(set(prev_candidates.keys()) | set(curr_candidates.keys()))
    diffs: List[Dict[str, Any]] = []
    for slot in slots:
        prev = prev_candidates.get(slot, {})
        curr = curr_candidates.get(slot, {})
        prev_votes = int(prev.get("votes") or 0)
        curr_votes = int(curr.get("votes") or 0)
        diffs.append(
            {
                "slot": slot,
                "candidate_id": curr.get("candidate_id") or prev.get("candidate_id"),
                "name": curr.get("name") or prev.get("name"),
                "party": curr.get("party") or prev.get("party"),
                "votes_previous": prev_votes,
                "votes_current": curr_votes,
                "delta_votes": curr_votes - prev_votes,
            }
        )
    return diffs


def build_snapshot_diffs(normalized_dir: Path) -> List[Dict[str, Any]]:
    files = sorted(normalized_dir.glob("*.json"))
    diffs: List[Dict[str, Any]] = []
    for previous_path, current_path in zip(files, files[1:]):
        previous = _load_json(previous_path)
        current = _load_json(current_path)
        diff_entry = {
            "from_snapshot": previous_path.name,
            "to_snapshot": current_path.name,
            "from_timestamp": previous.get("meta", {}).get("timestamp_utc"),
            "to_timestamp": current.get("meta", {}).get("timestamp_utc"),
            "totals_delta": _diff_totals(previous, current),
            "candidate_deltas": _diff_candidates(previous, current),
        }
        diffs.append(diff_entry)
    return diffs


def write_report(report_path: Path, normalized_dir: Path) -> Path:
    diffs = build_snapshot_diffs(normalized_dir)
    payload = {
        "generated_at": _format_timestamp(),
        "normalized_dir": str(normalized_dir),
        "diffs": diffs,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report_path


def run_replay(
    data_dir: Path,
    output_dir: Path,
    analysis_dir: Path,
    report_path: Path,
    department: str,
    year: int,
) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    snapshots = load_snapshots(data_dir)
    normalized = normalize_snapshots(snapshots, department, year)
    write_normalized_outputs(normalized, output_dir)
    normalized_dir = output_dir / "normalized"

    with _chdir(analysis_dir):
        analyze_rules.run_audit(str(normalized_dir))

    report_file = write_report(report_path, normalized_dir)
    return normalized_dir, report_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay 2025: normaliza snapshots, ejecuta reglas y genera diffs neutrales."
    )
    parser.add_argument(
        "--data-dir",
        default="tests/fixtures/snapshots_2025",
        help="Directorio con snapshots crudos 2025.",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/examples/replay_2025",
        help="Directorio para snapshots normalizados.",
    )
    parser.add_argument(
        "--analysis-dir",
        default="docs/examples/analysis_2025",
        help="Directorio para outputs de analyze_rules.",
    )
    parser.add_argument(
        "--report-path",
        default="reports/replay_2025_report.json",
        help="Ruta del reporte de diffs entre snapshots.",
    )
    parser.add_argument(
        "--department",
        default="Francisco Morazán",
        help="Departamento usado en la normalización.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="Año electoral.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    normalized_dir, report_file = run_replay(
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        analysis_dir=Path(args.analysis_dir),
        report_path=Path(args.report_path),
        department=args.department,
        year=args.year,
    )

    summary = {
        "normalized_dir": str(normalized_dir),
        "analysis_dir": str(Path(args.analysis_dir)),
        "report": str(report_file),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
