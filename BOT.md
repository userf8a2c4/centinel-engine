# Bot Telegram de Sentinel (solo lectura)

## 1) Crear el bot (BotFather)
1. En Telegram busca **@BotFather**.
2. Envía `/newbot` y sigue las instrucciones.
3. Guarda el **token** que te entrega.

## 2) Configurar variables en `.env`
Crea un archivo `.env` en la raíz del repo con:

```env
TELEGRAM_TOKEN=TU_TOKEN_AQUI
TELEGRAM_CHAT_ID=123456789
```

- `TELEGRAM_TOKEN`: el token que te dio BotFather.
- `TELEGRAM_CHAT_ID`: el chat/canal permitido (opcional). Si lo dejas vacío, el bot responde a cualquiera.

> El bot **no guarda datos personales**. Solo usa el `chat_id` en memoria para recordar el modo durante la conversación y lo limpia después.

## 3) Ejecutar el bot

```bash
python bot.py
```

## 4) Disclaimer fijo (en cada mensaje)

```
Solo datos públicos del CNE – Código abierto MIT – Repo: https://github.com/userf8a2c4/sentinel
```

## 5) Comandos principales

### Modo ciudadano (predeterminado)
- `/inicio` — Bienvenida + pregunta de modo + lista de comandos.
- `/ultimo` — Última actualización (hora, % escrutado, votos totales).
- `/cambios [rango]` — Cambios recientes (ej. `últimos 30min`).
- `/alertas` — Últimas alertas detectadas.
- `/grafico [rango]` — Gráfico Benford sencillo del rango.
- `/tendencia [rango]` — Gráfico de cómo cambió el % escrutado o votos.
- `/info [rango]` — Resumen fácil (votos, cambios principales).

### Modo auditor/prensa
- Todo lo anterior +
- `/hash [acta o JRV]` — Hash de integridad del archivo más cercano.
- `/json [rango o depto]` — JSON crudo del archivo más cercano.

## 6) Formatos de rango aceptados
- `últimos 30min`, `últimas 2h`, `últimos 3 días`
- `hoy`, `ayer`
- `desde 14:00 hasta 16:00`

## 7) Ejemplos de mensajes

**Bienvenida (/inicio)**
```
¡Bienvenido! Este bot solo muestra datos públicos ya guardados.
¿Modo ciudadano o auditor? Escribe 'ciudadano' o 'auditor'.

Comandos disponibles:
/inicio
/ultimo
/cambios [rango]
/alertas
/grafico [rango]
/tendencia [rango]
/info [rango]

Solo datos públicos del CNE – Código abierto MIT – Repo: https://github.com/userf8a2c4/sentinel
```

**Modo ciudadano (/ultimo)**
```
¡Última actualización a las 15:42! 78.00% escrutado, 1.200.000 votos totales.

Solo datos públicos del CNE – Código abierto MIT – Repo: https://github.com/userf8a2c4/sentinel
```

**Modo auditor (/hash JRV-12345)**
```
Hash SHA-256 de snapshot_01_2026-01-03_15-42-32.json: abc123... (verificado).

Solo datos públicos del CNE – Código abierto MIT – Repo: https://github.com/userf8a2c4/sentinel
```

## 8) Notas de seguridad
- El bot **no hace scraping**. Solo lee archivos ya existentes en `data/` y `hashes/`.
- Tiene rate limit: **1 comando por minuto por usuario**.
- Respuestas neutrales y 100% factuales.
