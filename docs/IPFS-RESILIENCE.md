# IPFS Resilience / Resiliencia IPFS

**Version:** 1.0 | **Date:** 2026-05-19 | **Status:** Active | **Audience:** Operadores · Auditores · Desarrolladores

> Cómo IPFS añade una capa de resiliencia que GitHub no puede garantizar.  
> How IPFS adds a resilience layer that GitHub cannot guarantee.

---

## Qué garantiza IPFS que GitHub no puede / What IPFS guarantees that GitHub cannot

GitHub es una plataforma centralizada. Puede censurar repositorios, eliminar contenido bajo presión gubernamental o simplemente dejar de funcionar. IPFS (InterPlanetary File System) garantiza propiedades que GitHub no puede:

| Propiedad | GitHub | IPFS |
|-----------|--------|------|
| **Inmutabilidad por contenido** | No — URL puede cambiar | Sí — CID es hash del contenido |
| **Resistencia a censura** | No — sujeto a DMCA/legal | Sí — contenido distribuido en la red |
| **Supervivencia si el repo es eliminado** | No | Sí — mientras haya nodos que lo anclen |
| **Verificación sin confiar en servidor** | No | Sí — CID verifica integridad por diseño |
| **Acceso sin cuenta** | Parcial | Sí — gateways públicos o nodo propio |

Para datos de auditoría electoral, esta diferencia es crítica: una autoridad puede presionar a GitHub para eliminar un repositorio. No puede presionar a la red IPFS.

---

## Cómo funciona el auto-pin / How auto-pin works

El workflow `ipfs-pin.yml` en centinel-data se ejecuta automáticamente en cada push a `main`:

```
Cada push a centinel-data/main
  │
  ├─ PINATA_JWT configurado?
  │    SÍ → pin completo del repo a Pinata
  │         → registrar CID en ipfs-manifest.json
  │         → commit ipfs-manifest.json
  │
  └─ NO → workflow se salta silenciosamente (sin error)
```

El pin es silencioso en ambos casos: no genera Issues, no envía notificaciones, no falla el workflow principal.

---

## Estructura de ipfs-manifest.json

```json
{
  "schema_version": "1.0",
  "last_updated": "2026-05-19T14:30:00+00:00",
  "snapshots": [
    {
      "cid": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
      "timestamp": "2026-05-19T14:30:00+00:00"
    },
    {
      "cid": "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
      "timestamp": "2026-05-18T03:00:00+00:00"
    }
  ]
}
```

Cada entrada es un pin completo del estado del repositorio centinel-data en ese momento. El CID es determinístico: el mismo contenido siempre produce el mismo CID.

Para usar el manifiesto:
```bash
# Listar todos los CIDs
cat centinel-data/ipfs-manifest.json | python3 -c "
import json, sys
m = json.load(sys.stdin)
for s in m['snapshots']:
    print(s['timestamp'], s['cid'])
"
```

---

## Recuperación si GitHub cae / Recovery if GitHub goes down

Si centinel-data deja de estar disponible en GitHub, los datos siguen accesibles vía IPFS:

```bash
# Opción 1: IPFS CLI (nodo propio o local)
ipfs get QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco

# Opción 2: Gateway público de IPFS Foundation
curl -O https://ipfs.io/ipfs/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco

# Opción 3: Gateway Cloudflare
curl -O https://cloudflare-ipfs.com/ipfs/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco

# Opción 4: Gateway dweb.link
curl -O https://dweb.link/ipfs/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco
```

El CID se obtiene del último `ipfs-manifest.json` disponible. Si el manifiesto también no está disponible, el operador puede haberlo guardado localmente o publicado como parte de un informe de auditoría.

---

## Setup Pinata (opcional) / Pinata setup (optional)

Pinata es el servicio de pinning recomendado por ser gratuito para uso básico y no requerir infraestructura propia. El setup toma aproximadamente 3 minutos:

**Paso 1 — Crear cuenta gratuita**

[→ pinata.cloud](https://pinata.cloud) → Sign Up → cuenta gratuita (1 GB incluido)

**Paso 2 — Crear API Key con JWT**

En Pinata: API Keys → New Key → seleccionar "Admin" o al menos permisos de pinning → Generate → **copiar el JWT** (solo se muestra una vez)

**Paso 3 — Guardar en centinel-data**

En GitHub: `centinel-data` → Settings → Secrets and variables → Actions → New repository secret:
- **Name:** `PINATA_JWT`
- **Secret:** pegar el JWT copiado

A partir del próximo push a centinel-data, el workflow `ipfs-pin.yml` comenzará a anclar automáticamente.

---

## Notas técnicas / Technical notes

- El pin incluye todo el contenido de centinel-data en ese momento (tar.gz del repo sin `.git`)
- El tamaño típico de un pin es proporcional al número de snapshots acumulados
- La cuenta gratuita de Pinata incluye 1 GB de almacenamiento; para elecciones largas considerar plan de pago o un nodo propio
- Los CIDs son inmutables: un pin nunca puede ser modificado retroactivamente, solo añadido

---

## Referencias / References

- [DATA-REPOS.md](DATA-REPOS.md) — Arquitectura de separación código/datos
- [RESILIENCE.md](RESILIENCE.md) — Mecanismos de resiliencia operativa del motor
- [SETUP-GUIDE.md](SETUP-GUIDE.md) — Guía de configuración del sistema
