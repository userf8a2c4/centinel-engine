# DEPLOY

## Español

### Rate limiting

El servicio API aplica límites en memoria por IP usando una ventana de 60 segundos:

- **Global:** 100 requests por minuto.
- **Verificación de hashchain:** 10 requests por minuto.

Para ajustar límites, edita los valores en `src/sentinel/api/main.py`:

- `global_rate_limiter` → `RateLimitConfig(limit=100, window_seconds=60)`
- `compare_rate_limiter` → `RateLimitConfig(limit=10, window_seconds=60)`

### Healthchecks.io

1. Crea una cuenta gratuita en https://healthchecks.io/.
2. Crea un check nuevo y copia el UUID.
3. Exporta la variable de entorno:
   ```bash
   export HEALTHCHECKS_UUID="tu-uuid"
   ```

El servicio enviará un ping de éxito cada 5 minutos. Si el scraping falla más de
3 veces seguidas o ocurre un error crítico, se enviará un ping de fallo.

---

## English

### Rate limiting

The API service applies in-memory IP-based limits using a 60-second window:

- **Global:** 100 requests per minute.
- **Hashchain verification:** 10 requests per minute.

To adjust limits, edit the values in `src/sentinel/api/main.py`:

- `global_rate_limiter` → `RateLimitConfig(limit=100, window_seconds=60)`
- `compare_rate_limiter` → `RateLimitConfig(limit=10, window_seconds=60)`

### Healthchecks.io

1. Create a free account at https://healthchecks.io/.
2. Create a new check and copy the UUID.
3. Export the environment variable:
   ```bash
   export HEALTHCHECKS_UUID="your-uuid"
   ```

The service will send a success ping every 5 minutes. If scraping fails more than
3 times in a row or a critical error occurs, a failure ping will be sent.
