"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `core/http_compat.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - HttpResponse
  - RequestsCompat
  - _RequestsNamespace

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `core/http_compat.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - HttpResponse
  - RequestsCompat
  - _RequestsNamespace

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Http Compat Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations



from __future__ import annotations

import importlib
import importlib.util
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class HttpResponse:
    """Minimal response surface used by security modules."""

    status_code: int
    text: str = ""


class RequestsCompat:
    """Subset of requests-like API used when requests is unavailable."""

    @staticmethod
    def post(url: str, json_payload: dict[str, Any] | None = None, timeout: int = 10, **_kwargs: Any) -> HttpResponse:
        body = b""
        if json_payload is not None:
            body = json.dumps(json_payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - URL validated by caller
                payload = resp.read().decode("utf-8", errors="ignore")
                return HttpResponse(status_code=int(getattr(resp, "status", 200)), text=payload)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="ignore")
            return HttpResponse(status_code=int(exc.code), text=text)
        except Exception:
            return HttpResponse(status_code=503, text="http_post_failed")


class _RequestsNamespace:
    """Expose requests-like namespace for monkeypatch compatibility."""

    _real_requests_post = None

    @classmethod
    def _get_real_post(cls):
        if cls._real_requests_post is not None:
            return cls._real_requests_post
        if importlib.util.find_spec("requests") is None:
            cls._real_requests_post = RequestsCompat.post
            return cls._real_requests_post
        try:
            cls._real_requests_post = importlib.import_module("requests").post
        except Exception:
            cls._real_requests_post = RequestsCompat.post
        return cls._real_requests_post

    @classmethod
    def post(
        cls, url: str, timeout: int = 10, json: dict[str, Any] | None = None, **kwargs: Any
    ) -> HttpResponse:  # noqa: A002
        post_func = cls._get_real_post()
        if post_func is RequestsCompat.post:
            return RequestsCompat.post(url=url, json_payload=json, timeout=timeout, **kwargs)
        return post_func(url, timeout=timeout, json=json, **kwargs)


requests = _RequestsNamespace()
