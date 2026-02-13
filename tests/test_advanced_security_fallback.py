"""Regression tests for optional dependency fallbacks in advanced_security."""

from __future__ import annotations

import builtins
import importlib
import sys
from types import ModuleType


def test_psutil_fallback_binds_symbol_when_dependency_missing(monkeypatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "psutil":
            raise ModuleNotFoundError("No module named 'psutil'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    cached_module: ModuleType | None = sys.modules.pop("core.advanced_security", None)
    try:
        module = importlib.import_module("core.advanced_security")
        assert hasattr(module, "psutil")
        assert module.psutil.cpu_percent() == 0.0
        assert module.psutil.virtual_memory().percent == 0.0
    finally:
        sys.modules.pop("core.advanced_security", None)
        if cached_module is not None:
            sys.modules["core.advanced_security"] = cached_module
