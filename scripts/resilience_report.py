#!/usr/bin/env python3
"""Build a deterministic resilience report and release score from CI artifacts."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _load_junit(path: Path) -> dict[str, int]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    return {
        "tests": int(suite.attrib.get("tests", "0")),
        "failures": int(suite.attrib.get("failures", "0")),
        "errors": int(suite.attrib.get("errors", "0")),
        "skipped": int(suite.attrib.get("skipped", "0")),
    }


def _load_runtime_metrics(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "mttr_seconds": None,
            "http_429_events": None,
            "http_503_events": None,
            "effective_retries": None,
            "watchdog_recoveries": None,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "mttr_seconds": data.get("mttr_seconds"),
        "http_429_events": data.get("http_429_events"),
        "http_503_events": data.get("http_503_events"),
        "effective_retries": data.get("effective_retries"),
        "watchdog_recoveries": data.get("watchdog_recoveries"),
    }


def _compute_score(junit: dict[str, int], runtime: dict[str, Any]) -> int:
    total = max(junit["tests"], 1)
    penalty = 100 * (junit["failures"] + junit["errors"]) / total

    mttr = runtime.get("mttr_seconds")
    if isinstance(mttr, (int, float)):
        penalty += min(20.0, float(mttr) / 30.0)

    failures = junit["failures"] + junit["errors"]
    score = max(0, int(round(100 - penalty)))
    if failures == 0 and junit["tests"] > 0:
        score = max(score, 85)
    return score


def build_report(
    junit_xml: Path,
    output: Path,
    release_version: str,
    runtime_metrics: Path | None = None,
) -> dict[str, Any]:
    junit = _load_junit(junit_xml)
    runtime = _load_runtime_metrics(runtime_metrics)
    report = {
        "schema_version": "1.0",
        "release_version": release_version,
        "resilience_suite": junit,
        "runtime_metrics": runtime,
        "resilience_score": _compute_score(junit, runtime),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build resilience score report from CI artifacts")
    parser.add_argument("--junit-xml", required=True, help="Path to pytest junit XML")
    parser.add_argument("--output", required=True, help="Output JSON report path")
    parser.add_argument("--release-version", required=True, help="Release version label")
    parser.add_argument("--runtime-metrics", help="Optional runtime metrics JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        junit_xml=Path(args.junit_xml),
        output=Path(args.output),
        release_version=args.release_version,
        runtime_metrics=Path(args.runtime_metrics) if args.runtime_metrics else None,
    )
    print(f"resilience_score={report['resilience_score']}")
    print(f"report_path={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
