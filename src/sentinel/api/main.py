"""API pública para snapshots, alertas y verificación de hashchain.

English:
    Public API for snapshots, alerts, and hashchain verification.
"""

import json
import logging
import os
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
import yaml

from monitoring.health import register_healthchecks
from monitoring.strict_health import register_strict_health_endpoints
from sentinel.core.hashchain import compute_hash

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("SNAPSHOTS_DB_PATH", BASE_DIR / "data" / "snapshots.db"))
ALERTS_JSON = BASE_DIR / "data" / "alerts.json"
ALERTS_LOG = BASE_DIR / "alerts.log"
RULES_PATH = BASE_DIR / "command_center" / "rules.yaml"
SUMMARY_PATH = BASE_DIR / "reports" / "summary.txt"

app = FastAPI(title="C.E.N.T.I.N.E.L. Public API", version="0.1.0")
logger = logging.getLogger(__name__)

origins_raw = os.getenv("CORS_ORIGINS", "*")
origins = (
    ["*"] if origins_raw.strip() == "*" else [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


rate_limit_per_minute = _env_int("API_RATE_LIMIT", _rules_rate_limit(10))
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{rate_limit_per_minute}/minute"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


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
    row = connection.execute("""
        SELECT department_code, timestamp_utc, table_name, hash, previous_hash, tx_hash
        FROM snapshot_index
        ORDER BY timestamp_utc DESC
        LIMIT 1
        """).fetchone()
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
    payload = json.loads(snapshot["canonical_json"]) if snapshot else None
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
    payload = json.loads(snapshot["canonical_json"]) if snapshot else None
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
        except (OSError, json.JSONDecodeError):
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
def get_latest_snapshot() -> dict:
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


@app.get("/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: str) -> dict:
    """Endpoint que devuelve un snapshot por hash.

    Args:
        snapshot_id (str): Hash del snapshot.

    Returns:
        dict: Snapshot encontrado.

    English:
        Endpoint returning a snapshot by hash.

    Args:
        snapshot_id (str): Snapshot hash.

    Returns:
        dict: Snapshot payload.
    """
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
def verify_hash(hash_value: str = Query(..., alias="hash")) -> dict:
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


@app.get("/api/health")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def api_health() -> dict:
    """/** Endpoint de salud protegido por rate limiting. / Health endpoint protected by rate limiting. **/"""
    return {"status": "ok"}


@app.get("/api/summaries")
@limiter.limit(f"{rate_limit_per_minute}/minute")
def api_summaries() -> dict:
    """/** Endpoint de summaries protegido por rate limiting. / Summaries endpoint protected by rate limiting. **/"""
    return load_summaries_payload()


register_healthchecks(app)
register_strict_health_endpoints(app)
