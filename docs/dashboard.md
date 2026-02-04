# Dashboard Angular (CNE Honduras)

## Objetivo / Objective

**ES:** Migrar el dashboard Streamlit a Angular 17/18 con componentes standalone, polling en tiempo real cada 5 minutos configurable, alertas básicas de diffs/anomalías y reportes PDF formales para observadores internacionales (OEA/Carter Center). Este tablero consume únicamente JSON público departamental (18) y nacional del CNE Honduras.  
**EN:** Migrate the Streamlit dashboard to Angular 17/18 with standalone components, real-time polling every 5 minutes (configurable), basic diff/anomaly alerts, and formal PDF reports for international observers (OEA/Carter Center). The dashboard consumes only public departmental (18) and national JSON from CNE Honduras.

## Comandos de instalación / Setup commands

```bash
# Crear proyecto Angular (standalone)
ng new centinel-dashboard --standalone --style=css --routing=false

# Añadir Angular Material
ng add @angular/material

# Dependencias para PDF, charts y RxJS
npm i jspdf jspdf-autotable ng2-charts chart.js rxjs

# Testing e2e
npm i -D cypress
```

## Estructura propuesta / Proposed structure

```
dashboard-angular/
  src/
    app/
      app.component.ts
      components/
        dashboard.component.ts/html/css
        departamento-view.component.ts/html/css
        nacional-view.component.ts/html/css
        alertas.component.ts/html/css
      services/
        backend-api.service.ts
        polling.service.ts
        pdf-generator.service.ts
        alertas.service.ts
        http-headers.interceptor.ts
        types.ts
    environments/
      environment.ts
```

## Polling en tiempo real / Real-time polling

**ES:** `PollingService` utiliza RxJS `interval` + `HttpClient` para obtener JSON procesado desde el backend Python cada 5 minutos (`pollingIntervalMs`). Incluye `retry` con backoff y alertas cuando falla.  
**EN:** `PollingService` uses RxJS `interval` + `HttpClient` to fetch processed JSON from the Python backend every 5 minutes (`pollingIntervalMs`). It includes `retry` with backoff and alerts on failure.

## Alertas / Alerts

**ES:** `AlertasService` centraliza diffs/anomalías y `AlertasComponent` muestra lista + snackbars.  
**EN:** `AlertasService` centralizes diffs/anomalies and `AlertasComponent` shows list + snackbars.

## Reportes PDF / PDF reports

**ES:** `PdfGeneratorService` genera un PDF reproducible con portada, tabla departamental, metodología y disclaimer neutral. Se incluyen placeholders para p-values.  
**EN:** `PdfGeneratorService` generates a reproducible PDF with cover, departmental table, methodology, and neutral disclaimer. Placeholders for p-values are included.

## Integración con backend Python / Python backend integration

**ES:** `BackendApiService` apunta a `/audit/snapshot` y puede adaptarse a `scripts/run_pipeline.py` o endpoints futuros.  
**EN:** `BackendApiService` targets `/audit/snapshot` and can be adapted to `scripts/run_pipeline.py` or future endpoints.

## Testing / Tests

```bash
# Karma/Jasmine
ng test

# Cypress e2e (polling + export PDF)
ng e2e
```

## Deploy / Despliegue

**ES:** Para GitHub Pages o Vercel, compilar con `ng build --configuration=production` y publicar la carpeta `dist/`.  
**EN:** For GitHub Pages or Vercel, build with `ng build --configuration=production` and publish the `dist/` folder.
