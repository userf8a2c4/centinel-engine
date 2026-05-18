"""
Calibración de reglas Centinel contra datos reales CNE Honduras 2025.

Ejecutar:
    python scripts/calibrate_2025.py --data /path/to/hnd-electoral-audit-2025/data

Produce:
    reports/calibration_2025.json  — anomalías detectadas por regla
    reports/calibration_2025.md    — resumen legible para OTF/académicos
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Helpers ────────────────────────────────────────────────────────────────

def parse_num(s: str) -> int:
    """'1,027,090' → 1027090"""
    if s is None:
        return 0
    return int(str(s).replace(",", "").strip() or 0)


def load_snapshots(data_dir: Path) -> list[dict]:
    """Carga y ordena los JSON por timestamp en el nombre de archivo."""
    pattern = re.compile(
        r"HN\.PRESIDENTE\.00-TODOS\.000-TODOS (\d{4}-\d{2}-\d{2} \d{2}_\d{2}_\d{2})\.json"
    )
    snapshots = []
    for f in sorted(data_dir.glob("HN.PRESIDENTE*.json")):
        m = pattern.match(f.name)
        if not m:
            continue
        ts_str = m.group(1).replace("_", ":")
        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] {f.name}: {e}", file=sys.stderr)
            continue
        snapshots.append({"ts": ts, "file": f.name, "data": data})
    return sorted(snapshots, key=lambda x: x["ts"])


def extract_metrics(snap: dict) -> dict:
    """Extrae métricas comparables de un snapshot."""
    d = snap["data"]
    stats = d.get("estadisticas", {})
    tot = stats.get("totalizacion_actas", {})
    dist = stats.get("distribucion_votos", {})
    estado = stats.get("estado_actas_divulgadas", {})
    resultados = d.get("resultados", []) or []

    actas_totales = parse_num(tot.get("actas_totales"))
    actas_divulgadas = parse_num(tot.get("actas_divulgadas"))
    validos = parse_num(dist.get("validos"))
    nulos = parse_num(dist.get("nulos"))
    blancos = parse_num(dist.get("blancos"))
    inconsistentes = parse_num(estado.get("actas_inconsistentes"))
    correctas = parse_num(estado.get("actas_correctas"))

    votos_por_partido = {}
    for r in resultados:
        partido = r.get("partido", "DESCONOCIDO")
        votos_por_partido[partido] = parse_num(r.get("votos"))

    total_votos = sum(votos_por_partido.values())
    pct_nulos_blancos = (nulos + blancos) / total_votos if total_votos > 0 else 0
    pct_inconsistentes = inconsistentes / actas_divulgadas if actas_divulgadas > 0 else 0
    pct_escrutinio = actas_divulgadas / actas_totales if actas_totales > 0 else 0

    return {
        "ts": snap["ts"],
        "file": snap["file"],
        "actas_totales": actas_totales,
        "actas_divulgadas": actas_divulgadas,
        "validos": validos,
        "nulos": nulos,
        "blancos": blancos,
        "inconsistentes": inconsistentes,
        "correctas": correctas,
        "total_votos": total_votos,
        "pct_nulos_blancos": pct_nulos_blancos,
        "pct_inconsistentes": pct_inconsistentes,
        "pct_escrutinio": pct_escrutinio,
        "votos_por_partido": votos_por_partido,
        "blackout": total_votos == 0 and actas_divulgadas > 0,
    }


# ── Detectores de anomalías ────────────────────────────────────────────────

def detect_universe_mutation(metrics: list[dict]) -> list[dict]:
    """Detecta cambio en actas_totales (universo inmutable)."""
    alerts = []
    prev_total = None
    for m in metrics:
        if prev_total is not None and m["actas_totales"] != prev_total:
            delta = m["actas_totales"] - prev_total
            alerts.append({
                "rule": "universe_mutation",
                "severity": "CRITICAL",
                "ts": m["ts"].isoformat(),
                "file": m["file"],
                "message": (
                    f"actas_totales cambió de {prev_total:,} → {m['actas_totales']:,} "
                    f"(Δ={delta:+d}). El universo electoral debe ser constante."
                ),
                "value": {"before": prev_total, "after": m["actas_totales"], "delta": delta},
            })
        if m["actas_totales"] > 0:
            prev_total = m["actas_totales"]
    return alerts


def detect_blackout(metrics: list[dict]) -> list[dict]:
    """Detecta periodos donde resultados=[] pero actas_divulgadas crece."""
    alerts = []
    in_blackout = False
    blackout_start = None
    actas_at_start = 0

    for m in metrics:
        if m["blackout"] and not in_blackout:
            in_blackout = True
            blackout_start = m["ts"]
            actas_at_start = m["actas_divulgadas"]
            alerts.append({
                "rule": "data_blackout_start",
                "severity": "CRITICAL",
                "ts": m["ts"].isoformat(),
                "file": m["file"],
                "message": (
                    f"INICIO BLACKOUT: resultados vacíos pero "
                    f"actas_divulgadas={m['actas_divulgadas']:,}. "
                    "El sistema oculta votos mientras sigue contando."
                ),
                "value": {"actas_divulgadas": m["actas_divulgadas"]},
            })
        elif not m["blackout"] and in_blackout:
            in_blackout = False
            duration_min = (m["ts"] - blackout_start).total_seconds() / 60
            actas_in_blackout = m["actas_divulgadas"] - actas_at_start
            alerts.append({
                "rule": "data_blackout_end",
                "severity": "CRITICAL",
                "ts": m["ts"].isoformat(),
                "file": m["file"],
                "message": (
                    f"FIN BLACKOUT: duración={duration_min:.0f} min, "
                    f"actas contadas en sombra={actas_in_blackout:+,}. "
                    f"Votos totales restaurados={m['total_votos']:,}."
                ),
                "value": {
                    "duration_minutes": duration_min,
                    "actas_counted_in_shadow": actas_in_blackout,
                    "total_votes_after": m["total_votos"],
                },
            })
    return alerts


def detect_snapshot_jumps(metrics: list[dict], threshold_pct: float = 5.0) -> list[dict]:
    """Detecta saltos >threshold_pct% en votos de líder entre snapshots consecutivos."""
    alerts = []
    prev = None
    for m in metrics:
        if m["blackout"] or m["total_votos"] == 0:
            prev = m
            continue
        if prev and not prev["blackout"] and prev["total_votos"] > 0:
            for partido, votos in m["votos_por_partido"].items():
                prev_votos = prev["votos_por_partido"].get(partido, 0)
                if prev_votos == 0:
                    continue
                change_pct = abs(votos - prev_votos) / prev_votos * 100
                if change_pct > threshold_pct:
                    dt_min = (m["ts"] - prev["ts"]).total_seconds() / 60
                    alerts.append({
                        "rule": "snapshot_jump",
                        "severity": "CRITICAL",
                        "ts": m["ts"].isoformat(),
                        "file": m["file"],
                        "message": (
                            f"Salto del {change_pct:.1f}% en votos de '{partido[:30]}' "
                            f"({prev_votos:,} → {votos:,}) en {dt_min:.0f} min."
                        ),
                        "value": {
                            "partido": partido,
                            "before": prev_votos,
                            "after": votos,
                            "change_pct": change_pct,
                            "interval_minutes": dt_min,
                        },
                    })
        prev = m
    return alerts


def detect_irreversibility(metrics: list[dict]) -> list[dict]:
    """Detecta votos que disminuyen entre snapshots (irreversibilidad violada)."""
    alerts = []
    prev = None
    for m in metrics:
        if m["blackout"] or m["total_votos"] == 0:
            prev = m
            continue
        if prev and not prev["blackout"] and prev["total_votos"] > 0:
            for partido, votos in m["votos_por_partido"].items():
                prev_votos = prev["votos_por_partido"].get(partido, 0)
                if votos < prev_votos:
                    delta = votos - prev_votos
                    alerts.append({
                        "rule": "irreversibility",
                        "severity": "CRITICAL",
                        "ts": m["ts"].isoformat(),
                        "file": m["file"],
                        "message": (
                            f"VOTOS DECRECEN: '{partido[:30]}' perdió {abs(delta):,} votos "
                            f"({prev_votos:,} → {votos:,}). Los votos son irreversibles."
                        ),
                        "value": {
                            "partido": partido,
                            "before": prev_votos,
                            "after": votos,
                            "delta": delta,
                        },
                    })
        prev = m
    return alerts


def detect_null_blank_anomaly(
    metrics: list[dict], warning_pct: float = 8.0, critical_pct: float = 12.0
) -> list[dict]:
    """Detecta % de nulos+blancos fuera de rango histórico."""
    alerts = []
    for m in metrics:
        if m["blackout"] or m["total_votos"] == 0:
            continue
        pct = m["pct_nulos_blancos"] * 100
        if pct >= critical_pct:
            alerts.append({
                "rule": "null_blank_votes",
                "severity": "CRITICAL",
                "ts": m["ts"].isoformat(),
                "file": m["file"],
                "message": f"Nulos+blancos={pct:.2f}% supera umbral crítico ({critical_pct}%).",
                "value": {"pct_null_blank": pct, "threshold_critical": critical_pct},
            })
        elif pct >= warning_pct:
            alerts.append({
                "rule": "null_blank_votes",
                "severity": "WARNING",
                "ts": m["ts"].isoformat(),
                "file": m["file"],
                "message": f"Nulos+blancos={pct:.2f}% supera umbral de aviso ({warning_pct}%).",
                "value": {"pct_null_blank": pct, "threshold_warning": warning_pct},
            })
    return alerts


def detect_processing_speed(
    metrics: list[dict], max_actas_per_15min: int = 500
) -> list[dict]:
    """Detecta velocidad de procesamiento anómala (actas/15 min)."""
    alerts = []
    prev = None
    for m in metrics:
        if prev:
            delta_actas = m["actas_divulgadas"] - prev["actas_divulgadas"]
            delta_min = (m["ts"] - prev["ts"]).total_seconds() / 60
            if delta_min > 0:
                rate_per_15min = delta_actas / delta_min * 15
                if rate_per_15min > max_actas_per_15min and delta_actas > 0:
                    alerts.append({
                        "rule": "processing_speed",
                        "severity": "High",
                        "ts": m["ts"].isoformat(),
                        "file": m["file"],
                        "message": (
                            f"Velocidad={rate_per_15min:.0f} actas/15min "
                            f"(umbral={max_actas_per_15min}). "
                            f"Δactas={delta_actas:+,} en {delta_min:.0f} min."
                        ),
                        "value": {
                            "rate_per_15min": rate_per_15min,
                            "delta_actas": delta_actas,
                            "interval_minutes": delta_min,
                        },
                    })
        prev = m
    return alerts


def detect_inconsistency_spike(metrics: list[dict], critical_pct: float = 10.0) -> list[dict]:
    """Detecta % actas inconsistentes > umbral crítico."""
    alerts = []
    for m in metrics:
        if m["actas_divulgadas"] == 0:
            continue
        pct = m["pct_inconsistentes"] * 100
        if pct >= critical_pct:
            alerts.append({
                "rule": "inconsistency_rate",
                "severity": "CRITICAL",
                "ts": m["ts"].isoformat(),
                "file": m["file"],
                "message": (
                    f"Actas inconsistentes={m['inconsistentes']:,} "
                    f"({pct:.1f}% del total divulgado). "
                    f"Umbral crítico: {critical_pct}%."
                ),
                "value": {
                    "inconsistentes": m["inconsistentes"],
                    "pct_inconsistentes": pct,
                    "threshold": critical_pct,
                },
            })
    return alerts


def detect_trend_reversal_at_blackout(metrics: list[dict]) -> list[dict]:
    """Detecta si la brecha líder-segundo cambia de dirección durante/después del blackout."""
    alerts = []
    pre_blackout_gap = None
    post_blackout_gap = None
    blackout_found = False

    for m in metrics:
        if m["blackout"]:
            blackout_found = True
            continue
        if m["total_votos"] == 0:
            continue

        sorted_votos = sorted(m["votos_por_partido"].values(), reverse=True)
        if len(sorted_votos) < 2:
            continue
        gap = sorted_votos[0] - sorted_votos[1]

        if not blackout_found:
            pre_blackout_gap = {"gap": gap, "ts": m["ts"], "file": m["file"]}
        else:
            if post_blackout_gap is None:
                post_blackout_gap = {"gap": gap, "ts": m["ts"], "file": m["file"]}

    if pre_blackout_gap and post_blackout_gap:
        gap_change = post_blackout_gap["gap"] - pre_blackout_gap["gap"]
        gap_change_pct = gap_change / pre_blackout_gap["gap"] * 100 if pre_blackout_gap["gap"] > 0 else 0
        if abs(gap_change_pct) > 50:
            alerts.append({
                "rule": "trend_reversal_at_blackout",
                "severity": "CRITICAL",
                "ts": post_blackout_gap["ts"].isoformat(),
                "file": post_blackout_gap["file"],
                "message": (
                    f"REVERSIÓN DE TENDENCIA POST-BLACKOUT: "
                    f"brecha lider-segundo cambió de {pre_blackout_gap['gap']:,} → "
                    f"{post_blackout_gap['gap']:,} votos "
                    f"({gap_change_pct:+.1f}%) durante el periodo de opacidad."
                ),
                "value": {
                    "gap_before_blackout": pre_blackout_gap["gap"],
                    "gap_after_blackout": post_blackout_gap["gap"],
                    "gap_change": gap_change,
                    "gap_change_pct": gap_change_pct,
                },
            })
    return alerts


# ── Reporte ────────────────────────────────────────────────────────────────

def build_summary_table(metrics: list[dict]) -> list[dict]:
    """Construye tabla de serie temporal para el reporte."""
    rows = []
    prev = None
    for m in metrics:
        sorted_v = sorted(m["votos_por_partido"].items(), key=lambda x: -x[1])
        lider = sorted_v[0] if sorted_v else ("?", 0)
        segundo = sorted_v[1] if len(sorted_v) > 1 else ("?", 0)
        gap = lider[1] - segundo[1]

        delta_actas = 0
        delta_gap = 0
        if prev and not prev["blackout"]:
            delta_actas = m["actas_divulgadas"] - prev["actas_divulgadas"]
            prev_gap = sorted(prev["votos_por_partido"].values(), reverse=True)
            prev_gap_val = prev_gap[0] - prev_gap[1] if len(prev_gap) >= 2 else 0
            delta_gap = gap - prev_gap_val

        rows.append({
            "ts": m["ts"].isoformat(),
            "file": m["file"],
            "actas_divulgadas": m["actas_divulgadas"],
            "pct_escrutinio": round(m["pct_escrutinio"] * 100, 2),
            "lider": lider[0][:40],
            "votos_lider": lider[1],
            "segundo": segundo[0][:40],
            "votos_segundo": segundo[1],
            "brecha": gap,
            "delta_actas": delta_actas,
            "delta_brecha": delta_gap,
            "inconsistentes": m["inconsistentes"],
            "pct_nulos_blancos": round(m["pct_nulos_blancos"] * 100, 2),
            "blackout": m["blackout"],
        })
        prev = m
    return rows


def write_markdown_report(
    alerts: list[dict],
    summary: list[dict],
    output_path: Path,
) -> None:
    critical = [a for a in alerts if a["severity"] == "CRITICAL"]
    high = [a for a in alerts if a["severity"] == "High"]
    warnings = [a for a in alerts if a["severity"] == "WARNING"]

    lines = [
        "# Reporte de Calibración Centinel — Honduras 2025",
        "",
        f"**Fecha de análisis:** {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC",
        f"**Snapshots analizados:** {len(summary)}",
        f"**Alertas totales:** {len(alerts)} "
        f"(🔴 {len(critical)} CRITICAL · 🟠 {len(high)} HIGH · 🟡 {len(warnings)} WARNING)",
        "",
        "---",
        "",
        "## Resumen Ejecutivo",
        "",
    ]

    # Rango temporal
    if summary:
        lines += [
            f"- **Inicio serie:** {summary[0]['ts'][:16]}",
            f"- **Fin serie:** {summary[-1]['ts'][:16]}",
            f"- **Escrutinio máximo:** {max(r['pct_escrutinio'] for r in summary):.2f}%",
            "",
        ]

    lines += [
        "---",
        "",
        "## Alertas por Severidad",
        "",
        "### 🔴 CRITICAL",
        "",
    ]
    for a in critical:
        lines.append(f"- **[{a['rule']}]** `{a['ts'][:16]}` — {a['message']}")
    if not critical:
        lines.append("_(ninguna)_")

    lines += ["", "### 🟠 HIGH", ""]
    for a in high:
        lines.append(f"- **[{a['rule']}]** `{a['ts'][:16]}` — {a['message']}")
    if not high:
        lines.append("_(ninguna)_")

    lines += ["", "### 🟡 WARNING", ""]
    for a in warnings:
        lines.append(f"- **[{a['rule']}]** `{a['ts'][:16]}` — {a['message']}")
    if not warnings:
        lines.append("_(ninguna)_")

    lines += [
        "",
        "---",
        "",
        "## Serie Temporal Completa",
        "",
        "| Timestamp | % Escrutinio | Δ Actas | Brecha | Δ Brecha | Inconsistentes | Nulos+Blancos% | Blackout |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in summary:
        flag = "🚨" if r["blackout"] else ""
        lines.append(
            f"| {r['ts'][:16]} | {r['pct_escrutinio']}% | {r['delta_actas']:+,} | "
            f"{r['brecha']:,} | {r['delta_brecha']:+,} | {r['inconsistentes']:,} | "
            f"{r['pct_nulos_blancos']}% | {flag} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Notas de Calibración",
        "",
        "Los umbrales usados en este análisis corresponden a los valores en `command_center/rules.yaml`.",
        "Tras revisar los resultados, ajustar umbrales en el YAML para reducir falsos positivos.",
        "",
        "| Regla | Umbral usado | Alertas generadas | Recomendación |",
        "|---|---|---|---|",
        "| `snapshot_jump` | 5% en 10 min | — | Calibrar con datos normales |",
        "| `null_blank_votes` | warning=8%, critical=12% | — | Revisar % real de este dataset |",
        "| `processing_speed` | 500 actas/15min | — | Ajustar si hay lotes legítimos |",
        "| `inconsistency_rate` | 10% | — | Honduras 2025: ~14.4% final |",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrar reglas Centinel contra JSON CNE 2025")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("/home/user/hnd-electoral-audit-2025/data"),
        help="Directorio con los JSON del CNE",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Directorio de salida para reportes",
    )
    args = parser.parse_args()

    if not args.data.exists():
        sys.exit(f"[ERROR] Directorio no encontrado: {args.data}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Cargando snapshots desde {args.data}...")
    snapshots = load_snapshots(args.data)
    print(f"      {len(snapshots)} snapshots cargados")

    print("[2/4] Extrayendo métricas...")
    metrics = [extract_metrics(s) for s in snapshots]

    print("[3/4] Ejecutando detectores...")
    alerts = []
    alerts += detect_universe_mutation(metrics)
    alerts += detect_blackout(metrics)
    alerts += detect_snapshot_jumps(metrics, threshold_pct=5.0)
    alerts += detect_irreversibility(metrics)
    alerts += detect_null_blank_anomaly(metrics, warning_pct=8.0, critical_pct=12.0)
    alerts += detect_processing_speed(metrics, max_actas_per_15min=500)
    alerts += detect_inconsistency_spike(metrics, critical_pct=10.0)
    alerts += detect_trend_reversal_at_blackout(metrics)
    alerts.sort(key=lambda a: a["ts"])

    summary = build_summary_table(metrics)

    print(f"[4/4] Escribiendo reportes en {args.output_dir}/...")
    json_out = args.output_dir / "calibration_2025.json"
    json_out.write_text(
        json.dumps({"alerts": alerts, "summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_out = args.output_dir / "calibration_2025.md"
    write_markdown_report(alerts, summary, md_out)

    critical = sum(1 for a in alerts if a["severity"] == "CRITICAL")
    high = sum(1 for a in alerts if a["severity"] == "High")
    warnings = sum(1 for a in alerts if a["severity"] == "WARNING")

    print()
    print("=" * 60)
    print(f"  ALERTAS: {len(alerts)} total")
    print(f"    🔴 CRITICAL: {critical}")
    print(f"    🟠 HIGH:     {high}")
    print(f"    🟡 WARNING:  {warnings}")
    print(f"  Reportes: {json_out}")
    print(f"            {md_out}")
    print("=" * 60)


if __name__ == "__main__":
    main()
