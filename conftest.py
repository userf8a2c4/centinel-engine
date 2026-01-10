"""Bloquea llamadas de red durante las pruebas y asegura el PYTHONPATH.

English:
    Blocks network calls during tests and ensures PYTHONPATH.
"""

from __future__ import annotations

from pathlib import Path
import socket
import sys
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent
PARENT_ROOT = REPO_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(PARENT_ROOT) in sys.path:
    sys.path.remove(str(PARENT_ROOT))


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impide conexiones de red reales en tests.

    English:
        Prevents real network connections in tests.
    """

    def guarded_connect(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network access is disabled during tests.")

    def guarded_create_connection(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network access is disabled during tests.")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect, raising=True)
    monkeypatch.setattr(
        socket, "create_connection", guarded_create_connection, raising=True
    )
