"""Tests de inyección de fallas para resiliencia del pipeline.

English:
    Failure injection tests for pipeline resilience.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

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
            """Español: Función __init__ del módulo tests/test_failure_injection.py.

            English: Function __init__ defined in tests/test_failure_injection.py.
            """
            self.jobs = []

        def add_job(self, *args, **kwargs):
            """Español: Función add_job del módulo tests/test_failure_injection.py.

            English: Function add_job defined in tests/test_failure_injection.py.
            """
            self.jobs.append((args, kwargs))

        def start(self):
            """Español: Función start del módulo tests/test_failure_injection.py.

            English: Function start defined in tests/test_failure_injection.py.
            """
            return None

    class DummyCronTrigger:
        """/** Cron trigger dummy. / Dummy cron trigger. **"""

        def __init__(self, *args, **kwargs):
            """Español: Función __init__ del módulo tests/test_failure_injection.py.

            English: Function __init__ defined in tests/test_failure_injection.py.
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


def _install_crypto_stub() -> None:
    """/** Instala stub de cryptography.fernet para tests. / Install cryptography.fernet stub for tests. **"""
    cryptography_module = types.ModuleType("cryptography")
    fernet_module = types.ModuleType("cryptography.fernet")

    class DummyInvalidToken(Exception):
        """Dummy InvalidToken for tests."""

    class DummyFernet:
        """/** Fernet dummy para pruebas. / Dummy Fernet for tests. **"""

        def __init__(self, *_args, **_kwargs):
            """Español: Función __init__ del módulo tests/test_failure_injection.py.

            English: Function __init__ defined in tests/test_failure_injection.py.
            """
            return None

        @staticmethod
        def generate_key() -> bytes:
            """Español: Función generate_key del módulo tests/test_failure_injection.py.

            English: Function generate_key defined in tests/test_failure_injection.py.
            """
            return b"test-key"

        def encrypt(self, data: bytes) -> bytes:
            """Español: Función encrypt del módulo tests/test_failure_injection.py.

            English: Function encrypt defined in tests/test_failure_injection.py.
            """
            return data

        def decrypt(self, data: bytes) -> bytes:
            """Español: Función decrypt del módulo tests/test_failure_injection.py.

            English: Function decrypt defined in tests/test_failure_injection.py.
            """
            return data

    fernet_module.Fernet = DummyFernet
    fernet_module.InvalidToken = DummyInvalidToken

    sys.modules.setdefault("cryptography", cryptography_module)
    sys.modules.setdefault("cryptography.fernet", fernet_module)


_install_crypto_stub()


def _install_dotenv_stub() -> None:
    """/** Instala stub de dotenv para tests. / Install dotenv stub for tests. **"""
    dotenv_module = types.ModuleType("dotenv")

    def _load_dotenv(*_args, **_kwargs):
        """Español: Función _load_dotenv del módulo tests/test_failure_injection.py.

        English: Function _load_dotenv defined in tests/test_failure_injection.py.
        """
        return None

    dotenv_module.load_dotenv = _load_dotenv
    sys.modules.setdefault("dotenv", dotenv_module)


_install_dotenv_stub()

from scripts import run_pipeline


def _set_pipeline_paths(monkeypatch, base_path: Path) -> None:
    """Redirige rutas del pipeline a un directorio temporal.

    English:
        Redirect pipeline paths to a temporary directory.
    """
    monkeypatch.setattr(run_pipeline, "DATA_DIR", base_path / "data")
    monkeypatch.setattr(run_pipeline, "TEMP_DIR", base_path / "data" / "temp")
    monkeypatch.setattr(run_pipeline, "HASH_DIR", base_path / "hashes")
    monkeypatch.setattr(run_pipeline, "ANALYSIS_DIR", base_path / "analysis")
    monkeypatch.setattr(run_pipeline, "REPORTS_DIR", base_path / "reports")
    monkeypatch.setattr(run_pipeline, "ANCHOR_LOG_DIR", base_path / "logs" / "anchors")
    monkeypatch.setattr(
        run_pipeline, "STATE_PATH", base_path / "data" / "pipeline_state.json"
    )
    monkeypatch.setattr(
        run_pipeline,
        "PIPELINE_CHECKPOINT_PATH",
        base_path / "data" / "temp" / "pipeline_checkpoint.json",
    )
    monkeypatch.setattr(
        run_pipeline,
        "FAILURE_CHECKPOINT_PATH",
        base_path / "data" / "temp" / "checkpoint.json",
    )
    run_pipeline.DATA_DIR.mkdir(parents=True, exist_ok=True)
    run_pipeline.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    run_pipeline.HASH_DIR.mkdir(parents=True, exist_ok=True)
    run_pipeline.ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    run_pipeline.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_pipeline.ANCHOR_LOG_DIR.mkdir(parents=True, exist_ok=True)


def test_safe_run_pipeline_saves_checkpoint_on_connection_error(
    """Español: Función test_safe_run_pipeline_saves_checkpoint_on_connection_error del módulo tests/test_failure_injection.py.

    English: Function test_safe_run_pipeline_saves_checkpoint_on_connection_error defined in tests/test_failure_injection.py.
    """
    monkeypatch, tmp_path
) -> None:
    _set_pipeline_paths(monkeypatch, tmp_path)

    def _raise_connection_error(_config):
        """Español: Función _raise_connection_error del módulo tests/test_failure_injection.py.

        English: Function _raise_connection_error defined in tests/test_failure_injection.py.
        """
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(run_pipeline, "run_pipeline", _raise_connection_error)

    config = {"alerts": {}, "arbitrum": {"enabled": False}}
    run_pipeline.safe_run_pipeline(config)

    checkpoint_path = run_pipeline.FAILURE_CHECKPOINT_PATH
    assert checkpoint_path.exists()
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert payload["stage"] in {"unknown", "start"}
    assert "network down" in payload.get("error", "")


def test_run_pipeline_resumes_from_checkpoint(monkeypatch, tmp_path) -> None:
    """Español: Función test_run_pipeline_resumes_from_checkpoint del módulo tests/test_failure_injection.py.

    English: Function test_run_pipeline_resumes_from_checkpoint defined in tests/test_failure_injection.py.
    """
    _set_pipeline_paths(monkeypatch, tmp_path)
    snapshot_path = run_pipeline.DATA_DIR / "snapshot_resume.json"
    snapshot_path.write_text('{"resultados": {"foo": 1}}', encoding="utf-8")
    content_hash = run_pipeline.compute_content_hash(snapshot_path)

    checkpoint_payload = {
        "run_id": "resume-test",
        "stage": "normalize",
        "timestamp": "2029-01-01T00:00:00Z",
        "hashes": [],
        "snapshot_index": [{"file": snapshot_path.name, "mtime": 0}],
        "latest_snapshot": snapshot_path.name,
        "last_content_hash": content_hash,
    }
    run_pipeline.FAILURE_CHECKPOINT_PATH.write_text(
        json.dumps(checkpoint_payload, indent=2), encoding="utf-8"
    )

    commands: list[list[str]] = []

    monkeypatch.setattr(run_pipeline, "check_cne_connectivity", lambda *_args: True)
    monkeypatch.setattr(run_pipeline, "should_normalize", lambda *_args: False)

    def _record_command(command, _description):
        """Español: Función _record_command del módulo tests/test_failure_injection.py.

        English: Function _record_command defined in tests/test_failure_injection.py.
        """
        commands.append(command)

    monkeypatch.setattr(run_pipeline, "run_command", _record_command)
    monkeypatch.setattr(run_pipeline, "_anchor_snapshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_pipeline, "_anchor_if_due", lambda *_args, **_kwargs: None)

    config = {"alerts": {}, "arbitrum": {"enabled": False}}
    run_pipeline.run_pipeline(config)

    assert not any("download_and_hash.py" in command for command in commands)


def test_safe_run_pipeline_auto_resume_retries(monkeypatch, tmp_path) -> None:
    """Español: Función test_safe_run_pipeline_auto_resume_retries del módulo tests/test_failure_injection.py.

    English: Function test_safe_run_pipeline_auto_resume_retries defined in tests/test_failure_injection.py.
    """
    _set_pipeline_paths(monkeypatch, tmp_path)
    attempts = {"count": 0}

    def _flaky(_config):
        """Español: Función _flaky del módulo tests/test_failure_injection.py.

        English: Function _flaky defined in tests/test_failure_injection.py.
        """
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("boom")

    monkeypatch.setattr(run_pipeline, "run_pipeline", _flaky)
    monkeypatch.setattr(run_pipeline.time, "sleep", lambda *_args, **_kwargs: None)

    config = {
        "alerts": {},
        "arbitrum": {"enabled": False},
        "resilience": {
            "auto_resume": {
                "enabled": True,
                "max_attempts": 3,
                "backoff_base_seconds": 0,
                "backoff_max_seconds": 0,
                "retry_on": "any",
            }
        },
    }
    run_pipeline.safe_run_pipeline(config)

    assert attempts["count"] == 3


def test_emit_critical_alerts_writes_outputs(monkeypatch, tmp_path) -> None:
    """Español: Función test_emit_critical_alerts_writes_outputs del módulo tests/test_failure_injection.py.

    English: Function test_emit_critical_alerts_writes_outputs defined in tests/test_failure_injection.py.
    """
    _set_pipeline_paths(monkeypatch, tmp_path)
    alerts_log = tmp_path / "alerts.log"
    alerts_output = tmp_path / "data" / "alerts.json"

    config = {
        "alerts": {"log_path": str(alerts_log), "output_path": str(alerts_output)},
        "arbitrum": {"enabled": False},
    }
    critical_anomalies = [
        {"type": "CHAOS_SPIKE", "description": "Falla crítica", "file": "snap.json"}
    ]

    run_pipeline.emit_critical_alerts(critical_anomalies, config, run_id="run-1")

    assert alerts_log.exists()
    assert alerts_output.exists()
    payload = json.loads(alerts_output.read_text(encoding="utf-8"))
    assert payload[0]["alerts"][0]["severity"] == "CRITICAL"


def test_maybe_inject_chaos_failure_raises() -> None:
    """Español: Función test_maybe_inject_chaos_failure_raises del módulo tests/test_failure_injection.py.

    English: Function test_maybe_inject_chaos_failure_raises defined in tests/test_failure_injection.py.
    """
    resilience = {"chaos": {"enabled": True, "failure_rate": 1.0, "seed": 7}}
    rng = run_pipeline.build_chaos_rng(resilience)
    try:
        run_pipeline.maybe_inject_chaos_failure("download", resilience, rng)
    except RuntimeError as exc:
        assert "chaos_injected" in str(exc)
    else:
        raise AssertionError("Expected chaos injection to raise RuntimeError")
