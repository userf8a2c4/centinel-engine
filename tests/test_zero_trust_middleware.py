from __future__ import annotations

import logging

from fastapi import FastAPI

from sentinel.api.middleware import ZeroTrustMiddleware, _is_production_environment


def test_is_production_environment_true(monkeypatch):
    monkeypatch.setenv("CENTINEL_ENV", "production")
    assert _is_production_environment() is True


def test_is_production_environment_false(monkeypatch):
    monkeypatch.delenv("CENTINEL_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    assert _is_production_environment() is False


def test_warn_when_zero_trust_disabled_in_production(monkeypatch, caplog):
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setattr("sentinel.api.middleware._load_security_config", lambda: {"zero_trust": False})

    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="centinel.middleware"):
        ZeroTrustMiddleware(app)

    assert "zero_trust_disabled_in_production" in caplog.text
