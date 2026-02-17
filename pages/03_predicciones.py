"""Wrapper for Streamlit multipage: Predicciones y NLP."""

import importlib
import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parents[1] / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

_mod = importlib.import_module("sentinel.dashboard.pages.03_predicciones")
