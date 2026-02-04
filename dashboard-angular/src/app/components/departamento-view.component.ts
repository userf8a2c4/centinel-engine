import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import { DepartamentoSnapshot } from '../services/types';

/**
 * Vista detallada para un departamento específico.
 * Detailed view for a specific department.
 */
@Component({
  selector: 'app-departamento-view',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  templateUrl: './departamento-view.component.html',
  styleUrls: ['./departamento-view.component.css'],
})
export class DepartamentoViewComponent {
  /**
   * Snapshot actual del departamento.
   * Current snapshot for the department.
   */
  @Input({ required: true }) departamento!: DepartamentoSnapshot;

  /**
   * Configuración del gráfico de línea para tendencias.
   * Line chart configuration for trends.
   */
  get chartConfig(): ChartConfiguration<'line'> {
    return {
      type: 'line',
      data: {
        labels: ['T-1', 'T0'],
        datasets: [
          {
            data: [0, this.departamento?.total ?? 0],
            label: 'Total agregado',
            borderColor: '#1b5e20',
          },
        ],
      },
    };
  }
}
