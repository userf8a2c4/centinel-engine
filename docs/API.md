# API Pública / Public API

**Version:** 1.1 | **Date:** 2026-05-18 | **Status:** Active

## Español

La API pública de C.E.N.T.I.N.E.L. expone endpoints de solo lectura para
consultar snapshots, alertas y verificar la cadena de hashes.

### Endpoints

#### `GET /snapshots/latest`
Devuelve el snapshot más reciente almacenado.

#### `GET /snapshots/{snapshot_id}`
Devuelve un snapshot por su hash (`snapshot_id`). Responde con `404` si no existe.

#### `GET /hashchain/verify?hash=xxx`
Verifica si el hash existe y si la cadena es consistente. Responde:

```json
{
  "exists": true,
  "valid": true
}
```

#### `GET /alerts`
Devuelve alertas disponibles desde `data/alerts.json` o `alerts.log`.

### Ejecución

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Variables de entorno

- `SNAPSHOTS_DB_PATH`: ruta al SQLite de snapshots (default `data/snapshots.db`).
- `CORS_ORIGINS`: lista separada por comas o `*` para permitir CORS.

### Autenticación

**No se requiere autenticación.** Todos los endpoints son de solo lectura y públicos por diseño: el objetivo es que cualquier ciudadano u organización pueda verificar los datos sin credenciales ni registro. No existen endpoints de escritura en la API pública.

### Respuestas de error

| Código | Condición | Cuerpo de respuesta |
|--------|-----------|---------------------|
| `404 Not Found` | Snapshot no encontrado (`/snapshots/{id}`) | `{"detail": "Snapshot not found"}` |
| `422 Unprocessable Entity` | Parámetro de consulta inválido | `{"detail": [{"loc": [...], "msg": "..."}]}` |
| `429 Too Many Requests` | Límite de peticiones excedido | `{"error": "rate limit exceeded", "retry_after": 60}` |
| `500 Internal Server Error` | Error inesperado del servidor | `{"detail": "Internal server error"}` |

### Límite de peticiones (Rate Limiting)

La API usa [`slowapi`](https://github.com/laurentS/slowapi) con límites por IP:

| Endpoint | Límite |
|----------|--------|
| `GET /snapshots/latest` | 60 peticiones / minuto |
| `GET /snapshots/{id}` | 60 peticiones / minuto |
| `GET /hashchain/verify` | 60 peticiones / minuto |
| `GET /alerts` | 60 peticiones / minuto |

Cuando se supera el límite, la API devuelve `429` con la cabecera `Retry-After: 60`.  
El límite es configurable via la variable de entorno `RATE_LIMIT` (default: `60/minute`).

## English

The C.E.N.T.I.N.E.L. public API exposes read-only endpoints to query snapshots,
alerts, and hashchain verification.

### Endpoints

#### `GET /snapshots/latest`
Returns the most recent snapshot stored.

#### `GET /snapshots/{snapshot_id}`
Returns a snapshot by its hash (`snapshot_id`). Returns `404` if missing.

#### `GET /hashchain/verify?hash=xxx`
Verifies whether the hash exists and the chain is consistent. Response:

```json
{
  "exists": true,
  "valid": true
}
```

#### `GET /alerts`
Returns available alerts from `data/alerts.json` or `alerts.log`.

### Run

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Environment variables

- `SNAPSHOTS_DB_PATH`: path to the snapshots SQLite DB (default `data/snapshots.db`).
- `CORS_ORIGINS`: comma-separated list or `*` for CORS.
- `RATE_LIMIT`: slowapi rate limit string (default `60/minute`).

### Authentication

**No authentication required.** All endpoints are read-only and public by design: the goal is that any citizen or organization can verify the data without credentials or registration. There are no write endpoints in the public API.

### Error Responses

| Code | Condition | Response body |
|------|-----------|---------------|
| `404 Not Found` | Snapshot not found (`/snapshots/{id}`) | `{"detail": "Snapshot not found"}` |
| `422 Unprocessable Entity` | Invalid query parameter | `{"detail": [{"loc": [...], "msg": "..."}]}` |
| `429 Too Many Requests` | Rate limit exceeded | `{"error": "rate limit exceeded", "retry_after": 60}` |
| `500 Internal Server Error` | Unexpected server error | `{"detail": "Internal server error"}` |

### Rate Limiting

The API uses [`slowapi`](https://github.com/laurentS/slowapi) with per-IP limits:

| Endpoint | Limit |
|----------|-------|
| `GET /snapshots/latest` | 60 requests / minute |
| `GET /snapshots/{id}` | 60 requests / minute |
| `GET /hashchain/verify` | 60 requests / minute |
| `GET /alerts` | 60 requests / minute |

When the limit is exceeded, the API returns `429` with a `Retry-After: 60` header.  
Configurable via the `RATE_LIMIT` environment variable (default: `60/minute`).
