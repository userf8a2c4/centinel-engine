# Budget Narrative — Centinel Engine
## Narrativa de Presupuesto / OTF Grant Application

**Version:** 1.0 | **Date:** 2026-05-18 | **Grant target:** OTF Core Infrastructure Fund
**Period:** 12 months | **Requested:** $95,000 USD

---

## Español

### Resumen Ejecutivo del Presupuesto

Centinel Engine solicita $95,000 USD para financiar 12 meses de operación, calibración y
despliegue piloto en dos municipios de Honduras. El sistema ya existe y está operativo
($0 de construcción). Este presupuesto cubre exclusivamente:
1. Personal técnico de mantenimiento y calibración (costo principal)
2. Piloto con observadores en campo
3. Validación académica externa (UPNFM)
4. Infraestructura mínima de operación continua

El costo por elección monitorizada en producción es $0 en licencias y < $50/mes en
infraestructura (GitHub Actions + dominio). El presupuesto cubre el período de maduración
del sistema, no su construcción.

---

### Desglose por Categoría

#### 1. Personal / Personnel — $62,000 (65.3%)

| Rol | Tiempo | Tarifa mensual | Total |
|-----|--------|---------------|-------|
| Ingeniero principal (mantenimiento, calibración HN-2025, CI) | 12 meses × 50% | $2,500 | $30,000 |
| Investigador estadístico (validación FP rate, metodología UPNFM) | 12 meses × 25% | $1,500 | $18,000 |
| Coordinador de campo (piloto 2 municipios, capacitación observadores) | 6 meses × 100% | $1,200 | $7,200 |
| Revisor de seguridad externo (auditoría anual) | 1 audit | $6,800 | $6,800 |

**Justificación:** Las tarifas son consistentes con salarios de Honduras y la región para
profesionales técnicos senior. El ingeniero principal trabaja 50% porque el sistema ya
está construido — el tiempo cubre mantenimiento reactivo, calibración de umbrales post-2025
y soporte a observadores.

#### 2. Piloto Electoral / Field Pilot — $12,000 (12.6%)

| Item | Costo |
|------|-------|
| Laptops para 2 equipos de observación en campo (hardware) | $1,800 |
| Capacitación presencial de observadores (2 municipios × 2 días) | $3,200 |
| Viajes y logística (combustible, hospedaje, per diem) | $4,800 |
| Documentación del piloto y reporte público | $2,200 |

**Justificación:** El piloto en 2 municipios con resultados documentados públicamente es
el paso que transforma el sistema de "herramienta técnica" a "herramienta validada en campo".
Es el requisito más crítico para credibilidad ante Carter Center y OEA.

#### 3. Validación Académica / Academic Validation — $8,000 (8.4%)

| Item | Costo |
|------|-------|
| Convenio UPNFM — revisión de metodología estadística | $4,500 |
| Publicación académica (open-access journal, peer review) | $2,000 |
| Presentación en LAWOG o LASA 2026 | $1,500 |

**Justificación:** La validación de UPNFM convierte una herramienta técnica en una
herramienta con aval institucional universitario. OTF valora la independencia institucional.

#### 4. Infraestructura / Infrastructure — $6,500 (6.8%)

| Item | Costo anual |
|------|-------------|
| GitHub Teams (privado + Actions minutes) | $1,200 |
| Dominio + certificado TLS | $120 |
| Supabase Pro (base de datos del piloto) | $1,680 |
| Servidor de respaldo VPS (resiliencia) | $1,200 |
| OpenTimestamps + Bitcoin fees estimados | $300 |
| Contingencia de infraestructura (10%) | $2,000 |

**Justificación:** La infraestructura principal es GitHub Pages (costo $0). El VPS y
Supabase son para el período del piloto activo únicamente. En operación sin piloto,
el costo mensual de infraestructura es < $50.

#### 5. Comunicación y Diseminación / Communication — $6,500 (6.8%)

| Item | Costo |
|------|-------|
| Traducción profesional de documentación técnica (EN→ES, viceversa) | $2,000 |
| Diseño de materiales para observadores no-técnicos | $1,500 |
| Website de documentación pública (fuera de GitHub Pages) | $1,000 |
| Presentaciones en conferencias de sociedad civil centroamericana | $2,000 |

---

### Total por Categoría

| Categoría | Monto | % del Total |
|-----------|-------|------------|
| Personal | $62,000 | 65.3% |
| Piloto en campo | $12,000 | 12.6% |
| Validación académica | $8,000 | 8.4% |
| Infraestructura | $6,500 | 6.8% |
| Comunicación | $6,500 | 6.8% |
| **TOTAL** | **$95,000** | **100%** |

---

### Por Qué Este Presupuesto es Eficiente

**Lo que NO se paga con este grant:**
- Desarrollo del sistema (ya existe, AGPL-3.0)
- Licencias de software (todas las dependencias son open-source)
- Servidores propietarios (GitHub Pages es gratuito indefinidamente)
- Consultoría de marketing o comunicaciones institucionales

**Ratio de impacto:** $95,000 / 2.5M votos monitorizados = $0.038 por voto en Honduras.
En contraste, soluciones propietarias como Scytl o ES&S cobran $0.50–$2.00 por voto en
contratos de monitoreo similares — una diferencia de 13–53x.

**Sostenibilidad post-grant:** El sistema opera con $50/mes de infraestructura después del
período de grant. La licencia AGPL-3.0 impide que sea absorbido por actores comerciales y
mantiene el código público indefinidamente.

---

### Hitos por Trimestre / Quarterly Milestones

| Trimestre | Hito |
|-----------|------|
| Q1 (meses 1-3) | Calibración de umbrales con datos HN-2025 reales; publicación de `FALSE_POSITIVE_ANALYSIS.md` con datos empíricos |
| Q2 (meses 4-6) | Convenio UPNFM firmado; capacitación de primer equipo de observadores; despliegue en municipio piloto 1 |
| Q3 (meses 7-9) | Piloto municipio 2; primer reporte público de resultados; submisión a journal académico |
| Q4 (meses 10-12) | Auditoría de seguridad externa; publicación del playbook de replicación para Guatemala/El Salvador; informe final OTF |

---

## English

### Budget Executive Summary

Centinel Engine requests $95,000 USD to fund 12 months of operation, calibration, and pilot
deployment in two Honduran municipalities. The system already exists and is operational
($0 in construction costs). This budget covers exclusively:
1. Technical staff for maintenance and calibration (primary cost)
2. Field pilot with on-ground observers
3. External academic validation (UPNFM)
4. Minimal infrastructure for continuous operation

The cost per monitored election in production is $0 in licenses and < $50/month in
infrastructure (GitHub Actions + domain). The budget covers the system's maturation period,
not its construction.

### Why This Budget is Efficient

**What this grant does NOT pay for:**
- System development (already exists, AGPL-3.0)
- Software licenses (all dependencies are open-source)
- Proprietary servers (GitHub Pages is free indefinitely)
- Marketing or institutional communications consulting

**Impact ratio:** $95,000 / 2.5M monitored votes = $0.038 per vote in Honduras.
By comparison, proprietary solutions like Scytl or ES&S charge $0.50–$2.00 per vote in
similar monitoring contracts — a difference of 13–53x.

**Post-grant sustainability:** The system operates on $50/month in infrastructure after
the grant period. The AGPL-3.0 license prevents commercial absorption and keeps the
code public indefinitely.

---

*Documento bilingüe ES/EN — Versión 1.0 — 2026-05-18*
*Para metodología técnica: [METHODOLOGY.md](METHODOLOGY.md)*
*Para teoría del cambio: [THEORY_OF_CHANGE.md](THEORY_OF_CHANGE.md)*
*Para auditoría de seguridad: [../SECURITY_AUDIT.md](../SECURITY_AUDIT.md)*
