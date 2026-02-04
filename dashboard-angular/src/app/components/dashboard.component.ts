import { CommonModule } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatTabsModule } from '@angular/material/tabs';
import { DepartamentoViewComponent } from './departamento-view.component';
import { NacionalViewComponent } from './nacional-view.component';
import { AlertasComponent } from './alertas.component';
import { PdfGeneratorService } from '../services/pdf-generator.service';
import { PollingService } from '../services/polling.service';

/**
 * Vista principal del dashboard con pestañas nacionales y departamentales.
 * Main dashboard view with national and departmental tabs.
 */
@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatTabsModule,
    DepartamentoViewComponent,
    NacionalViewComponent,
    AlertasComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent {
  private readonly pdfGenerator = inject(PdfGeneratorService);
  private readonly pollingService = inject(PollingService);

  /**
   * Señal computada para exponer los departamentos disponibles.
   * Computed signal to expose the available departments.
   */
  readonly departamentos = computed(() => this.pollingService.departamentos());

  /**
   * Dispara la exportación del PDF oficial para observadores.
   * Triggers export of the official PDF for observers.
   */
  exportarPdf(): void {
    this.pdfGenerator.generarReporte(this.pollingService.snapshot());
  }
}
