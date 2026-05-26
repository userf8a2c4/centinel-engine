# Replication Guide — Centinel Engine
## Guía de Replicación para Otro País Electoral

**Version:** 1.0 | **Date:** 2025-05-17 | **Status:** Active

---

## Español

### ¿Cuándo usar esta guía?

Esta guía es para equipos de observación electoral o desarrolladores que quieran desplegar
Centinel Engine para monitorear un proceso electoral en un país diferente a Honduras (o un
proceso diferente al presidencial hondureño).

---

### Prerequisitos

**Técnicos:**
- Python 3.11+
- Git
- Acceso a internet (para captura de datos del CNE local)
- Supabase account (gratuito) o base de datos PostgreSQL alternativa
- GitHub Pages o servidor web para el panel (opcional)

**Operativos:**
- Identificar los endpoints públicos del organismo electoral local
- Conocer el formato JSON de los datos que publica el organismo
- Al menos 1 persona técnica disponible durante el proceso electoral
- Entidad legal o académica que respalde el deployment

---

### Paso 1: Mapear los endpoints del organismo electoral local

El primer paso es encontrar las URLs de los datos electorales en tiempo real del organismo
equivalente al CNE de Honduras.

Buscar:
- Página de resultados en tiempo real del organismo electoral
- APIs públicas o feeds JSON (revisar las peticiones de red en el browser)
- Documentación técnica del sistema de transmisión de resultados

Registrar las URLs encontradas:
```
Endpoint principal:   https://[organismo]/api/resultados
Endpoints regionales: https://[organismo]/api/departamento/[codigo]
Formato de respuesta: [JSON / XML / otro]
```

---

### Paso 2: Adaptar la configuración

#### 2a. Editar `config/prod/endpoints.yaml`

```yaml
cne:
  main_url: "https://[nuevo-organismo]/api/resultados"
  presidential_endpoints:
    - url: "https://[nuevo-organismo]/api/region/01"
      dept: "[NOMBRE DEPARTAMENTO/REGION 1]"
      level: "departamental"
    - url: "https://[nuevo-organismo]/api/region/02"
      dept: "[NOMBRE DEPARTAMENTO/REGION 2]"
      level: "departamental"
    # ... continuar para todas las regiones
  
healing:
  animal_mode: false
  safe_mode_active: false
  consecutive_failures: 0
```

#### 2b. Adaptar el mapeo de departamentos en el panel

En `web/panel/index.html`, buscar la constante `DEPT_CODE_FROM_NAME` y actualizarla con los
nombres y códigos ISO 3166-2 del nuevo país:

```javascript
const DEPT_CODE_FROM_NAME = {
  'NOMBRE REGION 1': 'XX-01',
  'NOMBRE REGION 2': 'XX-02',
  // ... adaptar según el país
};
```

#### 2c. Adaptar el mapa SVG

El mapa en `web/panel/index.html` es específico de Honduras. Para otro país:
1. Obtener el SVG del mapa del nuevo país (Natural Earth, Wikipedia Commons, etc.)
2. Asegurarse que cada departamento/región tenga `id` o `data-id` con el código ISO
3. Reemplazar el bloque `<svg>` en el panel

---

### Paso 3: Adaptar el parser de datos

El componente central que lee los datos del CNE es `src/centinel/sync/`.

Si el nuevo organismo electoral publica datos en formato diferente:

1. Crear un nuevo adapter en `src/centinel/sync/adapters/[pais]_adapter.py`:

```python
def normalize_snapshot(raw_data: dict) -> dict:
    """
    Convierte el formato JSON del organismo electoral local
    al formato estándar de Centinel Engine.
    
    Formato estándar esperado:
    {
        "departamento": str,
        "porcentaje_escrutado": float,
        "electores_registrados": int,
        "actas": {"totales": int, "procesadas": int},
        "mesas": {"totales": int, "procesadas": int},
        "votos_totales": {"total": int, "validos": int, "nulos": int, "blancos": int},
        "votos": [{"candidato": str, "partido": str, "votes": int}],
    }
    """
    # Implementar transformación aquí
    return normalized
```

2. Registrar el adapter en `config/prod/config.yaml`:
```yaml
data_adapter: "centinel.sync.adapters.guatemala_adapter"
```

---

### Paso 4: Configurar sincronización a GitHub Pages (opcional)

Para publicar snapshots y alertas en tiempo real a la web pública:

1. En GitHub → **Settings → Secrets → Actions**, crear:
   - `GITHUB_TOKEN` (ya disponible automáticamente en Actions)
   - O un PAT con permiso `contents:write` si se ejecuta fuera de Actions
2. Las variables de entorno relevantes:
   ```bash
   GITHUB_REPOSITORY=VectisDev/centinel   # automático en Actions
   GITHUB_PAGES_BRANCH=main               # rama donde vive web/data/
   ```

> Sin estas variables, el motor sigue funcionando localmente. SQLite es siempre la fuente de verdad.

---

### Paso 5: Variables de entorno mínimas

```bash
# Opcionales — sync a GitHub Pages
GITHUB_TOKEN=...                  # PAT o token de Actions
GITHUB_PAGES_BRANCH=main         # rama de publicación (default: main)

# Opcionales con defaults
CENTINEL_POLL_INTERVAL=120        # segundos entre capturas (default: 120)
CENTINEL_ENDPOINT_TIMEOUT=10.0    # timeout HTTP en segundos (default: 10)
OTS_ENABLED=true                  # habilitar OpenTimestamps Bitcoin anchor
LOG_LEVEL=INFO
```

---

### Paso 6: Verificar que el sistema captura datos

```bash
# Instalar dependencias
pip install -e ".[dev]"

# Correr una captura de prueba (dry-run)
python scripts/run_pipeline.py --dry-run --once

# Verificar que el formato del snapshot sea correcto
python scripts/validate_snapshot.py --snapshot output/latest_snapshot.json
```

---

### Paso 7: Adaptar el panel público

En `web/panel/index.html`:

1. Cambiar el título y descripción en el `<head>` y `<header>`
2. Actualizar `web/config.js` con la URL de GitHub Pages del nuevo repositorio:
   ```javascript
   const CENTINEL_PAGES_URL = 'https://[tu-org].github.io/[tu-repo]';
   ```
3. Regenerar seeds de acceso con `make wizard` (genera nuevos hashes en `web/access.json`)

---

### Checklist de adaptación

Antes del proceso electoral:

- [ ] Endpoints del organismo electoral local identificados y documentados
- [ ] `config/prod/endpoints.yaml` actualizado con las URLs correctas
- [ ] Parser/adapter verificado contra datos de prueba del organismo
- [ ] Variables de entorno configuradas en el servidor de producción
- [ ] Supabase configurado con las tablas correctas
- [ ] Panel público deployado y accesible
- [ ] Verificador offline probado localmente
- [ ] `DEPT_CODE_FROM_NAME` en panel actualizado
- [ ] Mapa SVG del nuevo país integrado
- [ ] Prueba de captura dry-run exitosa
- [ ] Primer snapshot real capturado y verificado
- [ ] Cadena de hashes iniciada y ancla Bitcoin creada

Durante el proceso electoral:

- [ ] Operador de turno disponible 24/7
- [ ] INCIDENT_RESPONSE.md impreso y accesible
- [ ] Canal de comunicación seguro con coordinador técnico activo
- [ ] Storage externo para backup de evidencia funcionando
- [ ] Misión de observación presente notificada de la existencia del sistema

---

### Diferencias esperadas por país

| Aspecto | Honduras (referencia) | Adaptación típica |
|---------|----------------------|-------------------|
| Formato JSON | CNE Honduras | Requiere adapter |
| Departamentos | 18 | Varía por país |
| Mapa SVG | Honduras HN | Reemplazar SVG |
| Endpoints | 19+ URLs CNE | Mapear URLs locales |
| Idioma del panel | ES | ES (o añadir EN) |
| Base legal | LEOP Honduras | Ley electoral local |

---

### Países con procesos electorales próximos (referencia)

Para planificación de replicación, considerar el calendario de elecciones en:
- Guatemala
- El Salvador
- República Dominicana
- Costa Rica
- Panamá

Revisar calendario electoral actualizado en: https://www.ifes.org/elections

---

## English

### When to use this guide

This guide is for electoral observation teams or developers who want to deploy Centinel
Engine to monitor an electoral process in a country different from Honduras (or a different
process than the Honduran presidential election).

### Minimum environment variables

```bash
# Optional — sync to GitHub Pages
GITHUB_TOKEN=...                  # PAT or Actions token
GITHUB_PAGES_BRANCH=main         # publication branch (default: main)

# Optional with defaults
CENTINEL_POLL_INTERVAL=120        # seconds between captures
CENTINEL_ENDPOINT_TIMEOUT=10.0    # HTTP timeout in seconds
OTS_ENABLED=true                  # enable Bitcoin OpenTimestamps anchor
LOG_LEVEL=INFO
```

### Adaptation checklist

- [ ] Local electoral authority endpoints identified and documented
- [ ] `config/prod/endpoints.yaml` updated with correct URLs
- [ ] Parser/adapter verified against sample data from the authority
- [ ] Environment variables configured on production server
- [ ] Supabase configured with correct tables
- [ ] Public panel deployed and accessible
- [ ] Offline verifier tested locally
- [ ] `DEPT_CODE_FROM_NAME` in panel updated for new country
- [ ] Country SVG map integrated
- [ ] Dry-run capture test successful
- [ ] First real snapshot captured and verified
- [ ] Hash chain initiated and Bitcoin anchor created

---

*Last revision: 2025-05-17*
*See also: [METHODOLOGY.md](METHODOLOGY.md) | [THEORY_OF_CHANGE.md](THEORY_OF_CHANGE.md) | [OPERATOR-RUNBOOKS.md](OPERATOR-RUNBOOKS.md)*
