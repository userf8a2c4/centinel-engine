"""Tests for proactive endpoint monitor script.

English: Validates scheduler behavior and daemon-safe loop semantics.
Español: Valida comportamiento del scheduler y semántica segura del bucle daemon.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path("scripts/monitor_endpoints.py")


def _load_monitor_module():
    """English: Dynamically load monitor script module from scripts path.
    Español: Carga dinámicamente el módulo del monitor desde scripts.
    """

    spec = importlib.util.spec_from_file_location("monitor_endpoints", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_parser_accepts_interval_choices() -> None:
    module = _load_monitor_module()

    args = module.build_parser().parse_args(["--interval", "60"])

    assert args.interval == 60


def test_main_once_runs_single_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_monitor_module()
    calls: list[str] = []

    class DummyHealer:
        def __init__(self, _path: str) -> None:
            calls.append("init")

    def fake_scan(_healer):
        calls.append("scan")
        return {"scan_status": "success"}

    monkeypatch.setattr(module, "CNEEndpointHealer", DummyHealer)
    monkeypatch.setattr(module, "run_proactive_scan", fake_scan)
    monkeypatch.setattr("sys.argv", ["monitor_endpoints.py", "--once"])

    rc = module.main()

    assert rc == 0
    assert calls == ["init", "scan"]


def test_run_loop_sleeps_between_scans(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_monitor_module()
    calls: list[int] = []

    class DummyHealer:
        def __init__(self, _path: str) -> None:
            return None

    def fake_scan(_healer):
        calls.append(1)
        return {"scan_status": "success"}

    def fake_sleep(_seconds: int) -> None:
        raise RuntimeError("stop-loop")

    monkeypatch.setattr(module, "CNEEndpointHealer", DummyHealer)
    monkeypatch.setattr(module, "run_proactive_scan", fake_scan)
    monkeypatch.setattr(module.time, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-loop"):
        module.run_loop(30)

    assert len(calls) == 1


def test_build_parser_accepts_adaptive_flag() -> None:
    module = _load_monitor_module()

    args = module.build_parser().parse_args(["--adaptive-animal-mode"])

    assert args.adaptive_animal_mode is True


def test_run_loop_uses_recommended_interval_in_animal_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_monitor_module()

    class DummyHealer:
        def __init__(self, _path: str) -> None:
            return None

    def fake_scan(_healer):
        return {"scan_status": "degraded", "recommended_interval_minutes": 10}

    observed: list[int] = []

    def fake_sleep(seconds: int) -> None:
        observed.append(seconds)
        raise RuntimeError("stop-loop")

    monkeypatch.setattr(module, "CNEEndpointHealer", DummyHealer)
    monkeypatch.setattr(module, "run_proactive_scan", fake_scan)
    monkeypatch.setattr(module.time, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-loop"):
        module.run_loop(30, adaptive_animal_mode=True)

    assert observed == [600]
