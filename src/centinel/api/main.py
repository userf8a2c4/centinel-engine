"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/api/main.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _env_int
  - _rules_rate_limit
  - get_connection
  - _validate_table_name
  - fetch_latest_snapshot
  - fetch_snapshot_by_hash
  - verify_hashchain
  - load_alerts_payload
  - load_summaries_payload
  - get_latest_snapshot
  - get_snapshot
  - verify_hash
  - get_alerts
  - api_health
  - api_summaries

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/api/main.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _env_int
  - _rules_rate_limit
  - get_connection
  - _validate_table_name
  - fetch_latest_snapshot
  - fetch_snapshot_by_hash
  - verify_hashchain
  - load_alerts_payload
  - load_summaries_payload
  - get_latest_snapshot
  - get_snapshot
  - verify_hash
  - get_alerts
  - api_health
  - api_summaries

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Main Module
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


import json
import logging
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
import yaml

from monitoring.health import register_healthchecks
from monitoring.strict_health import register_strict_health_endpoints
from centinel.api.middleware import install_zero_trust
from centinel.core.hashchain import compute_hash

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = Path(os.getenv("SNAPSHOTS_DB_PATH", BASE_DIR / "data" / "snapshots.db"))
ALERTS_JSON = BASE_DIR / "data" / "alerts.json"
ALERTS_LOG = BASE_DIR / "alerts.log"
RULES_PATH = BASE_DIR / "command_center" / "rules.yaml"
SUMMARY_PATH = BASE_DIR / "reports" / "summary.txt"


@asynccontextmanager
async def _lifespan(application: FastAPI):  # noqa: ARG001
    logger.warning(
        "CENTINEL_STARTUP build=%s time=%s",
        globals().get("_build_stamp", "dev"),
        datetime.now(timezone.utc).isoformat(),
    )
    if os.getenv("CENTINEL_AUTOCONNECT", "").strip() == "1":
        from .routes.swarm import auto_start as _swarm_auto_start
        await _swarm_auto_start()
    yield


app = FastAPI(title="C.E.N.T.I.N.E.L. Public API", version="0.1.0", lifespan=_lifespan)
logger = logging.getLogger(__name__)

# Mount /audit/* router for independent third-party verification.
# Read-only, no-auth endpoints intentional: see docs/architecture.md.
from .audit import router as audit_router  # noqa: E402
from .routes.setup import router as setup_router  # noqa: E402
from .routes.swarm import router as swarm_router  # noqa: E402
from .routes.election import router as election_router  # noqa: E402

app.include_router(audit_router)
app.include_router(setup_router)
app.include_router(swarm_router)
app.include_router(election_router)


def _load_cors_origins() -> list[str]:
    """Load CORS allowed origins from env var or config file.

    Priority: env var CORS_ORIGINS > config YAML > empty list (no CORS).
    Security: explicit whitelist by default; wildcard disallowed.
    """
    # Try environment variable first (runtime override)
    origins_raw = os.getenv("CORS_ORIGINS", "").strip()
    if origins_raw:
        return [o.strip() for o in origins_raw.split(",") if o.strip()]

    # Fall back to config file
    config_path = BASE_DIR / "command_center" / "advanced_security_config.yaml"
    if config_path.exists():
        try:
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            origins = cfg.get("cors_allowed_origins", [])
            if isinstance(origins, list):
                return [o.strip() for o in origins if isinstance(o, str) and o.strip()]
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("cors_config_load_failed error=%s", exc)

    # Default: CORS disabled (empty list)
    return []


origins = _load_cors_origins()
_allow_credentials = bool(origins)  # credentials only valid with explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _env_int(name: str, default: int) -> int:
    """Lee una variable de entorno como entero con fallback seguro.

    Usa `default` cuando la variable no está definida o no es válida, además de
    registrar el valor inválido para trazabilidad operativa.

    English:
        Read an environment variable as an integer with a safe fallback.

        Uses `default` when the variable is unset or invalid, and logs invalid
        values for operational traceability.
    """
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("invalid_env_int name=%s value=%s", name, raw)
        return default


def _rules_rate_limit(default: int) -> int:
    """/** Lee rate limit desde command_center/rules.yaml. / Read rate limit from command_center/rules.yaml. **/"""
    if not RULES_PATH.exists():
        return default
    try:
        payload = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return default
    if not isinstance(payload, dict):
        return default
    security = payload.get("security", {})
    if not isinstance(security, dict):
        return default
    try:
        return int(security.get("rate_limit_rpm", default))
    except (TypeError, ValueError):
        return default


rate_limit_per_minute = _env_int("API_RATE_LIMIT", _rules_rate_limit(30))
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{rate_limit_per_minute}/minute"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Zero Trust middleware — outermost layer, runs first on every request.
# (Middleware Zero Trust — capa más externa, corre primero en cada request.)
# Opt-in via config.yaml → security.zero_trust: true
install_zero_trust(app)


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Crea la tabla snapshot_index si no existe.

    English:
        Create the snapshot_index table if it does not exist.
    """
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshot_index (
            department_code TEXT NOT NULL,
            timestamp_utc TEXT NOT NULL,
            table_name TEXT NOT NULL,
            hash TEXT NOT NULL,
            previous_hash TEXT,
            tx_hash TEXT,
            ipfs_cid TEXT,
            ipfs_tx_hash TEXT,
            PRIMARY KEY (department_code, timestamp_utc)
        )
        """
    )
    connection.commit()


def get_connection() -> sqlite3.Connection:
    """Abre una conexión SQLite con row factory dict-like.

    Returns:
        sqlite3.Connection: Conexión abierta a SQLite.

    English:
        Opens a SQLite connection with dict-like rows.

    Returns:
        sqlite3.Connection: Open SQLite connection.
    """
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    _ensure_schema(connection)
    return connection


def _validate_table_name(table_name: str) -> str:
    """Asegura que el nombre de tabla tenga el formato esperado."""
    if not re.fullmatch(r"dept_[A-Za-z0-9]+_snapshots", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


def fetch_latest_snapshot(connection: sqlite3.Connection) -> dict | None:
    """Devuelve el snapshot más reciente del índice.

    Args:
        connection (sqlite3.Connection): Conexión abierta.

    Returns:
        dict | None: Snapshot más reciente o None si no existe.

    English:
        Returns the latest snapshot from the index.

    Args:
        connection (sqlite3.Connection): Open connection.

    Returns:
        dict | None: Latest snapshot or None if missing.
    """
    row = connection.execute(
        """
        SELECT department_code, timestamp_utc, table_name, hash, previous_hash, tx_hash
        FROM snapshot_index
        ORDER BY timestamp_utc DESC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    table_name = _validate_table_name(row["table_name"])
    snapshot = connection.execute(
        f"""
        SELECT canonical_json, registered_voters, total_votes, valid_votes,
               null_votes, blank_votes, candidates_json, ipfs_cid, ipfs_tx_hash
        FROM {table_name}
        WHERE hash = ?
        """,  # nosec B608 - table name validated against strict pattern.
        (row["hash"],),
    ).fetchone()
    payload = None
    if snapshot:
        try:
            payload = json.loads(snapshot["canonical_json"])
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error(
                "corrupted_canonical_json hash=%s error=%s",
                row["hash"],
                exc,
            )
    return {
        "snapshot_id": row["hash"],
        "department_code": row["department_code"],
        "timestamp_utc": row["timestamp_utc"],
        "previous_hash": row["previous_hash"],
        "tx_hash": row["tx_hash"],
        "ipfs_cid": snapshot["ipfs_cid"] if snapshot else None,
        "ipfs_tx_hash": snapshot["ipfs_tx_hash"] if snapshot else None,
        "snapshot": payload,
    }


def fetch_snapshot_by_hash(connection: sqlite3.Connection, snapshot_hash: str) -> dict | None:
    """Busca un snapshot por hash en el índice.

    Args:
        connection (sqlite3.Connection): Conexión abierta.
        snapshot_hash (str): Hash del snapshot.

    Returns:
        dict | None: Snapshot encontrado o None.

    English:
        Finds a snapshot by hash in the index.

    Args:
        connection (sqlite3.Connection): Open connection.
        snapshot_hash (str): Snapshot hash.

    Returns:
        dict | None: Snapshot payload or None.
    """
    row = connection.execute(
        """
        SELECT department_code, timestamp_utc, table_name, hash, previous_hash, tx_hash
        FROM snapshot_index
        WHERE hash = ?
        LIMIT 1
        """,
        (snapshot_hash,),
    ).fetchone()
    if not row:
        return None
    table_name = _validate_table_name(row["table_name"])
    snapshot = connection.execute(
        f"""
        SELECT canonical_json, ipfs_cid, ipfs_tx_hash
        FROM {table_name}
        WHERE hash = ?
        """,  # nosec B608 - table name validated against strict pattern.
        (snapshot_hash,),
    ).fetchone()
    payload = None
    if snapshot:
        try:
            payload = json.loads(snapshot["canonical_json"])
        except (json.JSONDecodeError, TypeError) as exc:
            _safe_hash = str(snapshot_hash).replace("\n", "\\n").replace("\r", "\\r")
            logger.error(
                "corrupted_canonical_json hash=%s error=%s",
                _safe_hash,
                type(exc).__name__,
            )
    return {
        "snapshot_id": row["hash"],
        "department_code": row["department_code"],
        "timestamp_utc": row["timestamp_utc"],
        "previous_hash": row["previous_hash"],
        "tx_hash": row["tx_hash"],
        "ipfs_cid": snapshot["ipfs_cid"] if snapshot else None,
        "ipfs_tx_hash": snapshot["ipfs_tx_hash"] if snapshot else None,
        "snapshot": payload,
    }


def verify_hashchain(connection: sqlite3.Connection, snapshot_hash: str) -> dict:
    """Verifica el hash encadenado usando JSON canónico y hash previo.

    Args:
        connection (sqlite3.Connection): Conexión abierta.
        snapshot_hash (str): Hash a verificar.

    Returns:
        dict: Resultado con campos exists y valid.

    English:
        Verifies the chained hash using canonical JSON and previous hash.

    Args:
        connection (sqlite3.Connection): Open connection.
        snapshot_hash (str): Hash to verify.

    Returns:
        dict: Result with exists and valid fields.
    """
    row = connection.execute(
        """
        SELECT table_name, hash, previous_hash
        FROM snapshot_index
        WHERE hash = ?
        LIMIT 1
        """,
        (snapshot_hash,),
    ).fetchone()
    if not row:
        return {"exists": False, "valid": False}
    table_name = _validate_table_name(row["table_name"])
    snapshot = connection.execute(
        f"""
        SELECT canonical_json
        FROM {table_name}
        WHERE hash = ?
        """,  # nosec B608 - table name validated against strict pattern.
        (snapshot_hash,),
    ).fetchone()
    if not snapshot:
        return {"exists": True, "valid": False}
    computed = compute_hash(snapshot["canonical_json"], row["previous_hash"])
    return {"exists": True, "valid": computed == snapshot_hash}


def load_alerts_payload() -> list[dict]:
    """Carga alertas desde JSON o logs.

    Returns:
        list[dict]: Alertas disponibles.

    English:
        Loads alerts from JSON or logs.

    Returns:
        list[dict]: Available alerts.
    """
    if ALERTS_JSON.exists():
        try:
            data = json.loads(ALERTS_JSON.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("corrupted_alerts_json path=%s error=%s", ALERTS_JSON, exc)
            return []
    if ALERTS_LOG.exists():
        try:
            lines = ALERTS_LOG.read_text(encoding="utf-8").splitlines()
            return [{"timestamp": "", "descripcion": line} for line in lines if line]
        except OSError:
            return []
    return []


def load_summaries_payload() -> dict:
    """/** Carga un resumen textual desde reports/summary.txt. / Load a textual summary from reports/summary.txt. **/"""
    if not SUMMARY_PATH.exists():
        return {"summary": [], "updated_at": None}
    try:
        lines = SUMMARY_PATH.read_text(encoding="utf-8").splitlines()
        return {
            "summary": [line for line in lines if line.strip()],
            "updated_at": SUMMARY_PATH.stat().st_mtime,
        }
    except OSError:
        return {"summary": [], "updated_at": None}


@app.get("/snapshots/latest")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def get_latest_snapshot(request: Request) -> dict:
    """Endpoint que devuelve el snapshot más reciente.

    Returns:
        dict: Snapshot más reciente con metadatos.

    English:
        Endpoint returning the latest snapshot.

    Returns:
        dict: Latest snapshot with metadata.
    """
    connection = get_connection()
    try:
        payload = fetch_latest_snapshot(connection)
    finally:
        connection.close()
    if not payload:
        raise HTTPException(status_code=404, detail="No snapshots available.")
    return payload


_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@app.get("/snapshots/{snapshot_id}")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def get_snapshot(snapshot_id: str, request: Request) -> dict:
    """Endpoint que devuelve un snapshot por hash.

    Args:
        snapshot_id (str): SHA-256 hash del snapshot (64 hex chars).

    Returns:
        dict: Snapshot encontrado.

    English:
        Endpoint returning a snapshot by hash.

    Args:
        snapshot_id (str): Snapshot SHA-256 hash (64 hex chars).

    Returns:
        dict: Snapshot payload.
    """
    if not _HASH_RE.match(snapshot_id):
        raise HTTPException(status_code=400, detail="Invalid snapshot ID format.")
    connection = get_connection()
    try:
        payload = fetch_snapshot_by_hash(connection, snapshot_id)
    finally:
        connection.close()
    if not payload:
        raise HTTPException(status_code=404, detail="Snapshot not found.")
    return payload


@app.get("/hashchain/verify")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def verify_hash(request: Request, hash_value: str = Query(..., alias="hash")) -> dict:
    """Endpoint de verificación de hash encadenado.

    Args:
        hash_value (str): Hash a verificar.

    Returns:
        dict: Resultado de verificación.

    English:
        Endpoint for chained hash verification.

    Args:
        hash_value (str): Hash to verify.

    Returns:
        dict: Verification result.
    """
    connection = get_connection()
    try:
        result = verify_hashchain(connection, hash_value)
    finally:
        connection.close()
    return result


@app.get("/alerts")
def get_alerts() -> list[dict]:
    """Endpoint que devuelve alertas disponibles.

    Returns:
        list[dict]: Alertas disponibles.

    English:
        Endpoint returning available alerts.

    Returns:
        list[dict]: Available alerts.
    """
    return load_alerts_payload()


@app.get("/api/dashboard-data")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def dashboard_data(request: Request) -> dict:
    """Agrega datos de snapshots, alertas y estado en formato ElectionData.

    English:
        Aggregates snapshot, alert and status data into ElectionData format
        consumed by the React dashboard.
    """
    connection = get_connection()
    try:
        dept_status = _department_status(connection)

        # Build per-department data from latest snapshots.
        departments: dict[str, dict] = {}
        national_votes = 0
        national_actas = 0
        national_actas_total = 0
        all_candidates_agg: dict[str, dict] = {}
        alert_state = "normal"
        alert_department = None

        _, iso_to_name, _ = _load_country_maps()
        for ds in dept_status:
            dept_code = ds["department"]
            # Map internal name to ISO code used by frontend (e.g. atlantida -> HN-AT).
            iso_code = _dept_to_iso(dept_code)
            dept_name = iso_to_name.get(iso_code, dept_code.replace("_", " ").title())

            row = connection.execute(
                """
                SELECT table_name, hash, previous_hash, timestamp_utc
                FROM snapshot_index
                WHERE department_code = ?
                ORDER BY timestamp_utc DESC
                LIMIT 1
                """,
                (dept_code,),
            ).fetchone()

            candidates: list[dict] = []
            total_votes = 0
            registered_voters = 0
            actas_escrutadas = 1 if row else 0
            actas_total = 1

            if row:
                try:
                    tbl = _validate_table_name(row["table_name"])
                    snap = connection.execute(
                        f"""
                        SELECT registered_voters, total_votes, valid_votes,
                               null_votes, blank_votes, candidates_json
                        FROM {tbl}
                        WHERE hash = ?
                        """,  # nosec B608
                        (row["hash"],),
                    ).fetchone()
                    if snap:
                        total_votes = snap["total_votes"] or 0
                        registered_voters = snap["registered_voters"] or 0
                        try:
                            candidates = json.loads(snap["candidates_json"]) if snap["candidates_json"] else []
                        except (json.JSONDecodeError, TypeError):
                            candidates = []
                except (ValueError, sqlite3.OperationalError):
                    pass

            hash_valid = ds["status"] != "hash_broken"
            rules_broken = ds["status"] == "rule_broken"

            if ds["status"] == "hash_broken":
                alert_state = "hash_broken"
                alert_department = dept_name
            elif ds["status"] == "rule_broken" and alert_state == "normal":
                alert_state = "anomaly"
                alert_department = dept_name

            turnout = round((total_votes / registered_voters * 100), 1) if registered_voters else 0.0

            # Normalize candidates into frontend format.
            fe_candidates = _format_candidates(candidates, total_votes)

            departments[iso_code] = {
                "code": iso_code,
                "name": dept_name,
                "actasTotal": actas_total,
                "actasEscrutadas": actas_escrutadas,
                "totalVotes": total_votes,
                "integrityPercent": 100.0 if hash_valid and not rules_broken else 91.4,
                "turnoutPercent": turnout,
                "hashValid": hash_valid,
                "rulesBroken": rules_broken,
                "candidates": fe_candidates,
            }

            national_votes += total_votes
            national_actas += actas_escrutadas
            national_actas_total += actas_total

            # Aggregate candidate totals across departments.
            for c in fe_candidates:
                key = c["name"]
                if key not in all_candidates_agg:
                    all_candidates_agg[key] = {**c, "votes": 0}
                all_candidates_agg[key]["votes"] += c["votes"]

        # National JSON is the authoritative source for national totals.
        # Fall back to summing department snapshots if not available.
        nat_json = _load_national_snapshot()

        if nat_json:
            national_section = {
                "actasTotal": nat_json["actasTotal"],
                "actasEscrutadas": nat_json["actasDivulgadas"],
                "actasCorrectas": nat_json["actasCorrectas"],
                "actasInconsistentes": nat_json["actasInconsistentes"],
                "totalVotes": nat_json["votosValidos"],
                "votosNulos": nat_json["votosNulos"],
                "votosBlancos": nat_json["votosBlancos"],
                "integrityPercent": 97.4 if alert_state == "normal" else 91.4,
                "turnoutPercent": 0.0,
                "candidates": nat_json["candidates"],
                "source": "national_json",
                "fileTimestamp": nat_json.get("file_timestamp"),
            }
        else:
            nat_candidates = list(all_candidates_agg.values())
            for c in nat_candidates:
                c["percentage"] = round(c["votes"] / national_votes * 100, 1) if national_votes else 0.0
            national_section = {
                "actasTotal": national_actas_total,
                "actasEscrutadas": national_actas,
                "totalVotes": national_votes,
                "integrityPercent": 97.4 if alert_state == "normal" else 91.4,
                "turnoutPercent": 0.0,
                "candidates": nat_candidates,
                "source": "dept_aggregation",
            }

        return {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "source": "CENTINEL-API",
            "alertState": alert_state,
            "alertDepartment": alert_department,
            "national": national_section,
            "departments": departments,
        }
    finally:
        connection.close()


# ── Country-aware dept maps (lazy, built from CountryPreset) ──────────────────

_SETUP_MARKER_PATH = BASE_DIR / ".centinel-setup.json"

_cached_country_code: str | None = None
_cached_dept_to_iso: dict[str, str] | None = None
_cached_iso_to_name: dict[str, str] | None = None
_cached_departments: list[str] | None = None


def _load_country_maps() -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Load dept maps from the configured country, defaulting to HN."""
    global _cached_country_code, _cached_dept_to_iso, _cached_iso_to_name, _cached_departments

    try:
        setup = json.loads(_SETUP_MARKER_PATH.read_text()) if _SETUP_MARKER_PATH.exists() else {}
        code = setup.get("country_code", "HN").upper()
    except Exception:
        code = "HN"

    if code == _cached_country_code and _cached_dept_to_iso is not None:
        return _cached_dept_to_iso, _cached_iso_to_name, _cached_departments

    from centinel.countries import LATAM_COUNTRIES
    preset = LATAM_COUNTRIES.get(code, LATAM_COUNTRIES["HN"])
    d2i, i2n, slugs = preset.build_dept_maps()

    _cached_country_code = code
    _cached_dept_to_iso = d2i
    _cached_iso_to_name = i2n
    _cached_departments = slugs
    return d2i, i2n, slugs


def _dept_to_iso(dept_code: str) -> str:
    d2i, _, _ = _load_country_maps()
    return d2i.get(dept_code, dept_code)


# ── National JSON parser (HN schema) ─────────────────────────────────────────

_DATA_DIR = BASE_DIR / "data"
_FIXTURE_DIR = BASE_DIR / "tests" / "fixtures" / "hnd_2025"


def _parse_hn_int(value: str | int | None) -> int:
    """Parse CNE integer strings like '1,027,090' → 1027090."""
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


def _find_latest_national_json() -> Path | None:
    """Find the most recently timestamped national JSON file."""
    import re
    pattern = re.compile(r"HN\.PRESIDENTE\.00-TODOS\.000-TODOS .+\.json$")
    candidates: list[tuple[str, Path]] = []

    for search_dir in (_DATA_DIR, _FIXTURE_DIR):
        if not search_dir.exists():
            continue
        for p in search_dir.iterdir():
            if pattern.match(p.name):
                candidates.append((p.name, p))

    if not candidates:
        return None
    # Filename contains timestamp; lexicographic sort gives chronological order
    candidates.sort(key=lambda t: t[0])
    return candidates[-1][1]


def _load_national_snapshot() -> dict | None:
    """Parse the latest national CNE JSON into dashboard format."""
    path = _find_latest_national_json()
    if not path:
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    resultados = raw.get("resultados", [])
    stats = raw.get("estadisticas", {})
    actas_total = _parse_hn_int(stats.get("totalizacion_actas", {}).get("actas_totales"))
    actas_divulgadas = _parse_hn_int(stats.get("totalizacion_actas", {}).get("actas_divulgadas"))
    votos_validos = _parse_hn_int(stats.get("distribucion_votos", {}).get("validos"))
    votos_nulos = _parse_hn_int(stats.get("distribucion_votos", {}).get("nulos"))
    votos_blancos = _parse_hn_int(stats.get("distribucion_votos", {}).get("blancos"))
    actas_correctas = _parse_hn_int(stats.get("estado_actas_divulgadas", {}).get("actas_correctas"))
    actas_inconsistentes = _parse_hn_int(stats.get("estado_actas_divulgadas", {}).get("actas_inconsistentes"))
    total_emitidos = votos_validos + votos_nulos + votos_blancos

    candidates = []
    for r in resultados:
        votes = _parse_hn_int(r.get("votos"))
        try:
            pct = float(r.get("porcentaje", "0"))
        except (ValueError, TypeError):
            pct = round(votes / votos_validos * 100, 2) if votos_validos else 0.0
        candidates.append({
            "name": (r.get("candidato") or "").title(),
            "party": r.get("partido", ""),
            "votes": votes,
            "percentage": pct,
            "partyColor": "#6b7280",
            "victoryProbability": 0,
            "health": "normal",
            "analysisText": "",
            "forensics": {"loadSpikes": 0, "sigma": 0, "flowRate": 0,
                          "benfordDeviation": 0, "lastDelta": 0, "trendDirection": "stable"},
        })

    # Extract timestamp from filename  e.g. "2025-12-09 15_01_45"
    import re
    ts_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}_\d{2}_\d{2})", path.name)
    file_ts = ts_match.group(1).replace("_", ":").replace(" ", "T") + "Z" if ts_match else None

    return {
        "source_file": path.name,
        "file_timestamp": file_ts,
        "actasTotal": actas_total,
        "actasDivulgadas": actas_divulgadas,
        "actasCorrectas": actas_correctas,
        "actasInconsistentes": actas_inconsistentes,
        "votosValidos": votos_validos,
        "votosNulos": votos_nulos,
        "votosBlancos": votos_blancos,
        "totalEmitidos": total_emitidos,
        "candidates": candidates,
    }


def _format_candidates(raw: list, total_votes: int) -> list[dict]:
    """Normaliza candidatos del snapshot al formato del frontend."""
    result = []
    for c in raw:
        if isinstance(c, dict):
            votes = c.get("votes", c.get("votos", 0)) or 0
            pct = round(votes / total_votes * 100, 1) if total_votes else 0.0
            result.append(
                {
                    "name": c.get("name", c.get("nombre", "Desconocido")),
                    "party": c.get("party", c.get("partido", "")),
                    "partyColor": c.get("partyColor", c.get("color", "#6b7280")),
                    "votes": votes,
                    "percentage": pct,
                    "victoryProbability": c.get("victoryProbability", 0),
                    "health": c.get("health", "normal"),
                    "analysisText": c.get("analysisText", ""),
                    "forensics": c.get(
                        "forensics",
                        {
                            "loadSpikes": 0,
                            "sigma": 0,
                            "flowRate": 0,
                            "benfordDeviation": 0,
                            "lastDelta": 0,
                            "trendDirection": "stable",
                        },
                    ),
                }
            )
    return result


@app.get("/api/health")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def api_health(request: Request) -> dict:
    """/** Endpoint de salud protegido por rate limiting. / Health endpoint protected by rate limiting. **/"""
    return {"status": "ok"}


@app.get("/api/summaries")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def api_summaries(request: Request) -> dict:
    """/** Endpoint de summaries protegido por rate limiting. / Summaries endpoint protected by rate limiting. **/"""
    return load_summaries_payload()


def _get_departments() -> list[str]:
    _, _, slugs = _load_country_maps()
    return slugs


def _department_status(connection: sqlite3.Connection) -> list[dict]:
    """Calcula el estado de cada departamento basado en alertas y hashes.

    Retorna una lista con el estado de cada departamento:
    - 'ok': sin alertas (blanco hueso)
    - 'rule_broken': alguna regla del sistema se rompió (amarillo)
    - 'hash_broken': un hash se ha roto (rojo)
    """
    alerts = load_alerts_payload()
    alert_depts: dict[str, set[str]] = {}
    for alert in alerts:
        dept = (alert.get("department_code") or alert.get("departamento") or "").strip().lower().replace(" ", "_")
        severity = (alert.get("severity") or alert.get("nivel") or "warning").lower()
        alert_depts.setdefault(dept, set()).add(severity)

    results = []
    for dept in _get_departments():
        # Check hash integrity for latest snapshot of this department
        hash_ok = True
        row = connection.execute(
            """
            SELECT table_name, hash, previous_hash
            FROM snapshot_index
            WHERE department_code = ?
            ORDER BY timestamp_utc DESC
            LIMIT 1
            """,
            (dept,),
        ).fetchone()
        if row:
            try:
                table_name = _validate_table_name(row["table_name"])
                snap = connection.execute(
                    f"SELECT canonical_json FROM {table_name} WHERE hash = ?",  # nosec B608
                    (row["hash"],),
                ).fetchone()
                if snap:
                    computed = compute_hash(snap["canonical_json"], row["previous_hash"])
                    if computed != row["hash"]:
                        hash_ok = False
            except (ValueError, sqlite3.OperationalError):
                pass

        severities = alert_depts.get(dept, set())
        if not hash_ok:
            status = "hash_broken"
        elif severities:
            status = "rule_broken"
        else:
            status = "ok"

        results.append(
            {
                "department": dept,
                "status": status,
                "has_data": row is not None,
                "alert_count": len(alert_depts.get(dept, set())),
            }
        )
    return results


@app.get("/api/departments/status")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def departments_status(request: Request) -> list[dict]:
    """Estado de los 18 departamentos para el mapa de calor ciudadano."""
    connection = get_connection()
    try:
        return _department_status(connection)
    finally:
        connection.close()


@app.get("/api/national-snapshot")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def national_snapshot(request: Request) -> dict:
    """Retorna el snapshot nacional más reciente del CNE (JSON de nivel nacional).

    Busca el archivo JSON más reciente en data/ y tests/fixtures/hnd_2025/,
    lo parsea y retorna en formato normalizado para el dashboard.
    Retorna 404 si no hay ningún archivo disponible.
    """
    snap = _load_national_snapshot()
    if snap is None:
        raise HTTPException(status_code=404, detail="No national snapshot available yet.")
    return snap


DASHBOARD_BUILD_DIR = BASE_DIR / "static" / "dashboard"
DASHBOARD_HTML_PATH = BASE_DIR / "templates" / "dashboard.html"
SETUP_DIR = BASE_DIR / "web" / "setup"


@app.get("/setup/", response_class=HTMLResponse)
@app.get("/setup", response_class=HTMLResponse)
def setup_page():
    """Sirve el wizard de configuración inicial."""
    setup_html = SETUP_DIR / "index.html"
    if setup_html.exists():
        return FileResponse(setup_html, media_type="text/html")
    raise HTTPException(status_code=404, detail="Setup wizard not found.")


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Sirve el dashboard desde templates/dashboard.html."""
    if DASHBOARD_HTML_PATH.exists():
        return FileResponse(DASHBOARD_HTML_PATH, media_type="text/html")
    # Fallback al React build solo si dashboard.html no existe.
    react_index = DASHBOARD_BUILD_DIR / "index.html"
    if react_index.exists():
        return FileResponse(react_index, media_type="text/html")
    raise HTTPException(status_code=500, detail="Dashboard template not found.")


# Mount static directories. Must be after explicit routes to avoid shadowing API endpoints.
if DASHBOARD_BUILD_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DASHBOARD_BUILD_DIR / "assets"), name="dashboard-assets")
if SETUP_DIR.exists():
    app.mount("/setup/static", StaticFiles(directory=SETUP_DIR), name="setup-static")

_PEERS_DIR = BASE_DIR / "web" / "peers"
if _PEERS_DIR.exists():
    app.mount("/peers", StaticFiles(directory=_PEERS_DIR), name="peers-static")


# EN: Log build info at startup for deploy verification.
# ES: Registrar info de build al iniciar para verificar deploys.
_build_info_path = BASE_DIR / "BUILD_INFO"
_build_stamp = _build_info_path.read_text().strip() if _build_info_path.exists() else "dev"


@app.get("/live")
async def _live_check():
    """EN: Returns build info — use to verify deploy version. / ES: Retorna info de build — usar para verificar versión desplegada."""
    return {
        "status": "ok",
        "build": _build_stamp,
        "started": datetime.now(timezone.utc).isoformat(),
    }


register_healthchecks(app)
register_strict_health_endpoints(app)
