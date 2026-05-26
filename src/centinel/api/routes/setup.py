"""
Endpoints de configuración inicial y regeneración de seeds.
Initial setup and seed regeneration endpoints.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from centinel.countries import LATAM_COUNTRIES, list_countries
from centinel.seed_pdf import generate_seeds, hash_seeds, generate_pdf, SEED1_SALT, SEED1_ITERS

logger = logging.getLogger("centinel.api.setup")


def _sl(value: str) -> str:
    """Sanitize a value for safe log inclusion (prevents log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")

router = APIRouter(prefix="/api/setup", tags=["setup"])

_BASE = Path(__file__).resolve().parents[4]
_ACCESS_JSON = _BASE / "web" / "access.json"
_SETUP_MARKER = _BASE / ".centinel-setup.json"
_CONFIG_YAML = _BASE / "command_center" / "config.yaml"


def _read_setup() -> dict:
    if not _SETUP_MARKER.exists():
        return {}
    try:
        return json.loads(_SETUP_MARKER.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_access() -> dict:
    if not _ACCESS_JSON.exists():
        return {}
    try:
        return json.loads(_ACCESS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_access(hashes: dict[str, str]) -> None:
    payload = {
        "version": 1,
        "algo": "PBKDF2-SHA256",
        "salt": SEED1_SALT,
        "iterations": SEED1_ITERS,
        "seeds": hashes,
    }
    _ACCESS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _ACCESS_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _verify_seed(seed_label: str, seed_value: str) -> bool:
    """Verify a plaintext seed against the stored PBKDF2 hash."""
    access = _read_access()
    stored_hashes = access.get("seeds", {})
    expected = stored_hashes.get(seed_label)
    if not expected:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", seed_value.encode(), SEED1_SALT.encode(), SEED1_ITERS
    ).hex()
    # Constant-time comparison
    return hashlib.compare_digest(actual, expected)


def _pdf_response(seeds: dict, country_name: str, country_flag: str, code: str) -> Response:
    pdf_bytes = generate_pdf(seeds, country_name, country_flag)
    filename = f"centinel-seeds-{code.lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _update_config_yaml(code: str) -> None:
    """Patch command_center/config.yaml with the selected country's CNE domain."""
    if not _CONFIG_YAML.exists():
        return
    try:
        import yaml
        text = _CONFIG_YAML.read_text(encoding="utf-8")
        cfg = yaml.safe_load(text) or {}

        country = LATAM_COUNTRIES[code]
        # Extract domain from url_pattern if available
        domain = None
        if country.url_pattern:
            from urllib.parse import urlparse
            domain = urlparse(country.url_pattern).netloc
        if not domain:
            # Fallback: derive from authority abbreviation
            code_lower = code.lower()
            domain = f"cne.{code_lower}"

        cfg["cne_domains"] = [domain]
        cfg["country_code"] = code
        cfg["country_name"] = country.name

        _CONFIG_YAML.write_text(
            yaml.dump(cfg, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        logger.info("config_yaml_updated country=%s domain=%s", _sl(code), _sl(domain))
    except Exception as exc:
        logger.warning("config_yaml_update_failed country=%s error=%s", _sl(code), _sl(str(exc)))


# ── Request models ────────────────────────────────────────────────────────────


class InitRequest(BaseModel):
    country_code: str


class RegenerateRequest(BaseModel):
    country_code: str | None = None
    seed_label: str          # e.g. "S1-A"
    seed_value: str          # plaintext seed to authenticate


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/status")
def setup_status() -> dict:
    """Retorna si el sistema ya fue configurado."""
    setup = _read_setup()
    return {
        "configured": bool(setup),
        "country_code": setup.get("country_code"),
        "country_name": setup.get("country_name"),
        "configured_at": setup.get("configured_at"),
        "last_regenerated_at": setup.get("last_regenerated_at"),
    }


@router.get("/countries")
def get_countries() -> list[dict]:
    """Retorna la lista de países LATAM con sus presets."""
    return [
        {
            "code": c.code,
            "name": c.name,
            "flag": c.flag,
            "authority": c.authority,
            "divisions_label": c.divisions_label,
            "divisions_count": c.divisions_count,
        }
        for c in list_countries()
    ]


@router.get("/access.json")
def get_access_json():
    """Sirve web/access.json para que el panel OPS pueda verificar seeds localmente."""
    if not _ACCESS_JSON.exists():
        raise HTTPException(status_code=404, detail="access.json not found. Run setup first.")
    return FileResponse(_ACCESS_JSON, media_type="application/json")


@router.post("/init")
def setup_init(req: InitRequest) -> Response:
    """
    Configura el sistema por primera vez.
    Genera 12 seeds, guarda hashes en access.json y retorna el PDF.
    Solo funciona si el sistema no ha sido configurado.
    """
    if _SETUP_MARKER.exists():
        raise HTTPException(
            status_code=409,
            detail="Sistema ya configurado. Usa /api/setup/regenerate para nuevos seeds.",
        )

    code = req.country_code.upper().strip()
    if code not in LATAM_COUNTRIES:
        raise HTTPException(status_code=400, detail=f"País '{code}' no soportado.")

    country = LATAM_COUNTRIES[code]
    seeds = generate_seeds()
    hashes = hash_seeds(seeds)

    _write_access(hashes)

    _SETUP_MARKER.write_text(
        json.dumps(
            {
                "country_code": code,
                "country_name": country.name,
                "configured_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    _update_config_yaml(code)

    logger.info("setup_complete country=%s", _sl(code))
    return _pdf_response(seeds, country.name, country.flag, code)


@router.post("/regenerate")
def regenerate_seeds(req: RegenerateRequest) -> Response:
    """
    Regenera seeds nuevos (invalida todos los anteriores).
    Requiere autenticación: uno de los 12 seeds actuales (seed_label + seed_value).
    """
    setup = _read_setup()
    if not setup:
        raise HTTPException(status_code=400, detail="Sistema no configurado aún.")

    if not _verify_seed(req.seed_label, req.seed_value):
        logger.warning("regenerate_auth_failed label=%s", _sl(req.seed_label))
        raise HTTPException(status_code=401, detail="Seed de autenticación inválido.")

    code = (req.country_code or setup.get("country_code", "HN")).upper().strip()
    if code not in LATAM_COUNTRIES:
        raise HTTPException(status_code=400, detail=f"País '{code}' no soportado.")

    country = LATAM_COUNTRIES[code]
    seeds = generate_seeds()
    hashes = hash_seeds(seeds)

    _write_access(hashes)

    setup["last_regenerated_at"] = datetime.now(timezone.utc).isoformat()
    _SETUP_MARKER.write_text(json.dumps(setup, indent=2) + "\n", encoding="utf-8")

    logger.warning("seeds_regenerated country=%s — previous seeds invalidated", _sl(code))
    return _pdf_response(seeds, country.name, country.flag, code)
