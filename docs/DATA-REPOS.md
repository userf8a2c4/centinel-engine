# Repositorio de Datos — centinel-data

**Version:** 1.0 | **Date:** 2026-05-19 | **Status:** Active | **Audience:** NDI · Carter Center · Auditores · Desarrolladores

> Por qué el código y los datos viven en repositorios separados, y cómo verificar los datos desde cero.  
> Why code and data live in separate repositories, and how to verify data from scratch.

---

## Por qué la separación / Why the separation

Centinel-engine no almacena datos electorales en el mismo repositorio que el código. Esto es una decisión de diseño deliberada por tres razones:

**1. Auditoría limpia / Clean audit trail**  
El historial de commits de centinel-engine contiene solo cambios de código. El historial de centinel-data contiene solo actualizaciones de datos. Un auditor puede revisar cada uno sin ruido del otro.

**2. Trazabilidad de datos / Data traceability**  
Cada snapshot publicado en centinel-data tiene su propio commit con timestamp, hash SHA-256 y origen. Es posible reconstruir el estado de los datos en cualquier punto del tiempo sin mezclar con despliegues de código.

**3. Resiliencia y replicación / Resilience and replication**  
centinel-data es un repositorio público independiente. Cualquier organización puede hacer fork o clonar solo los datos, sin necesidad de ejecutar el motor. Los datos sobreviven aunque centinel-engine sea eliminado.

---

## Diagrama / Diagram

```
  ┌─────────────────────────────────────────┐
  │           centinel-engine               │
  │  (código, workflows, análisis)          │
  └──────────────────┬──────────────────────┘
                     │
                     │  push automático (cada captura)
                     │  DATA_REPO_TOKEN
                     ▼
  ┌─────────────────────────────────────────┐
  │            centinel-data                │
  │  snapshots/ · hashes/ · diffs/          │
  │  reports/   · observer-packs/           │
  │  ipfs-manifest.json                     │
  └──────────────────┬──────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
  GitHub Releases          IPFS (opcional)
  (backup semanal)    (pin via Pinata si PINATA_JWT)
          │                     │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │     Auditores       │
          │  NDI · Carter Center│
          │  Ciudadanos         │
          └─────────────────────┘
```

---

## Flujo de un snapshot / Snapshot lifecycle

```
1. GENERACIÓN
   centinel-engine captura datos del endpoint CNE
   → sha256(datos) → hash chain
   → diffs vs snapshot anterior

2. PUBLICACIÓN LOCAL
   Commit en centinel-engine:
     data/, hashes/, diffs/, reports/

3. PUSH A centinel-data
   Workflow "Push data to centinel-data":
     snapshots/  ← data/
     hashes/     ← hashes/
     diffs/      ← diffs/
     reports/    ← reports/

4. GITHUB RELEASES (semanal)
   Workflow auto-release.yml en centinel-data:
     → backup-YYYY-MM-DD.zip + SHA256

5. IPFS (opcional, si PINATA_JWT configurado)
   Workflow ipfs-pin.yml en centinel-data:
     → pin a Pinata → CID registrado en ipfs-manifest.json
```

---

## Verificar desde cero / Verify from scratch

Cualquier auditor puede verificar la integridad de los datos sin confiar en Centinel:

```bash
# Clonar solo los datos
git clone https://github.com/USER/centinel-data

# Verificar hash del snapshot más reciente
sha256sum centinel-data/snapshots/latest/snapshot.json

# Comparar con el hash registrado en hashes/
cat centinel-data/hashes/latest.json

# Reconstruir la cadena de hashes
python3 -c "
import json, hashlib, pathlib
hashes = sorted(pathlib.Path('centinel-data/hashes').glob('*.json'))
for h in hashes:
    data = json.loads(h.read_text())
    print(data.get('timestamp'), data.get('sha256'))
"
```

---

## Fallback sin DATA_REPO_TOKEN / Fallback without DATA_REPO_TOKEN

Si el secret `DATA_REPO_TOKEN` no está configurado, el sistema opera en modo local sin error:

```
DATA_REPO_TOKEN ausente → datos se quedan en centinel-engine
                        → ningún workflow falla
                        → ningún mensaje de error al usuario
                        → centinel-data no se crea
```

Este es el comportamiento por defecto al hacer fork. Los datos se acumulan localmente en `data/`, `hashes/`, `diffs/`, `reports/` dentro de centinel-engine. Todo el análisis y la auditoría funcionan igual.

Para activar la publicación a centinel-data, ver [SETUP-GUIDE.md](SETUP-GUIDE.md).

---

## Estructura de centinel-data / centinel-data structure

```
centinel-data/
├── snapshots/
│   ├── latest/
│   │   └── snapshot.json      # Snapshot más reciente
│   ├── emergency/             # Snapshots de emergencia (anomalías ALTA/CRÍTICA)
│   └── YYYY-MM-DD/            # Snapshots por fecha
├── hashes/                    # Hash chain — SHA-256 de cada snapshot
├── diffs/                     # Diferencias entre snapshots consecutivos
├── reports/                   # PDFs de informes bilingües
├── observer-packs/            # ZIPs para organizaciones observadoras
└── ipfs-manifest.json         # CIDs de cada pin IPFS (si aplica)
```

---

## Referencias / References

- [SETUP-GUIDE.md](SETUP-GUIDE.md) — Cómo activar centinel-data
- [IPFS-RESILIENCE.md](IPFS-RESILIENCE.md) — Capa IPFS para resiliencia adicional
- [ARCHITECTURE.md](ARCHITECTURE.md) — Arquitectura técnica completa
