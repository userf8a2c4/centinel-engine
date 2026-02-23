#!/usr/bin/env python3
"""Build release-level institutional transparency metrics from resilience reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


def _read_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _runtime(report: dict[str, Any]) -> dict[str, Any]:
    runtime = report.get("runtime_metrics")
    return runtime if isinstance(runtime, dict) else {}


def build_transparency_report(report_paths: list[Path], output: Path) -> dict[str, Any]:
    reports = [_read_report(path) for path in report_paths]
    if not reports:
        raise ValueError("At least one resilience report is required")

    release_versions = [r.get("release_version", "unknown") for r in reports]
    scores = [_num(r.get("resilience_score")) for r in reports]
    mttr_values = [_num(_runtime(r).get("mttr_seconds")) for r in reports]
    events_429 = [_num(_runtime(r).get("http_429_events")) for r in reports]
    events_503 = [_num(_runtime(r).get("http_503_events")) for r in reports]
    recoveries = [_num(_runtime(r).get("watchdog_recoveries")) for r in reports]

    def _avg(values: list[float | None]) -> float | None:
        clean = [v for v in values if v is not None]
        return round(mean(clean), 2) if clean else None

    transparency = {
        "schema_version": "1.0",
        "releases_analyzed": len(reports),
        "release_versions": release_versions,
        "metrics": {
            "avg_resilience_score": _avg(scores),
            "avg_mttr_seconds": _avg(mttr_values),
            "avg_http_429_events": _avg(events_429),
            "avg_http_503_events": _avg(events_503),
            "avg_watchdog_recoveries": _avg(recoveries),
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(transparency, indent=2, ensure_ascii=False), encoding="utf-8")
    return transparency


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build institutional transparency metrics report")
    parser.add_argument(
        "--resilience-reports",
        required=True,
        nargs="+",
        help="List of resilience report JSON files",
    )
    parser.add_argument("--output", required=True, help="Output JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_transparency_report(
        report_paths=[Path(p) for p in args.resilience_reports],
        output=Path(args.output),
    )
    print(f"report_path={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
