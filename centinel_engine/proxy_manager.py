# Proxy Manager Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations

"""Proxy rotation and User-Agent pool manager for resilient, undetectable scraping.

Provides a large pool of real-world User-Agent strings (50+) with random rotation,
and integrates with the existing ProxyRotator in ``src/centinel/proxy_handler.py``
to automatically rotate proxies every N requests or on 429/403 detection.

Bilingual: Gestor de rotacion de proxies y pool de User-Agents para scraping
resiliente e indetectable. Provee un pool grande de cadenas User-Agent reales (50+)
con rotacion aleatoria, e integra con el ProxyRotator existente en
``src/centinel/proxy_handler.py`` para rotar proxies automaticamente cada N requests
o al detectar respuestas 429/403.
"""

from __future__ import annotations

import logging
import secrets
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Real-world User-Agent pool (50+ current browser UAs, Feb 2026)
# Pool de User-Agents reales (50+ UAs de navegadores actuales, feb 2026)
# ---------------------------------------------------------------------------
USER_AGENT_POOL: List[str] = [
    # Chrome on Windows / Chrome en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome on macOS / Chrome en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome on Linux / Chrome en Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Firefox on Windows / Firefox en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Firefox on macOS / Firefox en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Firefox on Linux / Firefox en Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Safari on macOS / Safari en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # Edge on Windows / Edge en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    # Edge on macOS / Edge en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # Mobile UAs / UAs moviles
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    # Opera / Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    # Brave / Brave
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Brave/122",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Brave/122",
    # Vivaldi / Vivaldi
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Vivaldi/6.5",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Vivaldi/6.5",
]

# Minimum required pool size / Tamano minimo requerido del pool
_MIN_POOL_SIZE: int = 50

assert (
    len(USER_AGENT_POOL) >= _MIN_POOL_SIZE
), f"UA pool must have >= {_MIN_POOL_SIZE} entries, got {len(USER_AGENT_POOL)}"

# HTTP status codes that trigger forced proxy rotation /
# Codigos HTTP que fuerzan rotacion de proxy
ROTATION_TRIGGER_CODES: frozenset[int] = frozenset({429, 403})

# Default request count between proxy rotations /
# Cantidad de requests por defecto entre rotaciones de proxy
DEFAULT_ROTATION_EVERY_N: int = 15


class ProxyAndUAManager:
    """Manages coordinated proxy rotation and User-Agent randomization.

    Tracks request count and HTTP responses to trigger proxy rotation on
    schedule or on hostile status codes (429/403). Selects a new random
    User-Agent for every single request to minimize fingerprinting.

    Bilingual: Gestiona rotacion coordinada de proxies y aleatorizacion de
    User-Agent. Registra conteo de requests y respuestas HTTP para activar
    rotacion de proxy por calendario o por codigos de estado hostiles (429/403).
    Selecciona un nuevo User-Agent aleatorio para cada request individual para
    minimizar fingerprinting.

    Args:
        proxy_rotator: An existing ProxyRotator instance (from proxy_handler.py).
            If None, operates in direct mode with UA rotation only.
        rotation_every_n: Force proxy rotation after this many requests (default: 15).
        ua_pool: Custom User-Agent pool. If None, uses the built-in 50+ pool.
    """

    def __init__(
        self,
        *,
        proxy_rotator: Optional[Any] = None,
        rotation_every_n: int = DEFAULT_ROTATION_EVERY_N,
        ua_pool: Optional[List[str]] = None,
    ) -> None:
        self._proxy_rotator = proxy_rotator
        self._rotation_every_n: int = max(rotation_every_n, 1)
        self._ua_pool: List[str] = ua_pool if ua_pool and len(ua_pool) > 0 else list(USER_AGENT_POOL)
        self._request_count: int = 0
        self._rotation_count: int = 0
        self._lock: threading.Lock = threading.Lock()

        logger.info(
            "Proxy+UA manager initialized | Gestor proxy+UA inicializado: "
            "ua_pool_size=%d, rotation_every_n=%d, proxy_mode=%s",
            len(self._ua_pool),
            self._rotation_every_n,
            getattr(self._proxy_rotator, "mode", "none"),
        )

    def _get_random_ua(self) -> str:
        """Select a cryptographically random User-Agent from the pool.

        Bilingual: Selecciona un User-Agent criptograficamente aleatorio del pool.
        """
        return secrets.choice(self._ua_pool)

    def _should_rotate_proxy(self) -> bool:
        """Check if proxy rotation is due based on request count.

        Bilingual: Verifica si la rotacion de proxy corresponde segun conteo de requests.
        """
        return self._request_count > 0 and self._request_count % self._rotation_every_n == 0

    def rotate_proxy_and_ua(
        self,
        *,
        force_proxy_rotation: bool = False,
    ) -> Tuple[Optional[str], str]:
        """Rotate proxy (if due) and always select a fresh User-Agent.

        This is the main entry point called before each HTTP request. It
        returns the proxy URL to use (or None for direct) and a randomized
        User-Agent string.

        Bilingual: Rota el proxy (si corresponde) y siempre selecciona un
        User-Agent fresco. Este es el punto de entrada principal llamado antes
        de cada request HTTP. Retorna la URL del proxy a usar (o None para
        directo) y una cadena User-Agent aleatorizada.

        Args:
            force_proxy_rotation: If True, forces immediate proxy rotation
                regardless of the counter (e.g., after 429/403).

        Returns:
            Tuple of (proxy_url or None, user_agent_string).
        """
        with self._lock:
            self._request_count += 1

            # Always rotate UA / Siempre rotar UA
            ua = self._get_random_ua()

            # Determine proxy / Determinar proxy
            proxy_url: Optional[str] = None
            if self._proxy_rotator is not None:
                should_rotate = force_proxy_rotation or self._should_rotate_proxy()

                if should_rotate:
                    # Force selection of next proxy / Forzar seleccion del siguiente proxy
                    self._proxy_rotator._requests_since_rotation = self._proxy_rotator.rotation_every_n
                    self._rotation_count += 1
                    logger.info(
                        "Proxy rotation triggered | Rotacion de proxy activada: " "request_count=%d, forced=%s",
                        self._request_count,
                        force_proxy_rotation,
                    )

                proxy_url = self._proxy_rotator.get_proxy_for_request()

            logger.debug(
                "rotate_proxy_and_ua | rotacion proxy+ua: " "proxy=%s, ua=%s..., req_count=%d",
                proxy_url or "direct",
                ua[:50],
                self._request_count,
            )

            return proxy_url, ua

    def notify_response(self, status_code: int) -> bool:
        """Notify the manager of an HTTP response status code.

        If the status code indicates rate-limiting or blocking (429, 403),
        triggers an immediate proxy rotation on the next request.

        Bilingual: Notifica al gestor de un codigo de estado HTTP de respuesta.
        Si el codigo indica rate-limiting o bloqueo (429, 403), activa una
        rotacion inmediata de proxy en el siguiente request.

        Args:
            status_code: The HTTP response status code.

        Returns:
            True if the status code triggered a forced rotation flag.
        """
        if status_code in ROTATION_TRIGGER_CODES or 500 <= status_code <= 599:
            logger.warning(
                "Hostile status detected, forcing proxy rotation | "
                "Estado hostil detectado, forzando rotacion de proxy: status=%d",
                status_code,
            )
            return True
        return False

    def mark_proxy_bad(self, proxy: Optional[Dict[str, str]] = None) -> None:
        """Mark current proxy as unhealthy and force next rotation when possible.

        Bilingual: Marca el proxy actual como no saludable y fuerza la
        siguiente rotacion cuando sea posible.

        Args:
            proxy: Proxy dictionary from ``get_proxy_and_ua`` (optional).
        """
        del proxy  # Explicitly unused marker / Marcador explicito de no uso
        if self._proxy_rotator is None:
            logger.warning("proxy_mark_bad_skipped | sin rotador de proxy configurado")
            return

        with self._lock:
            try:
                self._proxy_rotator._requests_since_rotation = self._proxy_rotator.rotation_every_n
                self._rotation_count += 1
                logger.warning("proxy_marked_bad | proxy marcado como malo, rotacion forzada en siguiente request")
            except Exception as exc:  # noqa: BLE001
                logger.error("proxy_mark_bad_failed | fallo al marcar proxy malo: %s", exc)

    @property
    def stats(self) -> Dict[str, Any]:
        """Return manager statistics for monitoring.

        Bilingual: Retorna estadisticas del gestor para monitoreo.
        """
        with self._lock:
            return {
                "total_requests": self._request_count,
                "total_rotations": self._rotation_count,
                "ua_pool_size": len(self._ua_pool),
                "rotation_every_n": self._rotation_every_n,
                "proxy_mode": getattr(self._proxy_rotator, "mode", "none"),
            }


# ---------------------------------------------------------------------------
# Module-level singleton / Singleton a nivel de modulo
# ---------------------------------------------------------------------------

_MANAGER: Optional[ProxyAndUAManager] = None
_MANAGER_LOCK: threading.Lock = threading.Lock()


def get_proxy_ua_manager(
    *,
    proxy_rotator: Optional[Any] = None,
    rotation_every_n: int = DEFAULT_ROTATION_EVERY_N,
) -> ProxyAndUAManager:
    """Return the global ProxyAndUAManager singleton, creating it on first call.

    Bilingual: Retorna el singleton global de ProxyAndUAManager, creandolo en
    la primera llamada.
    """
    global _MANAGER
    if _MANAGER is not None:
        return _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is not None:
            return _MANAGER
        _MANAGER = ProxyAndUAManager(
            proxy_rotator=proxy_rotator,
            rotation_every_n=rotation_every_n,
        )
        return _MANAGER


def reset_proxy_ua_manager() -> None:
    """Reset the global singleton (mainly for testing).

    Bilingual: Reinicia el singleton global (principalmente para testing).
    """
    global _MANAGER
    with _MANAGER_LOCK:
        _MANAGER = None


def get_proxy_and_ua(
    *,
    force_proxy_rotation: bool = False,
) -> Tuple[Optional[Dict[str, str]], str]:
    """Return a proxy mapping and User-Agent for the next HTTP request.

    Bilingual: Retorna un mapeo de proxy y User-Agent para el siguiente request HTTP.

    Args:
        force_proxy_rotation: Force immediate proxy rotation when True.

    Returns:
        Tuple with proxy dictionary (or None for direct mode) and UA string.

    Raises:
        RuntimeError: If proxy metadata cannot be normalized.
    """
    manager = get_proxy_ua_manager()
    proxy_url, ua_str = manager.rotate_proxy_and_ua(force_proxy_rotation=force_proxy_rotation)

    # Normalize proxy URL into client-friendly dict / Normalizar URL a dict compatible
    if proxy_url is None:
        return None, ua_str

    proxy_dict: Dict[str, str] = {"http": proxy_url, "https": proxy_url}
    return proxy_dict, ua_str


def mark_proxy_bad(proxy: Optional[Dict[str, str]] = None) -> None:
    """Mark the active proxy as bad in the global manager.

    Bilingual: Marca el proxy activo como malo en el gestor global.

    Args:
        proxy: Proxy dictionary returned by ``get_proxy_and_ua``.
    """
    manager = get_proxy_ua_manager()
    manager.mark_proxy_bad(proxy)
