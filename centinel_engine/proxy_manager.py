"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `centinel_engine/proxy_manager.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - ProxyAndUAManager
  - get_proxy_ua_manager
  - reset_proxy_ua_manager
  - get_proxy_and_ua
  - mark_proxy_bad

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `centinel_engine/proxy_manager.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - ProxyAndUAManager
  - get_proxy_ua_manager
  - reset_proxy_ua_manager
  - get_proxy_and_ua
  - mark_proxy_bad

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
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
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36"
        for version in range(108, 136)
    ]
    + [
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0"
        for version in range(102, 130)
    ]
    + [
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 13_{version}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.{version} Safari/605.1.15"
        for version in range(0, 12)
    ]
    + [
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/{version}.0.0.0 Safari/537.36"
        for version in range(115, 131)
    ]
)

_ACCEPT_POOL = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "application/json,text/plain,*/*",
    "text/html,application/xml;q=0.9,*/*;q=0.8",
)
_LANGUAGE_POOL = (
    "es-HN,es-419;q=0.9,es;q=0.8,en;q=0.6",
    "es-419,es;q=0.9,en-US;q=0.6,en;q=0.5",
    "en-US,en;q=0.8,es-HN;q=0.6,es;q=0.4",
)
_FETCH_MODE_POOL = ("navigate", "cors", "no-cors")
_REFERER_POOL = ("", "https://www.cne.hn/", "https://www.google.com/")


class ProxyAndUAManager:
    """Select proxies and User-Agents with deterministic guardrails.

    Bilingual: Selecciona proxies y User-Agents con barreras determinísticas.
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

    def build_request_headers(self, user_agent: str) -> Dict[str, str]:
        """Build randomized anti-fingerprinting request headers.

        Bilingual: Construye headers aleatorios anti-fingerprinting.

        Args:
            user_agent: Selected User-Agent for the current request.

        Returns:
            Dict[str, str]: HTTP header mapping with varied neutral values.

        Raises:
            None.
        """
        headers: Dict[str, str] = {
            "User-Agent": user_agent,
            "Accept": secrets.choice(_ACCEPT_POOL),
            "Accept-Language": secrets.choice(_LANGUAGE_POOL),
            "Sec-Fetch-Mode": secrets.choice(_FETCH_MODE_POOL),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        referer = secrets.choice(_REFERER_POOL)
        if referer:
            headers["Referer"] = referer
        return headers

    def rotate_proxy_and_ua(self, force_proxy_rotation: bool = False) -> Tuple[Optional[Dict[str, str]], str]:
        """Return current proxy mapping and newly selected User-Agent.

        Bilingual: Retorna proxy actual y un User-Agent recién seleccionado.
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
    """
    global _proxy_ua_manager_singleton
    with _proxy_manager_lock:
        _proxy_ua_manager_singleton = None


def get_proxy_and_ua() -> Tuple[Optional[Dict[str, str]], str]:
    """Convenience wrapper returning rotated proxy and User-Agent.

    Bilingual: Helper que retorna proxy y User-Agent rotados.
    """
    return get_proxy_ua_manager().rotate_proxy_and_ua()


def mark_proxy_bad(proxy: Optional[Dict[str, str]] = None) -> None:
    """Convenience wrapper to mark proxy as bad.

    Bilingual: Helper para marcar un proxy como defectuoso.
    """
    get_proxy_ua_manager().mark_proxy_bad(proxy)
