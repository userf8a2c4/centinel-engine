# DEPLOY

## Rate limiting

El servicio API aplica límites en memoria por IP usando una ventana de 60 segundos:

- **Global:** 100 requests por minuto.
- **Verificación de hashchain:** 10 requests por minuto.

Para ajustar límites, edita los valores en `src/sentinel/api/main.py`:

- `global_rate_limiter` → `RateLimitConfig(limit=100, window_seconds=60)`
- `compare_rate_limiter` → `RateLimitConfig(limit=10, window_seconds=60)`

## Healthchecks.io

1. Crea una cuenta gratuita en https://healthchecks.io/.
2. Crea un check nuevo y copia el UUID.
3. Exporta la variable de entorno:
   ```bash
   export HEALTHCHECKS_UUID="tu-uuid"
   ```

El servicio enviará un ping de éxito cada 5 minutos. Si el scraping falla más de
3 veces seguidas o ocurre un error crítico, se enviará un ping de fallo.
