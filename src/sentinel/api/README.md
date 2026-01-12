# API pública / Public API

## Español

La carpeta `api/` contiene la API pública de C.E.N.T.I.N.E.L. basada en FastAPI.
Expone endpoints de solo lectura para consultar snapshots, alertas y verificar la
cadena de hashes en SQLite.

### Uso rápido

1. Configura el path a la base de datos (opcional):
   - `SNAPSHOTS_DB_PATH=/ruta/a/data/snapshots.db`
2. Inicia el servidor:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Variables de entorno

- `SNAPSHOTS_DB_PATH`: ruta al SQLite de snapshots (default `data/snapshots.db`).
- `CORS_ORIGINS`: lista separada por comas o `*` para permitir CORS.

## English

The `api/` folder contains the public FastAPI application for C.E.N.T.I.N.E.L.
It exposes read-only endpoints for snapshots, alerts, and hashchain verification
backed by the SQLite store.

### Quick start

1. Optionally configure the database path:
   - `SNAPSHOTS_DB_PATH=/path/to/data/snapshots.db`
2. Start the server:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Environment variables

- `SNAPSHOTS_DB_PATH`: path to the snapshots SQLite DB (default `data/snapshots.db`).
- `CORS_ORIGINS`: comma-separated list or `*` to allow CORS.
