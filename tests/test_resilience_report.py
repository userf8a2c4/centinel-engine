from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_resilience_report_from_junit(tmp_path: Path) -> None:
    junit = tmp_path / "resilience.junit.xml"
    junit.write_text(
        """<testsuite name=\"resilience\" tests=\"8\" failures=\"0\" errors=\"0\" skipped=\"1\"></testsuite>""",
        encoding="utf-8",
    )
    output = tmp_path / "resilience_report.json"

    subprocess.run(
        [
            sys.executable,
            "scripts/resilience_report.py",
            "--junit-xml",
            str(junit),
            "--output",
            str(output),
            "--release-version",
            "v4.0.0",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["release_version"] == "v4.0.0"
    assert report["resilience_suite"]["tests"] == 8
    assert report["resilience_score"] >= 85


def test_resilience_report_penalizes_failures_and_mttr(tmp_path: Path) -> None:
    junit = tmp_path / "resilience.junit.xml"
    junit.write_text(
        """<testsuite name=\"resilience\" tests=\"10\" failures=\"2\" errors=\"1\" skipped=\"0\"></testsuite>""",
        encoding="utf-8",
    )
    metrics = tmp_path / "runtime_metrics.json"
    metrics.write_text(
        json.dumps(
            {
                "mttr_seconds": 300,
                "http_429_events": 7,
                "http_503_events": 2,
                "effective_retries": 9,
                "watchdog_recoveries": 1,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "resilience_report.json"

    subprocess.run(
        [
            sys.executable,
            "scripts/resilience_report.py",
            "--junit-xml",
            str(junit),
            "--output",
            str(output),
            "--release-version",
            "v4.0.1",
            "--runtime-metrics",
            str(metrics),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["runtime_metrics"]["mttr_seconds"] == 300
    assert report["resilience_score"] < 80
