# Centinel Engine — Academic Research Access

**For: Devis Alvarado, UPNFM Mathematics Department, and collaborating researchers**

---

## ESPAÑOL

### Bienvenida

Centinel Engine es un **sistema de monitoreo electoral verificable criptográficamente**, 
diseñado para funcionar bajo presión en ambientes hostiles. Está construido sobre principios
matemáticos rigurosos, con integridad garantizada por SHA-256 y cadenas hash verificables.

Ustedes (Devis, colegas matemáticos, estudiantes) tienen acceso **privilegiado pero
de solo lectura** a toda la superficie de auditoría pública, lo que les permite:

- Reproducir verificaciones de integridad del 100% del chain
- Inspeccionar timestamps forenses y secuencias de fallback
- Publicar papers sobre la solidez matemática del sistema
- Ejecutar tesis sobre criptografía, redundancia bizantina, o estabilidad electoral

### Acceso a la API de Investigación

Todos los endpoints son **públicos, sin autenticación**. El sistema está diseñado
para que observadores independientes (ustedes, Carter Center, UE, auditores ciudadanos)
puedan verificar en tiempo real sin necesidad de credenciales.

#### `/audit/health` → Disponibilidad del subsistema

```bash
curl https://centinel.upnfm.edu.hn/audit/health
```

Retorna:
```json
{
  "status": "ok",
  "subsystem": "audit",
  "server_time_utc": "2026-05-15T14:23:45.123456",
  "snapshot_root": "/data/snapshots",
  "snapshot_root_exists": true,
  "endpoints": [
    "/audit/health",
    "/audit/chain/verify",
    "/audit/timeline",
    "/audit/snapshots/{date}",
    "/audit/proof/{hash}"
  ],
  "no_auth_required": true,
  "data_license": "Public — CNE transparency law (Decreto 170-2006 Honduras)"
}
```

**Uso académico:** Confirma que la infraestructura es alcanzable y expone la
versión del protocolo público que implementa.

---

#### `/audit/chain/verify` → Verificación completa de la cadena

```bash
curl https://centinel.upnfm.edu.hn/audit/chain/verify
```

Retorna:
```json
{
  "valid": true,
  "count": 14523,
  "verified_count": 14523,
  "last_valid_hash": "a3f92c8d...",
  "broken_at": null,
  "broken_at_path": null,
  "errors": [],
  "snapshot_root": "/data/snapshots",
  "verified_at_utc": "2026-05-15T14:24:01.234567",
  "note": "All snapshots verified; chain integrity confirmed."
}
```

**Si la cadena está rota:**
```json
{
  "valid": false,
  "count": 14523,
  "verified_count": 1456,
  "last_valid_hash": "f7e2a1b9...",
  "broken_at": 1457,
  "broken_at_path": "data/snapshots/2026-05-14T09:45:23Z",
  "errors": [
    "Snapshot index 1457: expected_hash mismatch. Computed: deadbeef..., stored: cafebabe..."
  ]
}
```

**Uso académico:** Ejecutar localmente para reproducir la verificación criptográfica.
Comparar `last_valid_hash` entre múltiples instancias (Honduras, Guatemala, UE) para
detectar divergencia o manipulación.

---

#### `/audit/timeline?limit=100&offset=0` → Índice cronológico

```bash
curl 'https://centinel.upnfm.edu.hn/audit/timeline?limit=5&offset=0'
```

Retorna:
```json
{
  "total": 14523,
  "offset": 0,
  "limit": 5,
  "entries": [
    {
      "path": "data/snapshots/2026-05-01T00:00:00Z",
      "expected_hash": "a3f92c8d...",
      "previous_hash": null,
      "timestamp_utc": "2026-05-01T00:00:00.000001",
      "source_url": "https://resultados2029.cne.hn/...",
      "software_version": "centinel-v2.14.0"
    },
    {
      "path": "data/snapshots/2026-05-01T00:15:30Z",
      "expected_hash": "b4f02d9e...",
      "previous_hash": "a3f92c8d...",
      "timestamp_utc": "2026-05-01T00:15:30.000123",
      "source_url": "https://resultados2029.cne.hn/...",
      "software_version": "centinel-v2.14.0"
    }
    // ... 3 more entries
  ]
}
```

**Uso académico:** Explorar el dataset histórico completo. Analizar frecuencia de snapshots,
cambios en URLs de fuente, versiones de software. Detectar anomalías o patrones sospechosos.

---

#### `/audit/snapshots/{date}` → Filtrar por fecha electoral (UTC)

```bash
curl 'https://centinel.upnfm.edu.hn/audit/snapshots/2026-11-29'
```

Retorna:
```json
{
  "date_utc": "2026-11-29",
  "count": 96,
  "entries": [
    {
      "path": "data/snapshots/2026-11-29T00:00:30Z",
      "expected_hash": "deadbeef...",
      "previous_hash": "cafebabe...",
      "timestamp_utc": "2026-11-29T00:00:30.123456",
      "source_url": "https://resultados2029.cne.hn/...",
      "software_version": "centinel-v2.14.0"
    }
    // ... 95 more
  ]
}
```

**Uso académico:** Extraer datos electorales para un día específico. Reconstruir
cronología de eventos alrededor de un anomalía reportada.

---

#### `/audit/proof/{hash}` → Prueba de inclusión y verificación

```bash
curl 'https://centinel.upnfm.edu.hn/audit/proof/deadbeef...'
```

Retorna:
```json
{
  "snapshot_hash": "deadbeef...",
  "position": 1457,
  "chain_length": 14523,
  "snapshot": {
    "path": "data/snapshots/2026-11-29T09:45:23Z",
    "expected_hash": "deadbeef...",
    "previous_hash": "cafebabe...",
    "timestamp_utc": "2026-11-29T09:45:23.654321",
    "source_url": "https://resultados2029.cne.hn/...",
    "software_version": "centinel-v2.14.0"
  },
  "predecessor": {
    "path": "data/snapshots/2026-11-29T09:30:15Z",
    "expected_hash": "cafebabe...",
    "previous_hash": "beefcafe...",
    "timestamp_utc": "2026-11-29T09:30:15.123456",
    "source_url": "https://resultados2029.cne.hn/...",
    "software_version": "centinel-v2.14.0"
  },
  "metadata": {
    "fallback_recovered_at": null,
    "fallback_sequence": null,
    "original_timestamp": "2026-11-29T09:45:23.654321"
  },
  "verified_at_utc": "2026-11-29T09:45:40.000000",
  "verification_instructions": "Reproduce locally: compute_snapshot_hash(content, metadata, predecessor.expected_hash) must equal snapshot_hash."
}
```

**Uso académico:** Para cualquier snapshot de interés, obtener su posición en la cadena,
su contenido, su predecesor, y la receta de verificación. Reproducir localmente para
confirmar integridad (ver sección Reproducibilidad más abajo).

---

### Oportunidades de Investigación y Tesis

#### 1. **Matemáticas: Resistencia a Colisiones del Merkle Root**

**Pregunta:** ¿Cuántos snapshots pueden capturarse antes de que la probabilidad de
colisión SHA-256 se vuelva material (ej. 10^-60)?

**Enfoque:**
- Analizar la frecuencia de snapshots (ej. cada 15 minutos = 96/día = 35K/año)
- Calcular probabilidad de colisión usando birthday paradox (2^128 para SHA-256)
- Documentar los límites teóricos del sistema bajo captura sostenida

**Resultado académico:** Paper en revista de criptografía (ej. Journal of Cryptologic Research)

---

#### 2. **Informática: Tolerancia a Fallos Bizantinos bajo Red Retrasada**

**Pregunta:** Si un atacante controla la red y puede retrasarla 30-60s, ¿puede
manipular la secuencia de snapshots de forma que la cadena aún verifique localmente?

**Enfoque:**
- Estudiar el módulo `fallback_sequence` en scripts/download_and_hash.py
- Analizar microsecond timestamps + monotonic counter como defensa
- Probar escenarios de reordenamiento de red

**Resultado académico:** Tesis de maestría en Seguridad de Sistemas Distribuidos

---

#### 3. **Ciencia Política: Criptografía como Escudo Político**

**Pregunta:** ¿Cómo cambia el debate público cuando los resultados electorales
están respaldados por pruebas criptográficas que un sistema experto (UPNFM) ha validado?

**Enfoque:**
- Analizar cómo la validación matemática afecta la credibilidad política
- Documentar cómo "las matemáticas están equivocadas" es un argumento más frágil
  que "los números están mal" (cuando no hay prueba técnica)
- Estudiar precedentes en países donde la auditoría técnica sostuvo la democracia

**Resultado académico:** Paper en *Journal of Democracy* o *Political Methodology*

---

#### 4. **Estadística: Detección de Anomalías Electorales**

**Pregunta:** Usando series temporales de snapshots, ¿podemos detectar patrones
anormales en los cambios de votación entre capturas sucesivas?

**Enfoque:**
- Descargar la línea de tiempo completa (`/audit/timeline`)
- Analizar deltas de timestamp: ¿son uniformes? ¿hay ráfagas?
- Modelar distribuciones de cambios de votos por zona
- Aplicar CUSUM o métodos de detección de puntos de cambio

**Resultado académico:** Tesis en Estadística Electoral o Métodos Cuantitativos

---

### Instrucciones de Acceso

#### Ambiente de Demostración

Para pruebas locales, ejecuta:

```bash
cd centinel-engine
docker compose -f docker-compose.demo.yml up -d --build
./scripts/verify_deployment.sh
open http://localhost:8000/docs
```

Luego accede a:
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/audit/health
- Chain: http://localhost:8000/audit/chain/verify

#### Ambiente de Producción

El sistema está desplegado en:

```
https://centinel.upnfm.edu.hn/
```

(Hipotético; ajusta a tu URL de producción real)

Todos los endpoints son públicos. No se requieren credenciales.

#### Retención de Datos

- **Snapshots:** Retenidos indefinidamente para auditoría histórica
- **Logs:** Rotados por tamaño (máx. 10 MB), retenidos 30 días
- **Chain state:** Persistido en disco; reconstruible desde snapshots

#### Reproducibilidad

Para reproducir una verificación:

```bash
# 1. Obtener un hash de la línea de tiempo
HASH=$(curl -s 'https://centinel.upnfm.edu.hn/audit/timeline?limit=1' | \
  python3 -c 'import json,sys; print(json.load(sys.stdin)["entries"][0]["expected_hash"])')

# 2. Obtener la prueba de inclusión
curl -s "https://centinel.upnfm.edu.hn/audit/proof/$HASH" > proof.json

# 3. En tu máquina, reproducir el hash localmente
python3 -c '
from src.centinel.hasher import compute_snapshot_hash
import json

proof = json.load(open("proof.json"))
snapshot = proof["snapshot"]
pred = proof["predecessor"]

# Pseudo-código; adapta a tus datos
content = fetch_snapshot_content(snapshot["path"])
metadata = extract_metadata(snapshot)
predecessor_hash = pred["expected_hash"] if pred else None

computed = compute_snapshot_hash(content, metadata, predecessor_hash)
expected = snapshot["expected_hash"]

assert computed == expected, f"Mismatch: {computed} != {expected}"
print("✓ Verification successful")
'
```

---

### Plantilla de Citación Académica

Para papers y tesis, cita como:

```
Centinel Election Monitoring System. Accessed [DATE].
Hash chain verified at [HASH]. Snapshot timestamp [UTC].
Reproduction: GET /audit/proof/{HASH}
URL: https://centinel.upnfm.edu.hn
```

Ejemplo en BibTeX:

```bibtex
@online{centinel2026,
  author = {Centinel Contributors},
  title = {Centinel Engine: Cryptographically Verifiable Election Monitoring},
  url = {https://github.com/userf8a2c4/centinel-engine},
  year = {2026},
  note = {Accessed 2026-05-15}
}
```

---

### Contacto y Soporte

Para preguntas técnicas:

- **GitHub Issues:** https://github.com/userf8a2c4/centinel-engine/issues
- **Email:** [maintainer email]
- **UPNFM Partnership:** [coordinator contact]

---

## ENGLISH

### Welcome

Centinel Engine is a **cryptographically verifiable election monitoring system**
designed to function under pressure in hostile environments. It is built on rigorous
mathematical principles, with integrity guaranteed by SHA-256 and verifiable hash chains.

You (Devis, mathematics colleagues, students) have **privileged read-only access**
to the entire public audit surface, allowing you to:

- Reproduce 100% of chain integrity verifications
- Inspect forensic timestamps and fallback sequences
- Publish papers on the mathematical soundness of the system
- Execute theses on cryptography, Byzantine redundancy, or electoral stability

### Research API Access

All endpoints are **public, unauthenticated**. The system is designed so that
independent observers (you, Carter Center, EU, citizen auditors) can verify in
real time without credentials.

[The API endpoints described above in ESPAÑOL apply identically in English.]

### Research and Thesis Opportunities

See the four opportunities listed above (Merkle collision resistance, Byzantine
fault tolerance, political cryptography, anomaly detection). They apply to English-
speaking researchers as well.

### Access Instructions

#### Demo Environment

```bash
cd centinel-engine
docker compose -f docker-compose.demo.yml up -d --build
./scripts/verify_deployment.sh
open http://localhost:8000/docs
```

#### Production

```
https://centinel.upnfm.edu.hn/
```

All endpoints are public. No credentials required.

#### Data Retention

- **Snapshots:** Indefinite retention for historical audit
- **Logs:** Rotated by size (max 10 MB), 30-day retention
- **Chain state:** Persisted to disk; reconstructible from snapshots

#### Reproducibility

See the reproducibility instructions in the ESPAÑOL section (they are language-agnostic).

### Citation Template

For academic work:

```
Centinel Election Monitoring System. Accessed [DATE].
Hash chain verified at [HASH]. Snapshot timestamp [UTC].
Reproduction: GET /audit/proof/{HASH}
URL: https://centinel.upnfm.edu.hn
```

---

### Support

For technical questions:

- **GitHub Issues:** https://github.com/userf8a2c4/centinel-engine/issues
- **Email:** [maintainer email]
- **UPNFM Partnership:** [coordinator contact]

---

## Appendix: System Architecture for Reference

### Core Components

- **Hasher Module** (`src/centinel/hasher.py`)
  - `compute_snapshot_hash()`: Chainable SHA-256 with previous_hash linkage
  - `verify_hashchain_from_snapshots()`: Full-chain verification with break-point reporting

- **Download Module** (`src/centinel/download.py`)
  - `write_atomic()`: Ensures no partial writes on crash

- **Circuit Breaker** (`scripts/circuit_breaker.py`)
  - State persistence to prevent restart-based DoS loops
  - Exponential backoff thresholds

- **Audit Router** (`src/centinel/api/audit.py`)
  - Public endpoints for chain verification, timeline browsing, proof retrieval

### Threat Model

The system is hardened against:

- **Data Tampering:** Hash chain detects any modification
- **Network MITM:** DNS pinning + TLS certificate pinning + public IP validation
- **Sustained DoS:** Circuit breaker + adaptive rate limiting
- **Restart Exploitation:** Persisted breaker state prevents reset loops
- **Config Tampering:** Pydantic schema validation at boot

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-15  
**System Version:** centinel-v2.14.0+  
**Audience:** UPNFM Researchers, Academic Partners, Independent Auditors
