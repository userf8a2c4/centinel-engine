import { Injectable, signal } from '@angular/core';

/**
 * Alerta simple emitida por las reglas de auditoría.
 * Simple alert emitted by audit rules.
 */
export interface AlertaAuditoria {
  nivel: 'info' | 'warning' | 'critical';
  mensaje: string;
  timestamp: string;
}

/**
 * Servicio centralizado para alertas provenientes de diffs y anomalías.
 * Centralized service for alerts from diffs and anomalies.
 */
@Injectable({ providedIn: 'root' })
export class AlertasService {
  /**
   * Lista reactiva de alertas actuales.
   * Reactive list of current alerts.
   */
  readonly alertas = signal<AlertaAuditoria[]>([]);

  /**
   * Agrega una alerta a la cola visible.
   * Adds an alert to the visible queue.
   */
  push(alerta: AlertaAuditoria): void {
    this.alertas.update((actuales) => [alerta, ...actuales].slice(0, 50));
  }

  /**
   * Limpia el listado de alertas.
   * Clears the alert list.
   */
  clear(): void {
    this.alertas.set([]);
  }
}
