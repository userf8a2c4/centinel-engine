"""Pruebas de estrés para resiliencia y reglas estadísticas.

Stress tests for resilience and statistical rules.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
import types

import pandas as pd
import pytest
import requests


def _install_apscheduler_stubs() -> None:
    """/** Instala stubs de apscheduler para tests. / Install apscheduler stubs for tests. **"""
    apscheduler_module = types.ModuleType("apscheduler")
    schedulers_module = types.ModuleType("apscheduler.schedulers")
    background_module = types.ModuleType("apscheduler.schedulers.background")
    blocking_module = types.ModuleType("apscheduler.schedulers.blocking")
    triggers_module = types.ModuleType("apscheduler.triggers")
    cron_module = types.ModuleType("apscheduler.triggers.cron")

    class DummyScheduler:
        """/** Scheduler dummy para pruebas. / Dummy scheduler for tests. **"""

        def __init__(self, *args, **kwargs):
            """Español: Función __init__ del módulo tests/test_stress.py.

            English: Function __init__ defined in tests/test_stress.py.
            """
            self.jobs = []

        def add_job(self, *args, **kwargs):
            """Español: Función add_job del módulo tests/test_stress.py.

            English: Function add_job defined in tests/test_stress.py.
            """
            self.jobs.append((args, kwargs))

        def start(self):
            """Español: Función start del módulo tests/test_stress.py.

            English: Function start defined in tests/test_stress.py.
            """
            return None

    class DummyCronTrigger:
        """/** Cron trigger dummy. / Dummy cron trigger. **"""

        def __init__(self, *args, **kwargs):
            """Español: Función __init__ del módulo tests/test_stress.py.

            English: Function __init__ defined in tests/test_stress.py.
            """
            self.args = args
            self.kwargs = kwargs

    background_module.BackgroundScheduler = DummyScheduler
    blocking_module.BlockingScheduler = DummyScheduler
    cron_module.CronTrigger = DummyCronTrigger

    sys.modules.setdefault("apscheduler", apscheduler_module)
    sys.modules.setdefault("apscheduler.schedulers", schedulers_module)
    sys.modules.setdefault("apscheduler.schedulers.background", background_module)
    sys.modules.setdefault("apscheduler.schedulers.blocking", blocking_module)
    sys.modules.setdefault("apscheduler.triggers", triggers_module)
    sys.modules.setdefault("apscheduler.triggers.cron", cron_module)


_install_apscheduler_stubs()

from core import analyze_rules  # noqa: E402
from scripts import download_and_hash  # noqa: E402
from scripts import run_pipeline  # noqa: E402


def _build_response(url: str) -> requests.Response:
    """/** Construye una respuesta HTTP mock. / Build a mock HTTP response. **"""
    response = requests.Response()
    response.status_code = 200
    response.url = url
    response._content = b"{}"
    return response


def test_download_with_retries_recovers_from_outages(monkeypatch):
    """/** Simula 5/19 fallas y verifica retries. / Simulate 5/19 failures and verify retries. **"""
    attempts: dict[str, int] = {}
    failing_urls = {f"https://cne.hn/data/{idx}" for idx in range(5)}

    def fake_get(self, url, timeout=10):
        """Español: Función fake_get del módulo tests/test_stress.py.

        English: Function fake_get defined in tests/test_stress.py.
        """
        # Incrementa intentos por URL. / Increment attempts per URL.
        attempts[url] = attempts.get(url, 0) + 1
        if url in failing_urls and attempts[url] == 1:
            raise requests.exceptions.ConnectionError("simulated outage")
        return _build_response(url)

    monkeypatch.setattr(requests.Session, "get", fake_get)

    urls = [f"https://cne.hn/data/{idx}" for idx in range(19)]
    responses = [download_and_hash.download_with_retries(url) for url in urls]

    assert all(response.status_code == 200 for response in responses)
    assert all(attempts[url] == 2 for url in failing_urls)
    assert all(attempts[url] == 1 for url in urls if url not in failing_urls)


def test_pipeline_checkpoint_resume(tmp_path, monkeypatch):
    """/** Verifica reanudación de checkpoint en pipeline. / Verify pipeline checkpoint resume. **"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    hashes_dir = tmp_path / "hashes"
    hashes_dir.mkdir()
    temp_dir = data_dir / "temp"
    temp_dir.mkdir()
    checkpoint_path = temp_dir / "checkpoint.json"

    monkeypatch.setattr(run_pipeline, "DATA_DIR", data_dir)
    monkeypatch.setattr(run_pipeline, "HASH_DIR", hashes_dir)
    monkeypatch.setattr(run_pipeline, "TEMP_DIR", temp_dir)
    monkeypatch.setattr(run_pipeline, "FAILURE_CHECKPOINT_PATH", checkpoint_path)

    snapshots = []
    for idx in range(19):
        snapshot_path = data_dir / f"snapshot_{idx}.json"
        snapshot_path.write_text(
            json.dumps(
                {"timestamp": datetime.now(timezone.utc).isoformat(), "id": idx}
            ),
            encoding="utf-8",
        )
        snapshots.append(snapshot_path)

    checkpoint_payload = {
        "run_id": "test",
        "current_index": 10,
        "processed_hashes": [f"hash_{idx}" for idx in range(10)],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    checkpoint_path.write_text(json.dumps(checkpoint_payload), encoding="utf-8")

    checkpoint = run_pipeline.load_resilience_checkpoint()
    processed_hashes, start_index, latest_snapshot = (
        run_pipeline.process_snapshot_queue(
            snapshots,
            checkpoint,
            run_id="test",
        )
    )

    updated_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    assert start_index == 10
    assert latest_snapshot == snapshots[-1]
    assert updated_payload["current_index"] == len(snapshots)
    assert len(updated_payload["processed_hashes"]) == len(snapshots)
    assert len(processed_hashes) == len(snapshots)


def test_rules_edge_cases_insufficient_data():
    """/** Valida retorno por datos insuficientes. / Validate insufficient data returns. **"""
    result = analyze_rules.apply_benford_law([])
    assert result["status"] == "INSUFICIENTE_DATOS"

    df = pd.DataFrame({"partido": ["A"], "votos": [1]})
    chi2_result = analyze_rules.check_distribution_chi2(df)
    assert chi2_result["status"] == "INSUFICIENTE_DATOS"


if __name__ == "__main__":
    # Ejemplo de uso / Usage example.
    raise SystemExit(pytest.main([__file__]))
