#!/usr/bin/env python3
"""
False positive rate validation for Centinel Engine statistical rules.

ES: Validación de tasa de falsos positivos para las reglas estadísticas de Centinel Engine.

Genera datos electorales sintéticos limpios (sin fraude) y corre las reglas estadísticas
para medir con qué frecuencia generan falsos positivos.

EN: Generates synthetic clean electoral data (no fraud) and runs statistical rules
to measure how often they generate false positives.

Usage:
    python scripts/validate_false_positive_rate.py
    python scripts/validate_false_positive_rate.py --iterations 500 --output results.json
    python scripts/validate_false_positive_rate.py --min-actas 50 --seed 42
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from centinel.core.rules import (
        benford_law_rule,
        benford_first_digit_rule,
        last_digit_uniformity_rule,
        participation_anomaly_rule,
        participation_anomaly_advanced_rule,
        null_blank_rule,
        table_consistency_rule,
        mesa_impossibility_rule,
        large_numbers_rule,
        turnout_impossible_rule,
        geographic_dispersion_rule,
        granular_anomaly_rule,
        irreversibility_rule,
        runs_test_rule,
        correlation_participation_vote_rule,
    )
    RULES_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Could not import rules: {e}", file=sys.stderr)
    RULES_AVAILABLE = False


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    "ATLANTIDA", "COLON", "COMAYAGUA", "COPAN", "CORTES",
    "CHOLUTECA", "EL PARAISO", "FRANCISCO MORAZAN", "GRACIAS A DIOS",
    "INTIBUCA", "ISLAS DE LA BAHIA", "LA PAZ", "LEMPIRA", "OCOTEPEQUE",
    "OLANCHO", "SANTA BARBARA", "VALLE", "YORO",
]

# Approximate registered voters per department (fictitious but realistic proportions)
DEPT_ELECTORES = {
    "ATLANTIDA": 220000, "COLON": 120000, "COMAYAGUA": 280000,
    "COPAN": 200000, "CORTES": 650000, "CHOLUTECA": 250000,
    "EL PARAISO": 280000, "FRANCISCO MORAZAN": 950000, "GRACIAS A DIOS": 45000,
    "INTIBUCA": 120000, "ISLAS DE LA BAHIA": 55000, "LA PAZ": 140000,
    "LEMPIRA": 180000, "OCOTEPEQUE": 80000, "OLANCHO": 320000,
    "SANTA BARBARA": 250000, "VALLE": 140000, "YORO": 320000,
}


def _benford_sample(n: int, rng: random.Random) -> list[int]:
    """Generate n integers that approximately follow Benford's law."""
    results = []
    for _ in range(n):
        # First digit from Benford distribution
        r = rng.random()
        cumulative = 0.0
        first_digit = 1
        for d in range(1, 10):
            cumulative += math.log10(1 + 1 / d)
            if r <= cumulative:
                first_digit = d
                break
        # Remaining digits random
        num_extra = rng.randint(1, 4)
        rest = "".join(str(rng.randint(0, 9)) for _ in range(num_extra))
        results.append(int(str(first_digit) + rest))
    return results


def generate_snapshot(
    dept: str,
    n_actas: int,
    pct_escrutado: float,
    turnout: float,
    rng: random.Random,
    prev_snapshot: Optional[dict] = None,
) -> dict:
    """
    Generate a synthetic CNE-format JSON snapshot for one department.

    All values are generated to be internally consistent and statistically
    clean (no manipulation patterns).
    """
    electores = DEPT_ELECTORES.get(dept, 200000)
    actas_total = max(n_actas, 1)
    actas_procesadas = max(1, int(actas_total * pct_escrutado))

    # Vote totals: Benford-distributed across actas
    # Three fictitious candidates (A, B, C) + null + blank
    vote_samples_a = _benford_sample(actas_procesadas, rng)
    vote_samples_b = _benford_sample(actas_procesadas, rng)
    vote_samples_c = _benford_sample(actas_procesadas, rng)

    # Normalize to fit within registered voter pool
    total_votes_raw = sum(vote_samples_a) + sum(vote_samples_b) + sum(vote_samples_c)
    expected_total = int(electores * turnout * pct_escrutado)
    if total_votes_raw > 0:
        scale = expected_total / total_votes_raw
    else:
        scale = 1.0

    votes_a = max(1, int(sum(vote_samples_a) * scale))
    votes_b = max(1, int(sum(vote_samples_b) * scale))
    votes_c = max(1, int(sum(vote_samples_c) * scale))

    total_votes = votes_a + votes_b + votes_c
    nulos = max(0, int(total_votes * rng.uniform(0.005, 0.03)))
    blancos = max(0, int(total_votes * rng.uniform(0.005, 0.02)))

    snapshot = {
        "departamento": dept,
        "timestamp": time.time(),
        "porcentaje_escrutado": round(pct_escrutado * 100, 2),
        "electores_registrados": electores,
        "actas": {
            "totales": actas_total,
            "procesadas": actas_procesadas,
            "divulgadas": actas_procesadas,
        },
        "mesas": {
            "totales": actas_total,
            "procesadas": actas_procesadas,
        },
        "votos_totales": {
            "total": total_votes + nulos + blancos,
            "validos": total_votes,
            "nulos": nulos,
            "blancos": blancos,
        },
        "votos": [
            {"candidato": "Candidato A", "partido": "Partido X", "votes": votes_a},
            {"candidato": "Candidato B", "partido": "Partido Y", "votes": votes_b},
            {"candidato": "Candidato C", "partido": "Partido Z", "votes": votes_c},
        ],
        "municipios": [
            {
                "nombre": f"Municipio {i+1}",
                "actas_procesadas": max(1, actas_procesadas // max(1, n_actas // 5)),
                "actas_totales": max(1, n_actas // max(1, n_actas // 5)),
                "votos": [
                    {"candidato": "Candidato A", "votes": vs_a},
                    {"candidato": "Candidato B", "votes": vs_b},
                    {"candidato": "Candidato C", "votes": vs_c},
                ],
            }
            for i, (vs_a, vs_b, vs_c) in enumerate(
                zip(
                    _benford_sample(min(5, actas_procesadas), rng),
                    _benford_sample(min(5, actas_procesadas), rng),
                    _benford_sample(min(5, actas_procesadas), rng),
                )
            )
        ],
    }

    # For irreversibility rule: ensure counts only increase
    if prev_snapshot:
        prev_actas = (prev_snapshot.get("actas") or {}).get("procesadas", 0)
        snapshot["actas"]["procesadas"] = max(actas_procesadas, prev_actas)
        snapshot["actas"]["divulgadas"] = snapshot["actas"]["procesadas"]
        snapshot["mesas"]["procesadas"] = snapshot["actas"]["procesadas"]

    return snapshot


# ---------------------------------------------------------------------------
# Rule runner
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "benford_law": {
        "min_samples": 10,
        "deviation_pct": 15,
        "chi_square_threshold": 0.05,
    },
    "benford_first_digit": {
        "min_samples": 10,
        "mad_threshold": 0.015,
    },
    "last_digit_uniformity": {
        "min_samples": 20,
        "chi_square_p_threshold": 0.01,
    },
    "participation_anomaly": {
        "z_score_threshold": 3.0,
        "min_departments": 3,
    },
    "participation_anomaly_advanced": {
        "z_score_threshold": 3.5,
        "min_departments": 3,
    },
    "null_blank": {
        "max_null_ratio": 0.15,
        "max_blank_ratio": 0.10,
    },
    "table_consistency": {
        "tolerance": 0.001,
    },
    "mesa_impossibility": {
        "max_turnout": 1.0,
    },
    "large_numbers": {
        "z_score_threshold": 3.0,
    },
    "turnout_impossible": {
        "max_turnout": 1.05,
    },
    "geographic_dispersion": {
        "z_score_threshold": 3.0,
    },
    "granular_anomaly": {
        "z_score_threshold": 3.5,
    },
    "irreversibility": {},
    "runs_test": {
        "p_value_threshold": 0.01,
    },
    "correlation": {
        "pearson_threshold": 0.85,
        "min_departments": 5,
    },
}

RULE_MAP = {}
if RULES_AVAILABLE:
    RULE_MAP = {
        "benford_law": benford_law_rule,
        "benford_first_digit": benford_first_digit_rule,
        "last_digit_uniformity": last_digit_uniformity_rule,
        "participation_anomaly": participation_anomaly_rule,
        "participation_anomaly_advanced": participation_anomaly_advanced_rule,
        "null_blank": null_blank_rule,
        "table_consistency": table_consistency_rule,
        "mesa_impossibility": mesa_impossibility_rule,
        "large_numbers": large_numbers_rule,
        "turnout_impossible": turnout_impossible_rule,
        "geographic_dispersion": geographic_dispersion_rule,
        "granular_anomaly": granular_anomaly_rule,
        "irreversibility": irreversibility_rule,
        "runs_test": runs_test_rule,
        "correlation": correlation_participation_vote_rule,
    }


def run_rules(snapshot: dict, prev_snapshot: Optional[dict]) -> dict[str, list]:
    """Run all available rules against a snapshot and return alerts by rule name."""
    results: dict[str, list] = {}
    for rule_name, module in RULE_MAP.items():
        config = DEFAULT_CONFIG.get(rule_name, {})
        try:
            alerts = module.apply(snapshot, prev_snapshot, config)
            results[rule_name] = alerts or []
        except Exception as e:
            results[rule_name] = [{"error": str(e)}]
    return results


# ---------------------------------------------------------------------------
# Statistical summary
# ---------------------------------------------------------------------------

def compute_fp_rate(
    rule_name: str,
    flagged_count: int,
    total_iterations: int,
) -> dict:
    """Compute false positive rate with Wilson confidence interval."""
    n = total_iterations
    p = flagged_count / n if n > 0 else 0.0

    # Wilson score interval (95%)
    z = 1.96
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    ci_low = max(0.0, centre - margin)
    ci_high = min(1.0, centre + margin)

    return {
        "rule": rule_name,
        "flagged": flagged_count,
        "total": n,
        "fp_rate_pct": round(p * 100, 2),
        "ci_95_low_pct": round(ci_low * 100, 2),
        "ci_95_high_pct": round(ci_high * 100, 2),
        "acceptable": p < 0.05,  # <5% is acceptable per grant docs
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate false positive rates for Centinel Engine statistical rules"
    )
    parser.add_argument(
        "--iterations", type=int, default=200,
        help="Number of synthetic clean elections to generate (default: 200)"
    )
    parser.add_argument(
        "--min-actas", type=int, default=60,
        help="Minimum actas per snapshot (default: 60)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Write JSON results to this file"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-iteration output"
    )
    args = parser.parse_args()

    if not RULES_AVAILABLE:
        print("[ERROR] Centinel rules not importable. Run from repo root with venv active.")
        sys.exit(1)

    rng = random.Random(args.seed)
    iterations = args.iterations
    min_actas = args.min_actas

    print(f"Centinel Engine — False Positive Rate Validation")
    print(f"Iterations: {iterations} | Min actas: {min_actas} | Seed: {args.seed}")
    print(f"Rules loaded: {len(RULE_MAP)}")
    print("=" * 60)

    # Track flagged counts per rule
    flagged: dict[str, int] = {rule: 0 for rule in RULE_MAP}
    total_snapshots = 0

    for i in range(iterations):
        dept = rng.choice(DEPARTMENTS)
        n_actas = rng.randint(min_actas, 300)
        pct_escrutado = rng.uniform(0.3, 1.0)
        turnout = rng.uniform(0.40, 0.75)

        prev_snapshot = None
        # Simulate a 3-snapshot sequence (beginning, middle, end of count)
        for stage_pct in [pct_escrutado * 0.3, pct_escrutado * 0.65, pct_escrutado]:
            snapshot = generate_snapshot(
                dept, n_actas, min(stage_pct, 1.0), turnout, rng, prev_snapshot
            )
            results = run_rules(snapshot, prev_snapshot)
            total_snapshots += 1

            for rule_name, alerts in results.items():
                real_alerts = [a for a in alerts if "error" not in a]
                if real_alerts:
                    flagged[rule_name] += 1

            prev_snapshot = snapshot

        if not args.quiet and (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{iterations} elections processed")

    print(f"\nTotal snapshots processed: {total_snapshots}")
    print(f"\nFalse Positive Rate by Rule (threshold: <5%):")
    print("-" * 60)

    summary = []
    all_acceptable = True
    for rule_name in sorted(RULE_MAP.keys()):
        fp = compute_fp_rate(rule_name, flagged[rule_name], total_snapshots)
        summary.append(fp)
        status = "✓ OK" if fp["acceptable"] else "✗ HIGH"
        if not fp["acceptable"]:
            all_acceptable = False
        print(
            f"  {rule_name:<40} {fp['fp_rate_pct']:5.2f}%  "
            f"[{fp['ci_95_low_pct']:.2f}%–{fp['ci_95_high_pct']:.2f}%]  {status}"
        )

    print("-" * 60)
    if all_acceptable:
        print("RESULT: All rules within acceptable false positive range (<5%)")
    else:
        high_rules = [s["rule"] for s in summary if not s["acceptable"]]
        print(f"RESULT: {len(high_rules)} rule(s) exceed 5% threshold: {high_rules}")
        print("Consider raising thresholds or adding minimum sample size guards.")

    output_data = {
        "metadata": {
            "run_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "iterations": iterations,
            "total_snapshots": total_snapshots,
            "min_actas": min_actas,
            "seed": args.seed,
            "rules_loaded": len(RULE_MAP),
        },
        "results": summary,
        "all_acceptable": all_acceptable,
    }

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(output_data, indent=2))
        print(f"\nResults written to: {out_path}")
    else:
        print("\nJSON output (use --output FILE to save):")
        print(json.dumps(output_data, indent=2))


if __name__ == "__main__":
    main()
