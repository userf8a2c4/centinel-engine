"""Paquete raíz para la distribución local de Centinel.

English:
    Root package shim for the local Centinel distribution.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_LOCAL_PACKAGE = _ROOT / "sentinel"
__path__ = [str(_LOCAL_PACKAGE), str(_ROOT)]
