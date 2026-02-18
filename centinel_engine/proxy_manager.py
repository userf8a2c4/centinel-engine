"""Proxy and User-Agent rotation manager for resilient scraping.

Bilingual: Gestor de rotación de proxy y User-Agent para scraping resiliente.
"""

from __future__ import annotations

import logging
import secrets
import threading
from typing import Any, Dict, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

DEFAULT_ROTATION_EVERY_N = 5
ROTATION_TRIGGER_CODES = {403, 429}

USER_AGENT_POOL = (
    [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/120.0.0.0 Safari/537.36",
    ]
    + [
        f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{110+i}.0.0.0 Safari/537.36"
        for i in range(20)
    ]
    + [f"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:{102+i}.0) Gecko/20100101 Firefox/{102+i}.0" for i in range(14)]
    + [
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 13_{i}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.{i} Safari/605.1.15"
        for i in range(8)
    ]
    + [
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/{115+i}.0.0.0 Safari/537.36"
        for i in range(8)
    ]
)


class ProxyAndUAManager:
    """Select proxies and User-Agents with deterministic guardrails.

    Bilingual: Selecciona proxies y User-Agents con barreras determinísticas.

    Args:
        proxy_rotator: Optional rotator object exposing `get_proxy_for_request()`.
        rotation_every_n: Rotate proxy after N requests.
        ua_pool: Candidate User-Agent pool.

    Returns:
        None: Class constructor.

    Raises:
        ValueError: If rotation cadence is invalid or UA pool is empty.
    """

    def __init__(
        self,
        proxy_rotator: Optional[Any] = None,
        rotation_every_n: int = DEFAULT_ROTATION_EVERY_N,
        ua_pool: Optional[Sequence[str]] = None,
    ) -> None:
        if rotation_every_n < 1:
            raise ValueError("rotation_every_n must be >= 1")
        self.proxy_rotator = proxy_rotator
        self.rotation_every_n = rotation_every_n
        self.ua_pool = list(ua_pool or USER_AGENT_POOL)
        if not self.ua_pool:
            raise ValueError("ua_pool cannot be empty")

        self._lock = threading.Lock()
        self._request_count = 0
        self._rotation_count = 0
        self._last_proxy_url: Optional[str] = None
        self._last_ua: Optional[str] = None
        self._force_rotation = True

    def _pick_proxy_url(self) -> Optional[str]:
        """Select proxy URL from rotator, gracefully falling back to direct mode.

        Bilingual: Selecciona URL de proxy desde el rotador con fallback a modo directo.

        Args:
            None.

        Returns:
            Optional[str]: Proxy URL or `None` for direct mode.

        Raises:
            None.
        """
        if self.proxy_rotator is None:
            return None
        try:
            return self.proxy_rotator.get_proxy_for_request()
        except Exception as exc:  # noqa: BLE001
            logger.warning("proxy_rotation_failed | fallback_direct_mode: %s", exc)
            return None

    def _maybe_rotate_proxy(self, force_proxy_rotation: bool) -> None:
        """Rotate proxy based on trigger flags and cadence.

        Bilingual: Rota proxy según flags de disparo y cadencia.

        Args:
            force_proxy_rotation: Whether to force immediate proxy rotation.

        Returns:
            None.

        Raises:
            None.
        """
        should_rotate = (
            force_proxy_rotation
            or self._force_rotation
            or (self._request_count % self.rotation_every_n == 0)
            or self._last_proxy_url is None
        )
        if should_rotate:
            self._last_proxy_url = self._pick_proxy_url()
            self._rotation_count += 1
            self._force_rotation = False

    def rotate_proxy_and_ua(self, force_proxy_rotation: bool = False) -> Tuple[Optional[Dict[str, str]], str]:
        """Return current proxy mapping and newly selected User-Agent.

        Bilingual: Retorna proxy actual y un User-Agent recién seleccionado.

        Args:
            force_proxy_rotation: Force rotation regardless of cadence.

        Returns:
            tuple[Optional[dict[str, str]], str]: Proxy mapping for `requests` and UA string.

        Raises:
            None.
        """
        with self._lock:
            self._request_count += 1
            self._maybe_rotate_proxy(force_proxy_rotation)
            self._last_ua = secrets.choice(self.ua_pool)
            proxy_payload = None
            if self._last_proxy_url:
                proxy_payload = {"http": self._last_proxy_url, "https": self._last_proxy_url}
            return proxy_payload, self._last_ua

    def notify_response(self, status_code: int) -> bool:
        """Report response status and return whether rotation is recommended.

        Bilingual: Reporta status de respuesta y retorna si conviene rotar.

        Args:
            status_code: HTTP status code from upstream request.

        Returns:
            bool: `True` when status suggests proxy rotation.

        Raises:
            None.
        """
        should_rotate = int(status_code) in ROTATION_TRIGGER_CODES
        if should_rotate:
            with self._lock:
                self._force_rotation = True
        return should_rotate

    @property
    def stats(self) -> dict[str, Any]:
        """Expose manager metrics for observability and tests.

        Bilingual: Expone métricas del gestor para observabilidad y pruebas.

        Args:
            None.

        Returns:
            dict[str, Any]: Runtime counters and mode indicators.

        Raises:
            None.
        """
        with self._lock:
            return {
                "total_requests": self._request_count,
                "total_rotations": self._rotation_count,
                "ua_pool_size": len(self.ua_pool),
                "proxy_mode": "proxy" if self._last_proxy_url else "direct",
                "last_proxy": self._last_proxy_url,
                "last_ua": self._last_ua,
            }

    def mark_proxy_bad(self, proxy: Optional[Dict[str, str]] = None) -> None:
        """Mark current proxy as unhealthy and request immediate rotation.

        Bilingual: Marca proxy actual como no saludable y fuerza rotación inmediata.

        Args:
            proxy: Optional proxy payload associated with the failed request.

        Returns:
            None.

        Raises:
            None.
        """
        _ = proxy
        with self._lock:
            self._force_rotation = True


_proxy_ua_manager_singleton: Optional[ProxyAndUAManager] = None
_proxy_manager_lock = threading.Lock()


def get_proxy_ua_manager(
    proxy_rotator: Optional[Any] = None,
    rotation_every_n: int = DEFAULT_ROTATION_EVERY_N,
    ua_pool: Optional[Sequence[str]] = None,
) -> ProxyAndUAManager:
    """Return singleton proxy/UA manager.

    Bilingual: Retorna el singleton del gestor de proxy/UA.

    Args:
        proxy_rotator: Optional proxy rotator implementation.
        rotation_every_n: Proxy rotation cadence.
        ua_pool: Optional custom User-Agent pool.

    Returns:
        ProxyAndUAManager: Shared manager instance.

    Raises:
        None.
    """
    global _proxy_ua_manager_singleton
    with _proxy_manager_lock:
        if _proxy_ua_manager_singleton is None:
            _proxy_ua_manager_singleton = ProxyAndUAManager(
                proxy_rotator=proxy_rotator,
                rotation_every_n=rotation_every_n,
                ua_pool=ua_pool,
            )
        return _proxy_ua_manager_singleton


def reset_proxy_ua_manager() -> None:
    """Reset singleton manager for tests and controlled restarts.

    Bilingual: Reinicia el singleton del gestor para pruebas y reinicios controlados.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """
    global _proxy_ua_manager_singleton
    with _proxy_manager_lock:
        _proxy_ua_manager_singleton = None


def get_proxy_and_ua() -> Tuple[Optional[Dict[str, str]], str]:
    """Convenience wrapper returning rotated proxy and User-Agent.

    Bilingual: Helper que retorna proxy y User-Agent rotados.

    Args:
        None.

    Returns:
        tuple[Optional[dict[str, str]], str]: Selected proxy payload and UA.

    Raises:
        None.
    """
    return get_proxy_ua_manager().rotate_proxy_and_ua()


def mark_proxy_bad(proxy: Optional[Dict[str, str]] = None) -> None:
    """Convenience wrapper to mark proxy as bad.

    Bilingual: Helper para marcar un proxy como defectuoso.

    Args:
        proxy: Proxy payload associated with a failed request.

    Returns:
        None.

    Raises:
        None.
    """
    get_proxy_ua_manager().mark_proxy_bad(proxy)
