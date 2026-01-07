"""Genera reporte PDF a partir de analysis_results.json y anomalies_report.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def build_pdf(
    output_path: Path, analysis_data: dict, anomalies_data: list[dict]
) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Falta dependencia 'reportlab'. Instala con: pip install reportlab"
        ) from exc

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    story = []

    generated_at = analysis_data.get("generated_at") or datetime.utcnow().isoformat() + "Z"
    story.append(Paragraph("Reporte de auditoría HND-SENTINEL-2029", styles["Title"]))
    story.append(Paragraph(f"Generado: {generated_at}", styles["Normal"]))
    story.append(Spacer(1, 12))

    departments = analysis_data.get("departments", {})
    story.append(Paragraph("Resumen por departamento", styles["Heading2"]))
    if departments:
        table_data = [["Departamento", "Métricas"]]
        for dept, metrics in departments.items():
            table_data.append([dept, safe_text(metrics)])
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No hay métricas disponibles.", styles["Italic"]))
    story.append(Spacer(1, 12))

    predictions = analysis_data.get("predictions", {})
    story.append(Paragraph("Predicciones", styles["Heading2"]))
    if predictions:
        for dept, payload in predictions.items():
            story.append(Paragraph(f"{dept}: {safe_text(payload)}", styles["Normal"]))
    else:
        story.append(Paragraph("No hay predicciones registradas.", styles["Italic"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Anomalías", styles["Heading2"]))
    if anomalies_data:
        anomaly_rows = [["Timestamp", "Descripción", "Detalles"]]
        for anomaly in anomalies_data:
            anomaly_rows.append(
                [
                    safe_text(anomaly.get("timestamp")),
                    safe_text(anomaly.get("descripcion") or anomaly.get("type")),
                    safe_text({k: v for k, v in anomaly.items() if k not in {"timestamp", "descripcion"}}),
                ]
            )
        anomaly_table = Table(anomaly_rows, hAlign="LEFT")
        anomaly_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(anomaly_table)
    else:
        story.append(Paragraph("No hay anomalías registradas.", styles["Italic"]))

    doc.build(story)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera reporte PDF desde JSONs.")
    parser.add_argument(
        "--analysis",
        type=Path,
        default=Path("analysis_results.json"),
        help="Ruta al analysis_results.json",
    )
    parser.add_argument(
        "--anomalies",
        type=Path,
        default=Path("anomalies_report.json"),
        help="Ruta al anomalies_report.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta de salida del PDF (por defecto reports/report_<timestamp>.pdf)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analysis_path = args.analysis
    anomalies_path = args.anomalies

    if not analysis_path.exists():
        raise SystemExit(f"No se encontró {analysis_path}")
    if not anomalies_path.exists():
        raise SystemExit(f"No se encontró {anomalies_path}")

    analysis_data = load_json(analysis_path)
    anomalies_data = load_json(anomalies_path)
    if not isinstance(anomalies_data, list):
        anomalies_data = []

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or reports_dir / f"report_{timestamp}.pdf"

    build_pdf(output_path, analysis_data, anomalies_data)

    latest_path = reports_dir / "latest_report.pdf"
    latest_path.write_bytes(output_path.read_bytes())
    print(f"Reporte generado: {output_path}")
    print(f"Reporte actualizado: {latest_path}")


if __name__ == "__main__":
    main()
