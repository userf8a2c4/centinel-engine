#!/usr/bin/env python3
"""Compute per-rule analytical quality metrics from labeled cases."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _confidence_rubric(precision: float, recall: float, samples: int) -> str:
    if samples < 20:
        return "low_sample"
    if precision >= 0.9 and recall >= 0.85:
        return "high"
    if precision >= 0.75 and recall >= 0.65:
        return "medium"
    return "review_required"


def _safe_div(num: float, den: float) -> float:
    return round(num / den, 6) if den > 0 else 0.0


def build_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0})

    for case in cases:
        rule = str(case.get("rule_key", "unknown"))
        predicted = bool(case.get("predicted_anomaly", False))
        actual = bool(case.get("actual_anomaly", False))

        if predicted and actual:
            counts[rule]["tp"] += 1
        elif predicted and not actual:
            counts[rule]["fp"] += 1
        elif not predicted and actual:
            counts[rule]["fn"] += 1
        else:
            counts[rule]["tn"] += 1

    per_rule: dict[str, Any] = {}
    totals = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}

    for rule, c in sorted(counts.items()):
        for k in totals:
            totals[k] += c[k]
        samples = c["tp"] + c["fp"] + c["tn"] + c["fn"]
        precision = _safe_div(c["tp"], c["tp"] + c["fp"])
        recall = _safe_div(c["tp"], c["tp"] + c["fn"])
        f1 = _safe_div(2 * precision * recall, precision + recall)
        per_rule[rule] = {
            **c,
            "samples": samples,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confidence": _confidence_rubric(precision, recall, samples),
        }

    total_samples = totals["tp"] + totals["fp"] + totals["tn"] + totals["fn"]
    macro_precision = _safe_div(sum(v["precision"] for v in per_rule.values()), len(per_rule) or 1)
    macro_recall = _safe_div(sum(v["recall"] for v in per_rule.values()), len(per_rule) or 1)

    return {
        "schema_version": "1.0",
        "total_cases": total_samples,
        "overall": {
            **totals,
            "precision": _safe_div(totals["tp"], totals["tp"] + totals["fp"]),
            "recall": _safe_div(totals["tp"], totals["tp"] + totals["fn"]),
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
        },
        "per_rule": per_rule,
    }


def read_cases(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        return payload["cases"]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute per-rule precision/recall from labeled cases")
    parser.add_argument("--input", required=True, help="Labeled cases JSON/JSONL")
    parser.add_argument("--output", required=True, help="Output metrics JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = read_cases(Path(args.input))
    report = build_metrics(cases)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"quality_cases={report['total_cases']}")
    print(f"rules={len(report['per_rule'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
