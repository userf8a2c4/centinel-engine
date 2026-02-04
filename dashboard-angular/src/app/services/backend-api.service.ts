import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuditoriaSnapshot } from './types';

/**
 * Servicio para conectar con el backend Python (polling JSON procesado).
 * Service to connect with the Python backend (processed JSON polling).
 */
@Injectable({ providedIn: 'root' })
export class BackendApiService {
  private readonly http = inject(HttpClient);

  /**
   * Obtiene el snapshot auditado desde el backend.
   * Fetches the audited snapshot from the backend.
   */
  fetchSnapshot(): Observable<AuditoriaSnapshot> {
    return this.http.get<AuditoriaSnapshot>(
      `${environment.apiBaseUrl}/audit/snapshot`
    );
  }
}
