from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_resilience_report(path: Path, release: str, score: int, mttr: int, e429: int, e503: int, rec: int) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "release_version": release,
                "resilience_suite": {"tests": 10, "failures": 0, "errors": 0, "skipped": 0},
                "runtime_metrics": {
                    "mttr_seconds": mttr,
                    "http_429_events": e429,
                    "http_503_events": e503,
                    "effective_retries": 3,
                    "watchdog_recoveries": rec,
                },
                "resilience_score": score,
            }
        ),
        encoding="utf-8",
    )


def test_institutional_transparency_report(tmp_path: Path) -> None:
    r1 = tmp_path / "r1.json"
    r2 = tmp_path / "r2.json"
    output = tmp_path / "institutional_transparency.json"

    _write_resilience_report(r1, "v1.0.0", 90, 40, 3, 1, 2)
    _write_resilience_report(r2, "v1.0.1", 80, 60, 5, 2, 1)

    subprocess.run(
        [
            sys.executable,
            "scripts/institutional_transparency_report.py",
            "--resilience-reports",
            str(r1),
            str(r2),
            "--output",
            str(output),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["releases_analyzed"] == 2
    assert data["release_versions"] == ["v1.0.0", "v1.0.1"]
    assert data["metrics"]["avg_resilience_score"] == 85.0
    assert data["metrics"]["avg_mttr_seconds"] == 50.0
    assert data["metrics"]["avg_http_429_events"] == 4.0


def test_institutional_transparency_report_handles_null_runtime_metrics(tmp_path: Path) -> None:
    r1 = tmp_path / "r1.json"
    r2 = tmp_path / "r2.json"
    output = tmp_path / "institutional_transparency_null_runtime.json"

    r1.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "release_version": "v2.0.0",
                "runtime_metrics": None,
                "resilience_score": 88,
            }
        ),
        encoding="utf-8",
    )
    _write_resilience_report(r2, "v2.0.1", 92, 30, 2, 1, 1)

    subprocess.run(
        [
            sys.executable,
            "scripts/institutional_transparency_report.py",
            "--resilience-reports",
            str(r1),
            str(r2),
            "--output",
            str(output),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["releases_analyzed"] == 2
    assert data["metrics"]["avg_resilience_score"] == 90.0
    assert data["metrics"]["avg_mttr_seconds"] == 30.0
