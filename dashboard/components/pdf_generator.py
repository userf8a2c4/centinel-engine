# dashboard/components/pdf_generator.py
# Generación de PDF - con fix para buffer y mime
# Español / English: Generación de PDF corregida / Fixed PDF generation

from fpdf import FPDF
from io import BytesIO
from datetime import datetime

def create_pdf(df, deptos_sel, date_range, partidos_sel):
    """Genera PDF con resumen del análisis.
    
    Args:
        df: DataFrame filtrado
        deptos_sel: Lista de departamentos seleccionados
        date_range: Tupla de fechas
        partidos_sel: Lista de partidos seleccionados
    
    Returns:
        bytes: Contenido del PDF listo para download
    
    ---
    Generates PDF with analysis summary.
    
    Args:
        df: Filtered DataFrame
        deptos_sel: Selected departments list
        date_range: Date range tuple
        partidos_sel: Selected parties list
    
    Returns:
        bytes: PDF content ready for download
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Análisis Personalizado - Sentinel", ln=1, align='C')
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 10, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1)
    pdf.ln(5)
    
    pdf.cell(0, 8, f"Rango: {date_range[0]} a {date_range[1]}", ln=1)
    pdf.cell(0, 8, f"Departamentos: {', '.join(deptos_sel)}", ln=1)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Resumen Último Snapshot", ln=1)
    pdf.set_font("Helvetica", "", 11)
    
    ultimo = df.iloc[-1]
    pdf.cell(0, 8, f"Total Votos: {ultimo['total_votos']:,}", ln=1)
    for p in partidos_sel:
        porc = ultimo[p] / ultimo['total_votos'] * 100 if ultimo['total_votos'] > 0 else 0
        pdf.cell(0, 8, f"{p}: {ultimo[p]:,} ({porc:.1f}%)", ln=1)
    
    pdf.ln(15)
    pdf.set_font("Helvetica", "I", 10)
    pdf.multi_cell(0, 8, "Sentinel: herramienta independiente y neutral.\n"
                         "Solo datos públicos del CNE.\n"
                         "Código: https://github.com/userf8a2c4/sentinel")
    
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)  # ¡Clave! Resetear posición al inicio
    return buffer.getvalue()  # Retornar bytes directamente
