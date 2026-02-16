"""Zero Trust middleware for the C.E.N.T.I.N.E.L. public API.
(Middleware Zero Trust para la API pública de C.E.N.T.I.N.E.L.)

Enforces: per-IP rate limiting (slowapi), IP blocklist, request size caps,
and suspicious-header rejection.  Every request is untrusted by default —
even from internal networks.  All checks are opt-in via config.yaml →
security.zero_trust: true.

(Aplica: rate limiting por IP (slowapi), blocklist de IPs, límite de tamaño
de request, y rechazo de headers sospechosos.  Cada request es no-confiable
por defecto — incluso desde redes internas.  Todos los chequeos son opt-in
vía config.yaml → security.zero_trust: true.)
"""

from __future__ import annotations

import ipaddress
import logging
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, DefaultDict

import yaml
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("centinel.middleware")

# ---------------------------------------------------------------------------
# Config helpers (Helpers de configuración)
# ---------------------------------------------------------------------------

# Path to the main config file (Ruta al archivo de configuración principal)
_CONFIG_PATH = Path(__file__).resolve().parents[3] / "command_center" / "config.yaml"


def _load_security_config() -> dict[str, Any]:
    """Load the 'security' section from command_center/config.yaml.
    (Carga la sección 'security' de command_center/config.yaml.)

    Returns an empty dict when the file is missing or malformed so
    the middleware degrades to permissive mode (no blocking).
    (Retorna dict vacío si el archivo falta o es inválido para que
    el middleware degrade a modo permisivo — sin bloqueo.)
    """
    if not _CONFIG_PATH.exists():
        return {}
    try:
        raw = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("middleware_config_load_failed error=%s", exc)
        return {}
    if not isinstance(raw, dict):
        return {}
    sec = raw.get("security", {})
    return sec if isinstance(sec, dict) else {}


# ---------------------------------------------------------------------------
# In-memory sliding-window rate limiter (Rate limiter deslizante en memoria)
# ---------------------------------------------------------------------------
# NOTE: This is intentionally simple and in-memory.  For horizontal scaling
# replace with Redis-backed counters.
# (NOTA: Intencionalmente simple y en memoria.  Para escalado horizontal
# reemplazar con contadores respaldados por Redis.)

class _SlidingWindowLimiter:
    """Per-IP sliding window rate limiter.
    (Rate limiter de ventana deslizante por IP.)
    """

    # Security: cap tracked IPs to prevent memory exhaustion from DDoS.
    # Seguridad: limitar IPs rastreadas para prevenir agotamiento de memoria por DDoS.
    _MAX_TRACKED_IPS = 10_000

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self._max: int = max_requests
        self._window: int = window_seconds
        self._buckets: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, ip: str) -> bool:
        """Return True if the IP is within its request budget.
        (Retorna True si la IP está dentro de su presupuesto de requests.)
        """
        now = time.monotonic()
        # Evict stale IPs when bucket count exceeds safety cap.
        # Eliminar IPs obsoletas cuando el conteo excede el límite de seguridad.
        if len(self._buckets) > self._MAX_TRACKED_IPS:
            stale = [k for k, v in self._buckets.items() if not v or now - v[-1] > self._window]
            for k in stale:
                del self._buckets[k]
        bucket = self._buckets[ip]
        # Evict expired timestamps (Eliminar timestamps expirados)
        while bucket and now - bucket[0] > self._window:
            bucket.popleft()
        if len(bucket) >= self._max:
            return False
        bucket.append(now)
        return True

    def reconfigure(self, max_requests: int, window_seconds: int) -> None:
        """Hot-reload limits without restart.
        (Reconfigura límites sin reiniciar.)
        """
        self._max = max_requests
        self._window = window_seconds


# ---------------------------------------------------------------------------
# IP blocklist helpers (Helpers de blocklist de IPs)
# ---------------------------------------------------------------------------

def _parse_blocklist(raw_list: list[str] | None) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse a list of IPs/CIDRs into network objects.
    (Parsea una lista de IPs/CIDRs en objetos de red.)

    Invalid entries are logged and skipped so a typo never crashes the API.
    (Entradas inválidas se loguean y se omiten para que un typo nunca
    rompa la API.)
    """
    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    if not raw_list:
        return nets
    for entry in raw_list:
        try:
            nets.append(ipaddress.ip_network(entry.strip(), strict=False))
        except ValueError:
            logger.warning("middleware_blocklist_invalid entry=%s", entry)
    return nets


def _ip_in_blocklist(
    ip_str: str,
    blocklist: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    """Check if an IP address falls within any blocked network.
    (Verifica si una IP cae dentro de alguna red bloqueada.)
    """
    if not blocklist:
        return False
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(addr in net for net in blocklist)


# ---------------------------------------------------------------------------
# The middleware class (La clase de middleware)
# ---------------------------------------------------------------------------

class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware enforcing Zero Trust principles on every request.
    (Middleware FastAPI que aplica principios Zero Trust en cada request.)

    Checks (in order):
      1. IP blocklist                → 403 Forbidden
      2. Sliding-window rate limit   → 429 Too Many Requests
      3. Request body size cap       → 413 Payload Too Large
      4. Suspicious header rejection → 400 Bad Request

    All checks are *disabled* when security.zero_trust is false (default).
    (Todos los chequeos están *deshabilitados* cuando security.zero_trust
    es false — por defecto.)
    """

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self._cfg = _load_security_config()
        self._enabled: bool = bool(self._cfg.get("zero_trust", False))

        # Rate-limit defaults (Valores por defecto de rate-limit)
        zt = self._cfg.get("zero_trust_config", {}) if isinstance(self._cfg.get("zero_trust_config"), dict) else {}
        self._limiter = _SlidingWindowLimiter(
            max_requests=int(zt.get("rate_limit_rpm", 60)),
            window_seconds=60,
        )
        self._max_body_bytes: int = int(zt.get("max_body_bytes", 1_048_576))  # 1 MB default

        # Blocklist (Lista de bloqueo)
        self._blocklist = _parse_blocklist(zt.get("ip_blocklist"))

        # Headers that should never appear in legitimate CNE polling traffic
        # (Headers que nunca deberían aparecer en tráfico legítimo de polling CNE)
        self._blocked_headers: set[str] = set(
            h.lower() for h in zt.get("blocked_headers", [])
        )

        if self._enabled:
            logger.info(
                "zero_trust_enabled blocklist=%d rate_limit=%d/min max_body=%d blocked_headers=%s",
                len(self._blocklist),
                self._limiter._max,
                self._max_body_bytes,
                list(self._blocked_headers) or "none",
            )

    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        """Process each request through the Zero Trust pipeline.
        (Procesa cada request a través del pipeline Zero Trust.)
        """
        # Fast-path: when disabled, pass through immediately
        # (Camino rápido: cuando está deshabilitado, pasa directo)
        if not self._enabled:
            return await call_next(request)

        client_ip = _extract_client_ip(request)

        # 1. IP blocklist (Lista de bloqueo de IPs)
        if _ip_in_blocklist(client_ip, self._blocklist):
            logger.warning("zero_trust_blocked_ip ip=%s path=%s", client_ip, request.url.path)
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden"},
            )

        # 2. Rate limiting (Limitación de tasa)
        if not self._limiter.is_allowed(client_ip):
            logger.warning("zero_trust_rate_limited ip=%s path=%s", client_ip, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": "60"},
            )

        # 3. Body size cap (Límite de tamaño de cuerpo)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self._max_body_bytes:
            logger.warning(
                "zero_trust_payload_too_large ip=%s bytes=%s",
                client_ip,
                content_length,
            )
            return JSONResponse(
                status_code=413,
                content={"detail": "Payload too large"},
            )

        # 4. Suspicious header rejection (Rechazo de headers sospechosos)
        if self._blocked_headers:
            for header in request.headers.keys():
                if header.lower() in self._blocked_headers:
                    logger.warning(
                        "zero_trust_blocked_header ip=%s header=%s",
                        client_ip,
                        header,
                    )
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Bad request"},
                    )

        # -- All checks passed (Todos los chequeos pasaron) --
        response = await call_next(request)

        # Append security headers (Agregar headers de seguridad)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


# ---------------------------------------------------------------------------
# Helpers (Funciones auxiliares)
# ---------------------------------------------------------------------------

def _extract_client_ip(request: Request) -> str:
    """Extract the real client IP respecting X-Forwarded-For behind a proxy.
    (Extrae la IP real del cliente respetando X-Forwarded-For detrás de proxy.)

    Falls back to request.client.host when the header is absent.
    (Recurre a request.client.host cuando el header está ausente.)
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in the chain is the original client
        # (La primera IP en la cadena es el cliente original)
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ---------------------------------------------------------------------------
# Registration helper (Helper de registro)
# ---------------------------------------------------------------------------

def install_zero_trust(app: FastAPI) -> None:
    """Install the Zero Trust middleware on a FastAPI app.
    (Instala el middleware Zero Trust en una app FastAPI.)

    Call this from main.py *after* CORS middleware so Zero Trust runs
    first in the middleware stack (outermost = runs first).
    (Llama esto desde main.py *después* del middleware CORS para que
    Zero Trust corra primero en el stack — el más externo corre primero.)

    Usage / Uso:
        from sentinel.api.middleware import install_zero_trust
        install_zero_trust(app)
    """
    app.add_middleware(ZeroTrustMiddleware)
    logger.info("zero_trust_middleware_installed")
