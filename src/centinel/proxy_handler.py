"""Proxy rotation, validation, and request routing for Centinel."""

from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import httpx
import yaml

DEFAULT_PROXY_TIMEOUT_SECONDS = 15.0
DEFAULT_PROXY_TEST_URL = "https://httpbin.org/ip"


@dataclass
class ProxyInfo:
    """Estado de un proxy en la sesión."""

    url: str
    consecutive_failures: int = 0
    dead: bool = False
    last_error: Optional[str] = None

    def mark_success(self) -> None:
        """Español: Función mark_success del módulo src/centinel/proxy_handler.py.

        English: Function mark_success defined in src/centinel/proxy_handler.py.
        """
        self.consecutive_failures = 0
        self.last_error = None

    def mark_failure(self, reason: str) -> None:
        """Español: Función mark_failure del módulo src/centinel/proxy_handler.py.

        English: Function mark_failure defined in src/centinel/proxy_handler.py.
        """
        self.consecutive_failures += 1
        self.last_error = reason
        if self.consecutive_failures >= 3:
            self.dead = True


class ProxyValidator:
    """Valida proxies al inicio con un timeout configurable."""

    def __init__(
        self,
        *,
        test_url: str = DEFAULT_PROXY_TEST_URL,
        timeout_seconds: float = 10.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Español: Función __init__ del módulo src/centinel/proxy_handler.py.

        English: Function __init__ defined in src/centinel/proxy_handler.py.
        """
        self.test_url = test_url
        self.timeout_seconds = timeout_seconds
        self.logger = logger or logging.getLogger(__name__)

    def validate(self, proxies: Iterable[str]) -> List[ProxyInfo]:
        """Prueba proxies y devuelve los que responden correctamente."""
        validated: List[ProxyInfo] = []
        timeout = httpx.Timeout(self.timeout_seconds)
        with httpx.Client(timeout=timeout) as client:
            for proxy_url in proxies:
                start = time.monotonic()
                try:
                    response = client.get(self.test_url, proxies=proxy_url)
                    elapsed = time.monotonic() - start
                    if response.status_code >= 400:
                        self.logger.warning(
                            "proxy_validation_failed",
                            proxy=proxy_url,
                            status_code=response.status_code,
                            elapsed_seconds=round(elapsed, 3),
                        )
                        continue
                    self.logger.info(
                        "proxy_validation_ok",
                        proxy=proxy_url,
                        status_code=response.status_code,
                        elapsed_seconds=round(elapsed, 3),
                    )
                    validated.append(ProxyInfo(url=proxy_url))
                except httpx.RequestError as exc:
                    elapsed = time.monotonic() - start
                    self.logger.warning(
                        "proxy_validation_error",
                        proxy=proxy_url,
                        elapsed_seconds=round(elapsed, 3),
                        error=str(exc),
                    )
        return validated


class ProxyRotator:
    """Rotador de proxies con soporte para lista fija o rotación."""

    def __init__(
        self,
        *,
        mode: str,
        proxies: List[ProxyInfo],
        rotation_strategy: str = "round_robin",
        rotation_every_n: int = 1,
        proxy_timeout_seconds: float = DEFAULT_PROXY_TIMEOUT_SECONDS,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Español: Función __init__ del módulo src/centinel/proxy_handler.py.

        English: Function __init__ defined in src/centinel/proxy_handler.py.
        """
        self.mode = mode
        self.rotation_strategy = rotation_strategy
        self.rotation_every_n = max(rotation_every_n, 1)
        self.proxy_timeout_seconds = proxy_timeout_seconds
        self.logger = logger or logging.getLogger(__name__)
        self._proxies = proxies
        self._current_index = 0
        self._requests_since_rotation = 0
        self._current_proxy: Optional[ProxyInfo] = None

    @property
    def active_proxies(self) -> List[ProxyInfo]:
        """Español: Función active_proxies del módulo src/centinel/proxy_handler.py.

        English: Function active_proxies defined in src/centinel/proxy_handler.py.
        """
        return [proxy for proxy in self._proxies if not proxy.dead]

    def _fallback_to_direct(self) -> None:
        """Español: Función _fallback_to_direct del módulo src/centinel/proxy_handler.py.

        English: Function _fallback_to_direct defined in src/centinel/proxy_handler.py.
        """
        if self.mode != "direct":
            self.logger.warning("proxy_fallback_direct", reason="no_active_proxies")
        self.mode = "direct"
        self._current_proxy = None

    def _select_next_proxy(self) -> Optional[ProxyInfo]:
        """Español: Función _select_next_proxy del módulo src/centinel/proxy_handler.py.

        English: Function _select_next_proxy defined in src/centinel/proxy_handler.py.
        """
        active = self.active_proxies
        if not active:
            self._fallback_to_direct()
            return None
        if self.rotation_strategy == "random":
            return random.choice(active)
        if self._current_index >= len(active):
            self._current_index = 0
        proxy = active[self._current_index]
        self._current_index = (self._current_index + 1) % len(active)
        return proxy

    def get_proxy_for_request(self) -> Optional[str]:
        """Obtiene el proxy para esta solicitud según la configuración."""
        if self.mode == "direct":
            return None
        active = self.active_proxies
        if not active:
            self._fallback_to_direct()
            return None
        if self.mode == "proxy_list":
            self._current_proxy = active[0]
            return self._current_proxy.url
        self._requests_since_rotation += 1
        if (
            self._current_proxy is None
            or self._requests_since_rotation >= self.rotation_every_n
        ):
            self._current_proxy = self._select_next_proxy()
            self._requests_since_rotation = 0
        return self._current_proxy.url if self._current_proxy else None

    def mark_success(self, proxy_url: str) -> None:
        """Español: Función mark_success del módulo src/centinel/proxy_handler.py.

        English: Function mark_success defined in src/centinel/proxy_handler.py.
        """
        proxy = self._find_proxy(proxy_url)
        if proxy:
            proxy.mark_success()

    def mark_failure(self, proxy_url: str, reason: str) -> None:
        """Español: Función mark_failure del módulo src/centinel/proxy_handler.py.

        English: Function mark_failure defined in src/centinel/proxy_handler.py.
        """
        proxy = self._find_proxy(proxy_url)
        if not proxy:
            return
        proxy.mark_failure(reason)
        if proxy.dead:
            self.logger.warning(
                "proxy_marked_dead",
                proxy=proxy.url,
                reason=proxy.last_error or "failure_threshold",
            )
        if not self.active_proxies:
            self._fallback_to_direct()

    def _find_proxy(self, proxy_url: str) -> Optional[ProxyInfo]:
        """Español: Función _find_proxy del módulo src/centinel/proxy_handler.py.

        English: Function _find_proxy defined in src/centinel/proxy_handler.py.
        """
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                return proxy
        return None


def load_proxy_config(config_path: Optional[Path] = None) -> dict:
    """Carga configuración de proxies desde YAML y variables de entorno."""
    path = config_path or Path(os.getenv("PROXY_CONFIG_PATH", "proxies.yaml"))
    payload: dict = {}
    if path.exists():
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def env(name: str, default: Optional[str] = None) -> Optional[str]:
        """Español: Función env del módulo src/centinel/proxy_handler.py.

        English: Function env defined in src/centinel/proxy_handler.py.
        """
        return os.getenv(name, default)

    proxies_env = env("PROXY_LIST")
    proxies = payload.get("proxies", []) if not proxies_env else proxies_env.split(",")
    proxies = [proxy.strip() for proxy in proxies if proxy.strip()]

    return {
        "mode": env("PROXY_MODE", str(payload.get("mode", "direct"))).lower(),
        "rotation_strategy": env(
            "PROXY_ROTATION_STRATEGY",
            str(payload.get("rotation_strategy", "round_robin")),
        ).lower(),
        "rotation_every_n": int(
            env("PROXY_ROTATION_EVERY_N", str(payload.get("rotation_every_n", 1)))
        ),
        "proxy_timeout_seconds": float(
            env(
                "PROXY_TIMEOUT_SECONDS",
                str(
                    payload.get("proxy_timeout_seconds", DEFAULT_PROXY_TIMEOUT_SECONDS)
                ),
            )
        ),
        "test_url": env(
            "PROXY_TEST_URL", str(payload.get("test_url", DEFAULT_PROXY_TEST_URL))
        ),
        "proxies": proxies,
    }


_ROTATOR: Optional[ProxyRotator] = None


def get_proxy_rotator(logger: Optional[logging.Logger] = None) -> ProxyRotator:
    """Inicializa y devuelve el rotador de proxies."""
    global _ROTATOR
    if _ROTATOR is not None:
        return _ROTATOR

    logger = logger or logging.getLogger(__name__)
    config = load_proxy_config()
    validator = ProxyValidator(
        test_url=config["test_url"],
        timeout_seconds=config["proxy_timeout_seconds"],
        logger=logger,
    )
    validated = validator.validate(config["proxies"])
    _ROTATOR = ProxyRotator(
        mode=config["mode"],
        proxies=validated,
        rotation_strategy=config["rotation_strategy"],
        rotation_every_n=config["rotation_every_n"],
        proxy_timeout_seconds=config["proxy_timeout_seconds"],
        logger=logger,
    )
    if config["mode"] != "direct" and not validated:
        logger.warning("proxy_startup_no_valid_proxies", fallback="direct")
        _ROTATOR.mode = "direct"
    return _ROTATOR
