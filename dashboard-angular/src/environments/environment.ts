/**
 * Configuración de entorno para polling y API.
 * Environment configuration for polling and API.
 */
export const environment = {
  production: false,
  pollingIntervalMs: 300000,
  pollingRetries: 3,
  apiBaseUrl: 'http://localhost:8000',
  clientName: 'Centinel-Audit-Dashboard',
  clientUserAgent: 'Centinel-WebObserver/1.0',
};
