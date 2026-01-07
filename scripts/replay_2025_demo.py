import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from dateutil import parser

from sentinel.utils.logging_config import setup_logging


setup_logging()
logger = logging.getLogger("sentinel.replay")


def parse_timestamp(path: Path, payload: dict) -> datetime | None:
    raw = payload.get("meta", {}).get("timestamp_utc")
    if raw:
        try:
            return parser.parse(raw)
        except (ValueError, TypeError):
            pass
    try:
        return parser.parse(path.stem.replace("snapshot_", "").replace("-", ":", 2))
    except (ValueError, TypeError):
        return None


def load_snapshot(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        logger.error("snapshot_read_failed path=%s error=%s", path, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.error("snapshot_json_failed path=%s error=%s", path, exc)
        return None

    timestamp = parse_timestamp(path, payload)
    if not timestamp:
        logger.warning("snapshot_timestamp_missing path=%s", path)
        return None

    totals = payload.get("totals", {})
    candidates = payload.get("candidates", [])
    candidate_votes = {
        str(c.get("candidate_id") or c.get("name") or c.get("slot")): int(c.get("votes", 0))
        for c in candidates
        if isinstance(c, dict)
    }

    return {
        "path": str(path),
        "timestamp": timestamp,
        "totals": {
            "total_votes": int(totals.get("total_votes", 0)),
            "valid_votes": int(totals.get("valid_votes", 0)),
            "null_votes": int(totals.get("null_votes", 0)),
            "blank_votes": int(totals.get("blank_votes", 0)),
        },
        "candidates": candidate_votes,
    }


def diff_snapshots(previous: dict, current: dict) -> dict:
    totals_delta = {
        key: current["totals"][key] - previous["totals"][key]
        for key in previous["totals"].keys()
    }

    candidate_ids = set(previous["candidates"]) | set(current["candidates"])
    candidates_delta = {
        candidate_id: current["candidates"].get(candidate_id, 0) - previous["candidates"].get(candidate_id, 0)
        for candidate_id in sorted(candidate_ids)
    }

    return {
        "from": previous["timestamp"].isoformat(),
        "to": current["timestamp"].isoformat(),
        "delta_totals": totals_delta,
        "delta_candidates": candidates_delta,
    }


def generate_report(source_dir: Path, output_path: Path) -> None:
    snapshots = []
    for path in sorted(source_dir.glob("*.json")):
        snapshot = load_snapshot(path)
        if snapshot:
            snapshots.append(snapshot)

    snapshots = sorted(snapshots, key=lambda item: item["timestamp"])
    if len(snapshots) < 2:
        logger.warning("insufficient_snapshots count=%s", len(snapshots))
        return

    diffs = []
    for previous, current in zip(snapshots, snapshots[1:]):
        diffs.append(diff_snapshots(previous, current))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "diffs": diffs,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("replay_report_generated output=%s", output_path)


def main() -> None:
    parser_cli = argparse.ArgumentParser(description="Genera reporte neutral de diffs con snapshots 2025.")
    parser_cli.add_argument(
        "--source-dir",
        default="docs/examples/replay_2025/normalized",
        help="Directorio con snapshots normalizados (default: docs/examples/replay_2025/normalized).",
    )
    parser_cli.add_argument(
        "--output",
        default="reports/replay_2025_report.json",
        help="Ruta de salida del reporte (default: reports/replay_2025_report.json).",
    )
    args = parser_cli.parse_args()

    generate_report(Path(args.source_dir), Path(args.output))


if __name__ == "__main__":
    main()
