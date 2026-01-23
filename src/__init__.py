"""C.E.N.T.I.N.E.L. v5 abstraction package."""

from __future__ import annotations

import sys
from pathlib import Path

package_root = Path(__file__).resolve().parent
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))
