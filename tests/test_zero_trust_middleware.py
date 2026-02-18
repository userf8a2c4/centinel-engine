"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_zero_trust_middleware.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_is_production_environment_true
  - test_is_production_environment_false
  - test_warn_when_zero_trust_disabled_in_production
  - test_ignores_forwarded_for_when_proxy_not_trusted
  - test_rejects_invalid_content_length

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_zero_trust_middleware.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_is_production_environment_true
  - test_is_production_environment_false
  - test_warn_when_zero_trust_disabled_in_production
  - test_ignores_forwarded_for_when_proxy_not_trusted
  - test_rejects_invalid_content_length

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from centinel.api.middleware import ZeroTrustMiddleware, _is_production_environment


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
    monkeypatch.setattr("centinel.api.middleware._load_security_config", lambda: {"zero_trust": False})

    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="centinel.middleware"):
        ZeroTrustMiddleware(app)

    assert "zero_trust_disabled_in_production" in caplog.text


def test_ignores_forwarded_for_when_proxy_not_trusted(monkeypatch, caplog):
    monkeypatch.setattr(
        "centinel.api.middleware._load_security_config",
        lambda: {
            "zero_trust": True,
            "zero_trust_config": {
                "trusted_proxy_cidrs": ["10.0.0.0/8"],
            },
        },
    )

    app = FastAPI()

    @app.get("/whoami")
    def whoami(request: Request):
        return {"client": request.client.host}

    app.add_middleware(ZeroTrustMiddleware)
    client = TestClient(app)

    with caplog.at_level(logging.WARNING, logger="centinel.middleware"):
        response = client.get("/whoami", headers={"x-forwarded-for": "203.0.113.88"})
    assert response.status_code == 200
    assert "zero_trust_untrusted_proxy_ignored" in caplog.text


def test_rejects_invalid_content_length(monkeypatch):
    monkeypatch.setattr(
        "centinel.api.middleware._load_security_config",
        lambda: {
            "zero_trust": True,
            "zero_trust_config": {},
        },
    )

    app = FastAPI()

    @app.post("/echo")
    def echo() -> dict:
        return {"ok": True}

    app.add_middleware(ZeroTrustMiddleware)
    client = TestClient(app)

    response = client.post("/echo", headers={"content-length": "NaN"}, content=b"x")
    assert response.status_code == 400
