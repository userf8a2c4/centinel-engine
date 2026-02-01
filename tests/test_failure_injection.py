"""Tests de inyección de fallas para resiliencia del pipeline.

English:
    Failure injection tests for pipeline resilience.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

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
    monkeypatch, tmp_path
) -> None:
    _set_pipeline_paths(monkeypatch, tmp_path)

    def _raise_connection_error(_config):
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
        commands.append(command)

    monkeypatch.setattr(run_pipeline, "run_command", _record_command)
    monkeypatch.setattr(run_pipeline, "_anchor_snapshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_pipeline, "_anchor_if_due", lambda *_args, **_kwargs: None)

    config = {"alerts": {}, "arbitrum": {"enabled": False}}
    run_pipeline.run_pipeline(config)

    assert not any("download_and_hash.py" in command for command in commands)
