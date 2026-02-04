import { CommonModule } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import { PollingService } from '../services/polling.service';

/**
 * Vista nacional agregada del tablero.
 * National aggregate view of the dashboard.
 */
@Component({
  selector: 'app-nacional-view',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  templateUrl: './nacional-view.component.html',
  styleUrls: ['./nacional-view.component.css'],
})
export class NacionalViewComponent {
  private readonly pollingService = inject(PollingService);

  /**
   * Snapshot nacional actualizado desde el servicio de polling.
   * National snapshot updated from the polling service.
   */
  readonly nacional = computed(() => this.pollingService.nacional());

  /**
   * Configuración del gráfico para el total nacional.
   * Chart configuration for the national total.
   */
  get chartConfig(): ChartConfiguration<'bar'> {
    const nacional = this.nacional();
    return {
      type: 'bar',
      data: {
        labels: ['Total nacional'],
        datasets: [
          {
            data: [nacional.total],
            label: 'Total agregado',
            backgroundColor: '#0d47a1',
          },
        ],
      },
    };
  }
}
