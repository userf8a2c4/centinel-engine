from __future__ import annotations

from pathlib import Path

import pytest

from centinel_engine.config_loader import load_config


def test_load_config_rejects_path_traversal_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config" / "prod").mkdir(parents=True)
    (tmp_path / "config" / "prod" / "ok.yaml").write_text("a: 1", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid environment name"):
        load_config("ok.yaml", env="../prod")


def test_load_config_accepts_safe_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config" / "prod_safe").mkdir(parents=True)
    (tmp_path / "config" / "prod_safe" / "ok.yaml").write_text("a: 1", encoding="utf-8")

    assert load_config("ok.yaml", env="prod_safe") == {"a": 1}
