"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_proxy_rotator.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_proxy_rotator_falls_back_to_direct_after_failures

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_proxy_rotator.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_proxy_rotator_falls_back_to_direct_after_failures

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
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
