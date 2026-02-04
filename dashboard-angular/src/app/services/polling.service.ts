import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { interval, of, timer } from 'rxjs';
import { catchError, retry, startWith, switchMap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AlertasService } from './alertas.service';
import { BackendApiService } from './backend-api.service';
import { AuditoriaSnapshot, DepartamentoSnapshot, NacionalSnapshot } from './types';

/**
 * Servicio de polling en tiempo real para JSON del CNE.
 * Real-time polling service for CNE JSON.
 */
@Injectable({ providedIn: 'root' })
export class PollingService {
  private readonly backendApi = inject(BackendApiService);
  private readonly alertas = inject(AlertasService);

  /**
   * Snapshot actual con datos nacionales y departamentales.
   * Current snapshot with national and departmental data.
   */
  private readonly snapshotSignal = signal<AuditoriaSnapshot>({
    actualizadoEn: new Date().toISOString(),
    nacional: { total: 0, hash: '-', diff: 0 },
    departamentos: [],
  });

  /**
   * Señal pública del snapshot.
   * Public snapshot signal.
   */
  readonly snapshot = this.snapshotSignal.asReadonly();

  /**
   * Señal nacional derivada.
   * Derived national signal.
   */
  readonly nacional = computed<NacionalSnapshot>(() => this.snapshotSignal().nacional);

  /**
   * Señal departamental derivada.
   * Derived departmental signal.
   */
  readonly departamentos = computed<DepartamentoSnapshot[]>(
    () => this.snapshotSignal().departamentos
  );

  constructor() {
    interval(environment.pollingIntervalMs)
      .pipe(
        startWith(0),
        switchMap(() =>
          this.backendApi.fetchSnapshot().pipe(
            retry({
              count: environment.pollingRetries,
              delay: (error, retryCount) =>
                timer(Math.min(1000 * 2 ** retryCount, 10000)),
            }),
            catchError((error) => {
              this.alertas.push({
                nivel: 'warning',
                mensaje: `Error de polling: ${error?.message ?? 'sin detalle'}`,
                timestamp: new Date().toISOString(),
              });
              return of(this.snapshotSignal());
            })
          )
        )
      )
      .subscribe((nuevoSnapshot) => this.actualizarSnapshot(nuevoSnapshot));

    effect(() => {
      const snapshot = this.snapshotSignal();
      if (snapshot.departamentos.length === 0) {
        this.alertas.push({
          nivel: 'info',
          mensaje: 'Esperando datos del backend Python.',
          timestamp: new Date().toISOString(),
        });
      }
    });
  }

  /**
   * Actualiza el snapshot y detecta diffs básicos.
   * Updates the snapshot and detects basic diffs.
   */
  private actualizarSnapshot(nuevoSnapshot: AuditoriaSnapshot): void {
    const anterior = this.snapshotSignal();
    if (anterior.nacional.hash !== nuevoSnapshot.nacional.hash) {
      this.alertas.push({
        nivel: 'warning',
        mensaje: 'Cambio detectado en hash nacional.',
        timestamp: new Date().toISOString(),
      });
    }

    this.snapshotSignal.set(nuevoSnapshot);
  }
}
