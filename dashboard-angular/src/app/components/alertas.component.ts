import { CommonModule } from '@angular/common';
import { Component, effect, inject } from '@angular/core';
import { MatListModule } from '@angular/material/list';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AlertasService } from '../services/alertas.service';

/**
 * Panel de alertas con snackbars para diffs/anomalías relevantes.
 * Alerts panel with snackbars for relevant diffs/anomalies.
 */
@Component({
  selector: 'app-alertas',
  standalone: true,
  imports: [CommonModule, MatListModule, MatSnackBarModule],
  templateUrl: './alertas.component.html',
  styleUrls: ['./alertas.component.css'],
})
export class AlertasComponent {
  private readonly alertasService = inject(AlertasService);
  private readonly snackBar = inject(MatSnackBar);

  /**
   * Alertas actuales como señal reactiva.
   * Current alerts as a reactive signal.
   */
  readonly alertas = this.alertasService.alertas;

  constructor() {
    effect(() => {
      const alerta = this.alertas()[0];
      if (alerta) {
        this.snackBar.open(alerta.mensaje, 'Cerrar', {
          duration: 8000,
          panelClass: [`alerta-${alerta.nivel}`],
        });
      }
    });
  }
}
