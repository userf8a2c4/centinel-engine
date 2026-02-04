import { Injectable } from '@angular/core';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { AuditoriaSnapshot } from './types';

/**
 * Servicio para generar reportes PDF reproducibles con jsPDF + autoTable.
 * Service to generate reproducible PDF reports with jsPDF + autoTable.
 */
@Injectable({ providedIn: 'root' })
export class PdfGeneratorService {
  /**
   * Genera un reporte PDF formal con portada, métricas y metodología.
   * Generates a formal PDF report with cover, metrics, and methodology.
   */
  generarReporte(snapshot: AuditoriaSnapshot): void {
    const pdf = new jsPDF({ unit: 'pt', format: 'a4' });

    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(18);
    pdf.text('Centinel - Reporte de Auditoría Electoral', 40, 60);

    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(12);
    pdf.text(`Fecha: ${snapshot.actualizadoEn}`, 40, 90);
    pdf.text(`Hash nacional: ${snapshot.nacional.hash}`, 40, 110);
    pdf.text(
      'Este reporte utiliza únicamente JSON público departamental y nacional del CNE Honduras.',
      40,
      140
    );
    pdf.text(
      'This report uses only public departmental and national JSON from CNE Honduras.',
      40,
      160
    );

    autoTable(pdf, {
      startY: 200,
      head: [['Departamento', 'Total', 'Diff', 'Hash']],
      body: snapshot.departamentos.map((dep) => [
        dep.nombre,
        dep.total.toLocaleString(),
        dep.diff.toLocaleString(),
        dep.hash,
      ]),
    });

    const finalY = (pdf as unknown as { lastAutoTable: { finalY: number } })
      .lastAutoTable.finalY;

    pdf.text('Metodología / Methodology', 40, finalY + 40);
    pdf.setFontSize(10);
    pdf.text(
      'ES: Se verifican hashes encadenados, diffs objetivos y reglas configurables en rules.yaml.',
      40,
      finalY + 60
    );
    pdf.text(
      'EN: Chained hashes, objective diffs, and configurable rules in rules.yaml are verified.',
      40,
      finalY + 74
    );
    pdf.text(
      'ES: P-values reservados para validaciones estadísticas futuras por equipos técnicos.',
      40,
      finalY + 88
    );
    pdf.text(
      'EN: P-values reserved for future statistical validation by technical teams.',
      40,
      finalY + 102
    );
    pdf.text(
      'ES: Este informe es neutral y no interpreta resultados, solo registra trazabilidad.',
      40,
      finalY + 116
    );
    pdf.text(
      'EN: This report is neutral and does not interpret results, only records traceability.',
      40,
      finalY + 130
    );

    pdf.save('centinel-auditoria.pdf');
  }
}
