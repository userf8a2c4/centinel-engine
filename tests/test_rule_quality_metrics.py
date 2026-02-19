from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_rule_quality_metrics_jsonl(tmp_path: Path) -> None:
    src = tmp_path / "cases.jsonl"
    src.write_text(
        "\n".join(
            [
                json.dumps({"rule_key": "turnout_impossible", "predicted_anomaly": True, "actual_anomaly": True}),
                json.dumps({"rule_key": "turnout_impossible", "predicted_anomaly": True, "actual_anomaly": False}),
                json.dumps({"rule_key": "turnout_impossible", "predicted_anomaly": False, "actual_anomaly": True}),
                json.dumps({"rule_key": "benford_first_digit", "predicted_anomaly": False, "actual_anomaly": False}),
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "quality.json"

    subprocess.run(
        [sys.executable, "scripts/rule_quality_metrics.py", "--input", str(src), "--output", str(out)],
        check=True,
    )

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["total_cases"] == 4
    assert report["overall"]["tp"] == 1
    assert report["overall"]["fp"] == 1
    assert report["overall"]["fn"] == 1
    assert "turnout_impossible" in report["per_rule"]


def test_rule_quality_metrics_json_object_cases(tmp_path: Path) -> None:
    src = tmp_path / "cases.json"
    src.write_text(
        json.dumps(
            {
                "cases": [
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                    {"rule_key": "a", "predicted_anomaly": True, "actual_anomaly": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "quality.json"

    subprocess.run(
        [sys.executable, "scripts/rule_quality_metrics.py", "--input", str(src), "--output", str(out)],
        check=True,
    )

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["per_rule"]["a"]["samples"] == 20
    assert report["per_rule"]["a"]["confidence"] == "high"
