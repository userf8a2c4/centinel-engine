"""Wrapper for Streamlit multipage: Panel de Caos."""

# Streamlit auto-discovers this file from the root pages/ directory.
# The actual implementation lives in src/sentinel/dashboard/pages/04_panel_caos.py
# This wrapper ensures it works when running: streamlit run dashboard.py

import importlib
import sys
from pathlib import Path

# Ensure src/ is on the path
_src = str(Path(__file__).resolve().parents[1] / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Import and execute the actual page module
_mod = importlib.import_module("sentinel.dashboard.pages.04_panel_caos")
