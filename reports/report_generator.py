"""ES: Generador institucional de reportes para C.E.N.T.I.N.E.L.

EN: Institutional report generator for C.E.N.T.I.N.E.L.

Este módulo concentra la lógica de exportación para que la UI de Streamlit
mantenga responsabilidades claras. Incluye:
- Ensamblado de metadatos de auditoría (hash, firma, timestamp).
- Exportación de payload JSON de audit trail.
- Generación de PDF formal con secciones institucionales (OEA/UE/Carter style).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import io
import json
from dataclasses import dataclass
from typing import Any

import pandas as pd

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    REPORTLAB_AVAILABLE = False


@dataclass(frozen=True)
class InstitutionalReportContext:
    """ES: Contexto tipado para construir un reporte institucional.

    EN: Typed context used to build an institutional report.

    Attributes:
        generated_at_utc: Fecha/hora UTC de emisión del reporte.
        snapshot_hash: Hash del snapshot seleccionado para trazabilidad.
        root_hash: Hash raíz auditado/anclado para cadena de custodia.
        source_label: Etiqueta de fuente oficial (ej. JSON oficial CNE).
        generated_by: Usuario o actor que dispara la exportación.
        report_scope: Alcance del reporte (nacional o departamento).
    """

    generated_at_utc: dt.datetime
    snapshot_hash: str
    root_hash: str
    source_label: str
    generated_by: str
    report_scope: str


def build_snapshot_hash(snapshot_df: pd.DataFrame) -> str:
    """ES: Construye hash SHA-256 determinístico del snapshot filtrado.

    EN: Build a deterministic SHA-256 hash for the filtered snapshot.
    """
    serialized = snapshot_df.sort_index(axis=1).to_json(orient="records", date_format="iso")
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_report_signature(snapshot_hash: str, root_hash: str, generated_at_iso: str) -> str:
    """ES: Genera firma criptográfica HMAC-SHA256 del documento.

    EN: Generate document cryptographic signature using HMAC-SHA256.

    Nota/Note:
        Esta firma ofrece integridad criptográfica de reporte dentro de la app.
        The signature provides report-level cryptographic integrity in-app.
    """
    secret = (root_hash or "CENTINEL-INSTITUTIONAL-DEFAULT").encode("utf-8")
    payload = f"{snapshot_hash}|{root_hash}|{generated_at_iso}".encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def build_audit_trail_payload(
    context: InstitutionalReportContext,
    metrics: dict[str, Any],
    anomalies: list[dict[str, Any]],
) -> dict[str, Any]:
    """ES: Construye payload JSON de auditoría listo para descarga.

    EN: Build audit JSON payload ready for download.
    """
    generated_iso = context.generated_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    signature = build_report_signature(context.snapshot_hash, context.root_hash, generated_iso)
    return {
        "institution": "C.E.N.T.I.N.E.L.",
        "generated_at_utc": generated_iso,
        "source": context.source_label,
        "generated_by": context.generated_by,
        "scope": context.report_scope,
        "snapshot_hash": context.snapshot_hash,
        "root_hash": context.root_hash,
        "metrics_summary": metrics,
        "anomalies_with_evidence": anomalies,
        "cryptographic_signature": signature,
        "methodology": {
            "es": "Auditoría técnica de series temporales y consistencia topológica sobre JSON oficial CNE.",
            "en": "Technical audit over temporal series and topology consistency from official CNE JSON.",
        },
    }


def export_audit_trail_json(payload: dict[str, Any]) -> str:
    """ES: Serializa el audit trail en JSON legible.

    EN: Serialize audit trail payload as human-readable JSON.
    """
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_story(
    context: InstitutionalReportContext,
    metrics: dict[str, Any],
    anomaly_rows: list[list[str]],
    cryptographic_signature: str,
) -> list[Any]:
    """ES: Construye el flujo de páginas/elementos para el PDF.

    EN: Build the PDF story (pages/elements).
    """
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CentinelTitle", parent=styles["Heading1"], fontSize=19, textColor=colors.HexColor("#0B1F3B"))
    section_style = ParagraphStyle("CentinelSection", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#163A63"))
    body_style = styles["BodyText"]

    generated_label = context.generated_at_utc.strftime("%Y-%m-%d %H:%M UTC")
    story: list[Any] = []
    story.append(Paragraph("C.E.N.T.I.N.E.L. / OEA · EU EOM · Carter Center", title_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Informe Institucional de Auditoría Electoral / Institutional Electoral Audit Report", body_style))
    story.append(Spacer(1, 0.5 * cm))

    cover_table = Table(
        [
            ["Fecha y hora / Date & Time", generated_label],
            ["Ámbito / Scope", context.report_scope],
            ["Fuente / Source", context.source_label],
            ["Hash snapshot", context.snapshot_hash],
            ["Hash raíz / Root hash", context.root_hash],
            ["Firma criptográfica / Signature", cryptographic_signature],
        ],
        colWidths=[5.2 * cm, 10.8 * cm],
    )
    cover_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94A3B8")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(cover_table)
    story.append(PageBreak())

    # ES/EN: Tabla de contenido institucional resumida.
    story.append(Paragraph("Tabla de Contenido / Table of Contents", section_style))
    story.append(Paragraph("1. Resumen de Métricas / Metrics Summary", body_style))
    story.append(Paragraph("2. Listado de Anomalías con Evidencia / Anomalies with Evidence", body_style))
    story.append(Paragraph("3. Firmas Digitales y Verificación / Digital Signatures", body_style))
    story.append(Paragraph("4. Metodología / Methodology", body_style))
    story.append(PageBreak())

    story.append(Paragraph("1. Resumen de Métricas / Metrics Summary", section_style))
    metric_rows = [["Métrica / Metric", "Valor / Value"]] + [[str(k), str(v)] for k, v in metrics.items()]
    metric_table = Table(metric_rows, colWidths=[8.0 * cm, 8.0 * cm])
    metric_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3B")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]))
    story.append(metric_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("2. Listado de Anomalías con Evidencia / Anomalies with Evidence", section_style))
    if len(anomaly_rows) == 1:
        anomaly_rows.append(["Sin anomalías / No anomalies", "-", "-", "-", "-"])
    anomalies_table = Table(anomaly_rows, repeatRows=1)
    anomalies_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    story.append(anomalies_table)
    story.append(PageBreak())

    story.append(Paragraph("3. Firmas Digitales / Digital Signatures", section_style))
    story.append(Paragraph(f"Firma criptográfica (HMAC-SHA256): <font name='Courier'>{cryptographic_signature}</font>", body_style))
    story.append(Paragraph("Firmas institucionales esperadas / Expected institutional signatures:", body_style))
    story.append(Spacer(1, 0.4 * cm))
    signature_lines = Table(
        [["Representante OEA / OAS", "Representante UE / EU", "Carter Center Liaison"]],
        colWidths=[5.3 * cm, 5.3 * cm, 5.3 * cm],
        rowHeights=[2.2 * cm],
    )
    signature_lines.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    story.append(signature_lines)
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("4. Metodología / Methodology", section_style))
    story.append(
        Paragraph(
            "ES: El documento resume el monitoreo de integridad sobre snapshots oficiales JSON CNE, "
            "incluyendo consistencia temporal, validación topológica y detección de anomalías estadísticas.<br/>"
            "EN: This document summarizes integrity monitoring over official CNE JSON snapshots, "
            "including temporal consistency, topology validation, and statistical anomaly detection.",
            body_style,
        )
    )
    return story


def generate_institutional_pdf_report(
    context: InstitutionalReportContext,
    metrics: dict[str, Any],
    anomaly_rows: list[list[str]],
) -> bytes:
    """ES: Genera PDF profesional institucional con estructura oficial.

    EN: Generate professional institutional PDF with official-grade layout.

    Raises:
        RuntimeError: si reportlab no está instalado.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is required for institutional PDF generation")

    generated_iso = context.generated_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    cryptographic_signature = build_report_signature(context.snapshot_hash, context.root_hash, generated_iso)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm)

    def _footer(canvas_obj: Any, _doc: Any) -> None:
        """ES: Footer institucional por página.

        EN: Institutional footer on every page.
        """
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.HexColor("#334155"))
        canvas_obj.drawString(1.8 * cm, 1.0 * cm, "C.E.N.T.I.N.E.L. – Auditoría Técnica Independiente")
        canvas_obj.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f"Página {canvas_obj.getPageNumber()}")
        canvas_obj.restoreState()

    story = _build_story(context, metrics, anomaly_rows, cryptographic_signature)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
