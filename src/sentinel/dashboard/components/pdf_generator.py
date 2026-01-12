"""English docstring: PDF generation utilities for the Sentinel dashboard.

---
Docstring en español: Utilidades de generación de PDF para el dashboard Sentinel.
"""

from __future__ import annotations

from datetime import date
import pandas as pd
from fpdf import FPDF

from sentinel.dashboard.utils.benford import benford_analysis
from sentinel.dashboard.utils.constants import BENFORD_THRESHOLD


def _format_filters(
    deptos: list[str],
    partidos: list[str],
    date_range: tuple[date, date],
) -> list[str]:
    """English docstring: Format filters for PDF output.

    Args:
        deptos: Selected departments.
        partidos: Selected parties.
        date_range: Selected date range.

    Returns:
        List of formatted filter strings.
    ---
    Docstring en español: Formatea filtros para la salida PDF.

    Args:
        deptos: Departamentos seleccionados.
        partidos: Partidos seleccionados.
        date_range: Rango de fechas seleccionado.

    Returns:
        Lista de cadenas formateadas.
    """

    start, end = date_range
    depto_label = ", ".join(deptos) if deptos else "Sin selección"
    partido_label = ", ".join(partidos) if partidos else "Sin selección"

    return [
        f"Departamentos: {depto_label}",
        f"Partidos: {partido_label}",
        f"Rango: {start.isoformat()} a {end.isoformat()}",
    ]


def create_pdf(
    df: pd.DataFrame,
    deptos: list[str],
    partidos: list[str],
    date_range: tuple[date, date],
) -> bytes:
    """English docstring: Create a PDF report with summary and Benford results.

    Args:
        df: Filtered dataframe.
        deptos: Selected departments.
        partidos: Selected parties.
        date_range: Selected date range.

    Returns:
        PDF bytes ready for download.
    ---
    Docstring en español: Crea un reporte PDF con resumen y resultados Benford.

    Args:
        df: Dataframe filtrado.
        deptos: Departamentos seleccionados.
        partidos: Partidos seleccionados.
        date_range: Rango de fechas seleccionado.

    Returns:
        Bytes del PDF listos para descargar.
    """

    pdf = FPDF()
    pdf.add_page()

    # Title section. / Sección de título.
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Sentinel - Reporte de Análisis", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Fecha de generación: {date.today().isoformat()}", ln=True)
    pdf.ln(2)

    # Filters section. / Sección de filtros.
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Filtros aplicados", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for line in _format_filters(deptos, partidos, date_range):
        pdf.cell(0, 6, f"- {line}", ln=True)
    pdf.ln(2)

    # Summary section. / Sección de resumen.
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Resumen último snapshot", ln=True)
    pdf.set_font("Helvetica", "", 11)

    if df.empty:
        pdf.multi_cell(0, 6, "No hay datos disponibles con los filtros actuales.")
    else:
        latest = df.iloc[-1]
        pdf.cell(0, 6, f"Total votos: {int(latest['total_votos']):,}", ln=True)
        for party in partidos:
            value = int(latest.get(party, 0))
            total = float(latest.get("total_votos", 0))
            pct = (value / total * 100) if total > 0 else 0
            pdf.cell(0, 6, f"{party}: {value:,} ({pct:.1f}%)", ln=True)
    pdf.ln(2)

    # Benford section. / Sección Benford.
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Integridad y Benford", ln=True)
    pdf.set_font("Helvetica", "", 11)

    observed, theoretical, deviation = benford_analysis(df["total_votos"]) if not df.empty else (None, None, None)

    if deviation is None:
        pdf.multi_cell(0, 6, "Datos insuficientes para análisis de Benford.")
    else:
        pdf.cell(0, 6, f"Desviación promedio: {deviation:.2f}%", ln=True)
        if deviation > BENFORD_THRESHOLD:
            pdf.multi_cell(0, 6, "Alerta: desviación superior al umbral esperado (posible anomalía).")
        else:
            pdf.multi_cell(0, 6, "Resultado dentro del rango esperado.")
    pdf.ln(2)

    # Disclaimer section. / Sección de disclaimer.
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Disclaimer", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0,
        5,
        "Este reporte es informativo y neutral, basado en datos públicos disponibles. "
        "No constituye resultados oficiales ni respaldo político. "
        "Repositorio: https://github.com/userf8a2c4/sentinel",
    )

    pdf_bytes = pdf.output(dest="S")
    # Ensure bytes output for download. / Asegurar salida en bytes para descarga.
    if isinstance(pdf_bytes, str):
        return pdf_bytes.encode("latin-1")
    if isinstance(pdf_bytes, bytearray):
        return bytes(pdf_bytes)
    return pdf_bytes
