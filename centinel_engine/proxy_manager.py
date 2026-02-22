"""Enhanced proxy rotation and User-Agent pool for stealth CNE access.
Bilingual: Rotacion mejorada de proxies y pool de User-Agents para acceso sigiloso al CNE.

Provides a large pool of real-world User-Agent strings (50+) and automatic proxy
rotation every 15 requests or upon detecting 429/403/5xx responses. Wraps the
existing ``src/centinel/proxy_handler.py`` rotator with additional hardening.

Provee un pool grande de cadenas User-Agent reales (50+) y rotacion automatica
de proxies cada 15 requests o al detectar respuestas 429/403/5xx. Envuelve
el rotador existente de ``src/centinel/proxy_handler.py`` con hardening adicional.
"""

from __future__ import annotations

import logging
import random
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from centinel_engine.config_loader import load_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User-Agent pool (50+ real browser strings, updated Feb 2026) /
# Pool de User-Agents (50+ cadenas reales de navegador, actualizado feb 2026)
# ---------------------------------------------------------------------------
_DEFAULT_USER_AGENTS: List[str] = [
    # Chrome Windows / Chrome en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome macOS / Chrome en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome Linux / Chrome en Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Firefox Windows / Firefox en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Firefox macOS / Firefox en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Firefox Linux / Firefox en Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Safari macOS / Safari en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    # Edge Windows / Edge en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    # Edge macOS / Edge en macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    # Opera / Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
    # Mobile Chrome / Chrome Movil
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    # Brave / Brave
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Brave/121",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Brave/121",
    # Vivaldi / Vivaldi
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.5",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.5",
]

# Request counter for proxy rotation / Contador de requests para rotacion de proxies
_ROTATION_INTERVAL: int = 15
# HTTP status codes that trigger immediate proxy rotation /
# Codigos HTTP que disparan rotacion inmediata de proxy
_ROTATION_TRIGGER_CODES: frozenset = frozenset({429, 403, 500, 502, 503, 504})


class ProxyAndUAManager:
    """Manages proxy rotation and User-Agent selection for each request.
    Bilingual: Gestiona la rotacion de proxies y la seleccion de User-Agent para cada request.

    Rotates User-Agent every request (random selection from pool).
    Rotates proxy every ``rotation_interval`` requests or when a trigger status
    code (429/403/5xx) is detected.

    Rota User-Agent en cada request (seleccion aleatoria del pool).
    Rota proxy cada ``rotation_interval`` requests o cuando se detecta un
    codigo de estado de disparo (429/403/5xx).
    """

    def __init__(
        self,
        proxy_list: Optional[List[str]] = None,
        user_agents: Optional[List[str]] = None,
        rotation_interval: int = _ROTATION_INTERVAL,
    ) -> None:
        """Initialize the proxy and UA manager.
        Bilingual: Inicializa el gestor de proxies y UA.

        Args:
            proxy_list: List of proxy URLs. Empty list means direct connection.
                        Lista de URLs de proxies. Lista vacia significa conexion directa.
            user_agents: Custom User-Agent list. Uses built-in pool if None.
                         Lista personalizada de User-Agents. Usa pool interno si es None.
            rotation_interval: Number of requests between proxy rotations (default 15).
                               Numero de requests entre rotaciones de proxy (default 15).
        """
        self._proxy_list: List[str] = list(proxy_list or [])
        self._user_agents: List[str] = list(user_agents or _DEFAULT_USER_AGENTS)
        self._rotation_interval: int = max(1, rotation_interval)
        self._request_count: int = 0
        self._current_proxy_index: int = 0
        self._lock: threading.Lock = threading.Lock()
        self._rng: random.Random = random.Random()

        logger.info(
            "ProxyAndUAManager initialized: proxies=%d, user_agents=%d, rotation_interval=%d / "
            "ProxyAndUAManager inicializado: proxies=%d, user_agents=%d, intervalo_rotacion=%d",
            len(self._proxy_list),
            len(self._user_agents),
            self._rotation_interval,
            len(self._proxy_list),
            len(self._user_agents),
            self._rotation_interval,
        )

    @property
    def proxy_count(self) -> int:
        """Number of configured proxies.
        Bilingual: Numero de proxies configurados.

        Returns:
            Integer count.
        """
        return len(self._proxy_list)

    @property
    def user_agent_count(self) -> int:
        """Number of available User-Agent strings.
        Bilingual: Numero de cadenas User-Agent disponibles.

        Returns:
            Integer count.
        """
        return len(self._user_agents)

    def get_proxy_and_ua(self) -> Tuple[Optional[Dict[str, str]], str]:
        """Get the next proxy dict and a random User-Agent for the current request.
        Bilingual: Obtiene el siguiente proxy dict y un User-Agent aleatorio para el request actual.

        Returns:
            Tuple of (proxy_dict_or_None, user_agent_string).
            proxy_dict is ``{"http": url, "https": url}`` or None for direct.

        Raises:
            RuntimeError: If User-Agent pool is empty (should never happen).
        """
        if not self._user_agents:
            raise RuntimeError(
                "User-Agent pool is empty / Pool de User-Agents esta vacio"
            )

        with self._lock:
            # Always rotate UA / Siempre rotar UA
            ua: str = self._rng.choice(self._user_agents)

            # Proxy rotation logic / Logica de rotacion de proxies
            if not self._proxy_list:
                return None, ua

            self._request_count += 1
            if self._request_count >= self._rotation_interval:
                self._rotate_proxy()

            proxy_url: str = self._proxy_list[self._current_proxy_index % len(self._proxy_list)]
            proxy_dict: Dict[str, str] = {
                "http": proxy_url,
                "https": proxy_url,
            }
            return proxy_dict, ua

    def notify_response_code(self, status_code: int) -> None:
        """Notify the manager of a response status code to trigger rotation if needed.
        Bilingual: Notifica al gestor de un codigo de respuesta para disparar rotacion si es necesario.

        Args:
            status_code: HTTP status code from the last response.
        """
        if status_code in _ROTATION_TRIGGER_CODES:
            with self._lock:
                logger.warning(
                    "Proxy rotation triggered by status %d / "
                    "Rotacion de proxy disparada por status %d",
                    status_code,
                    status_code,
                )
                self._rotate_proxy()

    def _rotate_proxy(self) -> None:
        """Advance to the next proxy in the list (must hold lock).
        Bilingual: Avanza al siguiente proxy en la lista (debe tener el lock).
        """
        if not self._proxy_list:
            return
        old_index: int = self._current_proxy_index
        self._current_proxy_index = (self._current_proxy_index + 1) % len(self._proxy_list)
        self._request_count = 0
        logger.debug(
            "Proxy rotated: index %d -> %d / Proxy rotado: indice %d -> %d",
            old_index,
            self._current_proxy_index,
            old_index,
            self._current_proxy_index,
        )


# ---------------------------------------------------------------------------
# Module-level factory / Factoria a nivel de modulo
# ---------------------------------------------------------------------------
_MANAGER: Optional[ProxyAndUAManager] = None
_MANAGER_LOCK: threading.Lock = threading.Lock()


def get_proxy_and_ua_manager(
    config_path: str = "config/prod/proxies.yaml",
) -> ProxyAndUAManager:
    """Return the global ProxyAndUAManager singleton.
    Bilingual: Retorna el singleton global de ProxyAndUAManager.

    Args:
        config_path: Path to proxies.yaml configuration file.

    Returns:
        The global ProxyAndUAManager instance.
    """
    global _MANAGER
    if _MANAGER is not None:
        return _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            # Load proxy list from config / Cargar lista de proxies desde config
            proxy_config: Dict = load_config(
                config_path,
                defaults={
                    "mode": "direct",
                    "proxies": [],
                    "rotation_every_n": _ROTATION_INTERVAL,
                },
            )
            proxy_list: List[str] = []
            mode: str = str(proxy_config.get("mode", "direct")).lower()
            if mode != "direct":
                raw_proxies = proxy_config.get("proxies", [])
                proxy_list = [p.strip() for p in raw_proxies if isinstance(p, str) and p.strip()]

            # Load custom UAs from file if available / Cargar UAs custom desde archivo si disponible
            user_agents: Optional[List[str]] = None
            ua_file: Path = Path("config/prod/user_agents.txt")
            if ua_file.exists():
                lines = ua_file.read_text(encoding="utf-8").strip().splitlines()
                custom_uas = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
                if len(custom_uas) >= 10:
                    user_agents = custom_uas
                    logger.info(
                        "Loaded %d custom User-Agents from %s / "
                        "Cargados %d User-Agents custom desde %s",
                        len(custom_uas),
                        ua_file,
                        len(custom_uas),
                        ua_file,
                    )

            rotation_interval: int = int(proxy_config.get("rotation_every_n", _ROTATION_INTERVAL))

            _MANAGER = ProxyAndUAManager(
                proxy_list=proxy_list,
                user_agents=user_agents,
                rotation_interval=rotation_interval,
            )
    return _MANAGER


def reset_proxy_manager() -> None:
    """Reset the global singleton (for testing only).
    Bilingual: Resetea el singleton global (solo para testing).
    """
    global _MANAGER
    with _MANAGER_LOCK:
        _MANAGER = None
