"""Pruebas para el rotador de proxies.

Proxy rotator tests.
"""

import logging

from centinel.proxy_handler import ProxyInfo, ProxyRotator


def test_proxy_rotator_falls_back_to_direct_after_failures() -> None:
    """Español: Cambia a modo directo tras fallos consecutivos.

    English: Switches to direct mode after repeated failures.
    """
    proxies = [ProxyInfo(url="http://proxy-1")]
    rotator = ProxyRotator(
        mode="rotating",
        proxies=proxies,
        rotation_strategy="round_robin",
        rotation_every_n=1,
        logger=logging.getLogger("tests.proxy"),
    )

    rotator.mark_failure("http://proxy-1", "timeout")
    rotator.mark_failure("http://proxy-1", "timeout")
    rotator.mark_failure("http://proxy-1", "timeout")

    assert proxies[0].dead is True
    assert rotator.mode == "direct"
    assert rotator.get_proxy_for_request() is None
