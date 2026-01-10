"""Ajusta sys.path para priorizar el paquete local de Sentinel.

English:
    Adjusts sys.path to prioritize the local Sentinel package.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent
PARENT_ROOT = REPO_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(PARENT_ROOT) in sys.path:
    sys.path.remove(str(PARENT_ROOT))
