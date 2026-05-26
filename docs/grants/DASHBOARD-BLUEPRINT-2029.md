# Centinel 2029 — World-Class Electoral Audit Dashboard Blueprint

## 1) Objetivo y principio rector

Diseñar una plataforma de auditoría electoral continua para Honduras 2029, neutral y agnóstica a partidos, basada exclusivamente en JSON públicos del CNE (sin actas/mesas), con ciclo operacional de actualización ≤5 minutos y trazabilidad verificable.

**Nombre oficial:**
- **Centinel – Centro de Vigilancia Electoral (C.E.N.T.I.N.E.L.)**

**Criterios institucionales:**
- Neutralidad política estricta.
- Rigor matemático explícito y auditable.
- Verificación criptográfica de snapshots.
- Transparencia metodológica para observación internacional (OEA, Carter Center, academia).

---

## 2) Stack recomendado (dos rutas)

## Ruta A (Frontend de referencia clase mundial)
- **Framework:** Next.js + React + TypeScript.
- **UI:** Tailwind CSS + componentes accesibles (Radix/UI o shadcn/ui).
- **Gráficas:** Recharts (rápido) + D3 para vistas forenses avanzadas.
- **Mapa:** Leaflet (react-leaflet) o Mapbox GL.
- **Animación:** Framer Motion (micro-interacciones sutiles).
- **Estado/queries:** TanStack Query + Zustand.
- **Accesibilidad:** enfoque WCAG 2.2 AA (contraste, foco, navegación teclado, lectores de pantalla).

## Ruta B (compatibilidad fuerte con ecosistema actual Python)
- **Framework:** Streamlit + Plotly + PyDeck/Folium.
- **Diseño:** CSS institucional inyectado, layout modular por tabs/páginas.
- **Back-end analítico:** pandas + scipy + statsmodels + utilidades crypto.
- **Reportes:** WeasyPrint/ReportLab.

---

## 3) Arquitectura de información (layout completo)

## 3.1 Header fijo (sticky)
- Logo C.E.N.T.I.N.E.L.
- Selector de idioma ES/EN.
- Timestamp UTC de último snapshot.
- Frecuencia polling (ejemplo: `Actualizado cada 4:52 min`).
- Estado global: `Stable / Investigating / Critical` con semáforo visual y texto explícito.
- Merkle root actual (clic para expandir cadena/prueba).
- Acción primaria: **Verificar en Arbitrum** (si L2 habilitado).

## 3.2 Sidebar no bloqueante
- Login seguro (sin bloquear lectura pública de panel general).
- Switch **Demo / Producción** visible.
- Selector de fuentes (reales vs dataset histórico 2025 para sandbox).
- Filtros globales: tiempo, departamento, candidato, severidad.
- Botones de export: PDF, CSV, JSON.

## 3.3 Cintillo KPI principal (cards grandes + sparkline)
1. Cobertura Activa.
2. Deltas Críticos.
3. Integridad Global.
4. Velocidad de Ingestión.
5. Alertas Abiertas.
6. Benford Conformity.

Cada card incluye:
- valor actual,
- variación vs ventana previa,
- sparkline 24h,
- tooltip metodológico.

## 3.4 Mapa interactivo nacional (Honduras)
- Choropleth/heatmap por departamento.
- Tooltip: votos acumulados, delta hora/hora, score de integridad, Benford score.
- Drill-down: mini-dashboard departamental.

## 3.5 Timeline interactivo avanzado
- Serie de votos por candidato (zoom/pan).
- Overlay de eventos anómalos con marcador y evidencia matemática.
- Vista paralela de Benford (1er/2do dígito) y KS statistic.
- Filtros por tiempo/departamento/candidato.

## 3.6 Módulo de análisis estadístico (tabs internas)
- Benford: histogramas expected vs observed.
- KS y chi-cuadrado con p-values.
- Outliers (IQR y z-score dinámico).
- Consistencia de agregación (suma depto vs nacional).
- Bayesian anomaly flag (posterior simplificada).
- QQ plots, boxplots, matriz de correlación.

## 3.7 Módulo criptográfico
- Cadena de hashes por snapshot.
- Merkle root vigente.
- Proof de inclusión por snapshot.
- Estado L2 Arbitrum (si aplica) + enlace de verificación.

## 3.8 Tablas forenses
- **Anomalías detectadas** (sortable/paginada): timestamp, depto, tipo, severidad, descripción matemática, evidencia diff JSON.
- **Snapshots recientes**: hash, delta global, score integridad, ver JSON, diff vs anterior.

## 3.9 Reportes institucionales
- PDF profesional con portada, resumen ejecutivo, KPIs, gráficos, metodología y firma hash.
- Export CSV/JSON con metadatos de verificación.
- Botón especializado: **Preparar Reporte para OEA/Carter Center**.

---

## 4) Modelo matemático recomendado

## 4.1 Integridad global (visible)

```text
Integridad Global = 0.40 * Cobertura + 0.30 * ConsistenciaDeltas + 0.30 * VerificacionCripto
```

Donde cada componente se normaliza a [0, 100].

## 4.2 Delta crítico
- Bandera crítica si `|z| > 2` (advertencia) y `|z| > 3` (crítica).
- Tooltip ejemplo: `Δ=-1234, z=-3.1, p=0.002`.

## 4.3 Benford + KS
- Benford 1er dígito: `P(d)=log10(1+1/d)`.
- Calcular distancia KS contra distribución observada y mostrar p-value.

## 4.4 Bayesian anomaly flag (modelo inicial)
- Variable latente simple con prior conservador.
- Posterior basada en evidencia combinada (z-score, KS, consistencia agregación).
- Mostrar como probabilidad calibrada con rangos interpretables.

---

## 5) UX, estilo y accesibilidad

- Dark mode premium:
  - Azul profundo `#0f172a`
  - Verde integridad `#10b981`
  - Rojo alerta `#ef4444`
- Tipografía: Inter (fallback Roboto/system-ui).
- Animaciones discretas (<200ms), sin distraer.
- Mobile-first para observadores de campo.
- WCAG 2.2 AA:
  - contraste,
  - foco visible,
  - navegación teclado,
  - etiquetas ARIA,
  - tooltips accesibles.

---

## 6) Innovación operacional

- Alertas AI-driven con umbrales dinámicos por varianza histórica 2025.
- Simulador what-if (impacto de alteraciones hipotéticas sobre score global).
- Publicación futura de roots/hashes en blockchain como evidencia pública inmutable.
- Modo Observador Internacional (vista simplificada: KPIs + mapa + timeline + alertas críticas).

---

## 7) Componentes sugeridos (React)

- `AppShell`
- `TopHeader`
- `StatusBadge`
- `LanguageSwitcher`
- `KpiGrid` / `KpiCard`
- `HondurasIntegrityMap`
- `AdvancedTimeline`
- `BenfordPanel`
- `StatisticalTestsPanel`
- `CryptoChainPanel`
- `AnomaliesTable`
- `SnapshotsTable`
- `InstitutionalReportBuilder`
- `ObserverModePanel`

---

## 8) Componentes sugeridos (Python/Streamlit)

- `render_header()`
- `render_sidebar_controls()`
- `render_kpi_cards()`
- `render_honduras_map()`
- `render_timeline_advanced()`
- `render_statistical_analysis()`
- `render_crypto_verification_panel()`
- `render_anomalies_table()`
- `render_snapshots_table()`
- `render_reporting_exports()`
- `render_observer_mode()`

---

## 9) Código base sugerido (esqueleto React + Tailwind)

```tsx
export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-900 text-slate-100">
      <TopHeader />
      <div className="grid grid-cols-1 xl:grid-cols-[320px_1fr] gap-4 p-4">
        <SidebarControls />
        <section className="space-y-4">
          <KpiGrid />
          <div className="grid grid-cols-1 2xl:grid-cols-2 gap-4">
            <HondurasIntegrityMap />
            <AdvancedTimeline />
          </div>
          <StatisticalTabs />
          <CryptoChainPanel />
          <AnomaliesTable />
          <SnapshotsTable />
          <InstitutionalReportBuilder />
        </section>
      </div>
    </main>
  );
}
```

---

## 10) Plan de implementación por fases

1. **Fase 1 (base robusta):** header/sidebar/KPIs/timeline + tablas de snapshots/anomalías.
2. **Fase 2 (estadística avanzada):** Benford+KS+chi²+outliers+agregación.
3. **Fase 3 (crypto y evidencia):** Merkle/proofs/L2 verification + exports institucionales.
4. **Fase 4 (modo internacional y AI):** observer mode + alertas dinámicas + simulador what-if.

---

## 11) Criterios de aceptación (nivel internacional)

- Polling efectivo ≤5 min sin degradación visual.
- Metodología estadística explícita y reproducible.
- Export institucional verificable (hash + timestamp + metadata).
- Trazabilidad criptográfica navegable por snapshot.
- Experiencia bilingüe accesible WCAG 2.2 AA.
- Neutralidad textual y visual en todo el producto.
