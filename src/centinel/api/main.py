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
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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

app = FastAPI(title="C.E.N.T.I.N.E.L. Public API", version="0.1.0")
logger = logging.getLogger(__name__)

# Security: default to no CORS origins instead of wildcard.
# Seguridad: por defecto sin orígenes CORS en lugar de wildcard.
origins_raw = os.getenv("CORS_ORIGINS", "")
origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()] if origins_raw.strip() else []
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


rate_limit_per_minute = _env_int("API_RATE_LIMIT", _rules_rate_limit(10))
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
            logger.error(
                "corrupted_canonical_json hash=%s error=%s",
                snapshot_hash,
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


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>C.E.N.T.I.N.E.L. Dashboard</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡️</text></svg>">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:#0A1428;color:#E0E6ED;min-height:100vh;display:flex;flex-direction:column}
.header{background:linear-gradient(135deg,#0D1B2A 0%,#1B2838 100%);border-bottom:2px solid #00A3E0;padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.5rem}
.header h1{font-size:1.4rem;letter-spacing:2px;color:#00A3E0}
.header-right{display:flex;align-items:center;gap:.75rem}
.badge{background:#00C853;color:#0A1428;padding:.25rem .75rem;border-radius:4px;font-size:.75rem;font-weight:700}
#conn-indicator{font-size:.7rem;color:#7A8BA3;display:flex;align-items:center;gap:4px}
#conn-dot{width:6px;height:6px;border-radius:50%;background:#00C853;transition:background .3s}
#conn-dot.off{background:#FF5252}
.container{max-width:1200px;margin:0 auto;padding:1.5rem;width:100%;flex:1}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;margin-bottom:1.5rem}
.card{background:#111D2E;border:1px solid #1E3048;border-radius:8px;padding:1.25rem;transition:border-color .2s}
.card:hover{border-color:#00A3E055}
.card h3{font-size:.7rem;text-transform:uppercase;letter-spacing:1px;color:#7A8BA3;margin-bottom:.5rem}
.card .value{font-size:1.4rem;font-weight:700;color:#00A3E0;word-break:break-word}
.card .value.ok{color:#00C853}
.card .value.warn{color:#FF9800}
.card .value.err{color:#FF5252}
.section{background:#111D2E;border:1px solid #1E3048;border-radius:8px;padding:1.25rem;margin-bottom:1rem}
.section h2{font-size:.95rem;color:#00A3E0;margin-bottom:.75rem;border-bottom:1px solid #1E3048;padding-bottom:.5rem;display:flex;align-items:center;justify-content:space-between}
.section h2 .updated{font-size:.65rem;color:#4A5568;font-weight:400}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th{text-align:left;color:#7A8BA3;padding:.5rem;border-bottom:1px solid #1E3048;font-weight:600}
td{padding:.5rem;border-bottom:1px solid #1E304833;word-break:break-all}
.mono{font-family:'SF Mono','Cascadia Code',monospace;font-size:.78rem;color:#8FAABE}
.alert-item{padding:.75rem;border-left:3px solid #FF9800;margin-bottom:.5rem;background:#1a1a2e;border-radius:0 4px 4px 0;font-size:.85rem}
.alert-item.critical{border-left-color:#FF5252}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #1E3048;border-top-color:#00A3E0;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.status-dot.green{background:#00C853}
.status-dot.red{background:#FF5252}
.footer{text-align:center;padding:1.5rem;color:#4A5568;font-size:.7rem;border-top:1px solid #1E3048}
.empty{color:#4A5568;font-style:italic;font-size:.85rem}
@media(max-width:600px){
  .header{padding:.75rem 1rem}
  .header h1{font-size:1.1rem}
  .container{padding:1rem}
  .cards{grid-template-columns:1fr 1fr}
  .card .value{font-size:1.1rem}
  td,th{padding:.35rem;font-size:.78rem}
}
@media(max-width:400px){
  .cards{grid-template-columns:1fr}
}
</style>
</head>
<body>
<div class="header">
  <h1>C.E.N.T.I.N.E.L.</h1>
  <div class="header-right">
    <span id="conn-indicator"><span id="conn-dot"></span><span id="conn-text">Conectado</span></span>
    <span class="badge">OBSERVADOR NEUTRAL</span>
  </div>
</div>
<div class="container">
  <div class="cards">
    <div class="card"><h3>Estado API</h3><div id="api-status" class="value"><span class="spinner"></span></div></div>
    <div class="card"><h3>&Uacute;ltimo Snapshot</h3><div id="snapshot-ts" class="value"><span class="spinner"></span></div></div>
    <div class="card"><h3>Departamento</h3><div id="snapshot-dept" class="value"><span class="spinner"></span></div></div>
    <div class="card"><h3>Alertas Activas</h3><div id="alert-count" class="value"><span class="spinner"></span></div></div>
  </div>
  <div class="section">
    <h2>Snapshot M&aacute;s Reciente <span class="updated" id="last-update"></span></h2>
    <table>
      <thead><tr><th>Campo</th><th>Valor</th></tr></thead>
      <tbody id="snapshot-table"><tr><td colspan="2"><span class="spinner"></span> Cargando...</td></tr></tbody>
    </table>
  </div>
  <div class="section">
    <h2>Alertas</h2>
    <div id="alerts-list"><span class="spinner"></span> Cargando...</div>
  </div>
  <div class="section">
    <h2>Resumen</h2>
    <div id="summary-content"><span class="spinner"></span> Cargando...</div>
  </div>
</div>
<div class="footer">C.E.N.T.I.N.E.L. Engine &mdash; Auditor&iacute;a Electoral Transparente &mdash; <a href="/docs" style="color:#00A3E0;text-decoration:none">API Docs</a></div>
<script>
function esc(s){if(!s)return'\\u2014';const d=document.createElement('div');d.textContent=String(s);return d.innerHTML}
async function f(url){try{const r=await fetch(url);if(!r.ok)throw r.status;return await r.json()}catch(e){return null}}
let ok=true;
async function load(){
  const [health,snap,alerts,summaries]=await Promise.all([
    f('/api/health'),f('/snapshots/latest'),f('/alerts'),f('/api/summaries')
  ]);
  const $=id=>document.getElementById(id);
  const now=new Date().toLocaleTimeString('es-HN',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  ok=!!(health&&health.status==='ok');
  $('conn-dot').className=ok?'':'off';
  $('conn-text').textContent=ok?'Conectado':'Desconectado';
  $('last-update').textContent=ok?'Actualizado: '+now:'';
  if(ok){$('api-status').className='value ok';$('api-status').innerHTML='<span class="status-dot green"></span>Operativo'}
  else{$('api-status').className='value err';$('api-status').innerHTML='<span class="status-dot red"></span>Error'}
  if(snap){
    $('snapshot-ts').textContent=snap.timestamp_utc||'\\u2014';
    $('snapshot-dept').textContent=snap.department_code||'\\u2014';
    let rows='';
    const fields=[['Hash',snap.snapshot_id],['Departamento',snap.department_code],['Timestamp UTC',snap.timestamp_utc],['Hash Previo',snap.previous_hash],['TX Hash',snap.tx_hash],['IPFS CID',snap.ipfs_cid]];
    fields.forEach(([k,v])=>{rows+='<tr><td>'+esc(k)+'</td><td class="mono">'+esc(v)+'</td></tr>'});
    $('snapshot-table').innerHTML=rows;
  }else{
    $('snapshot-ts').textContent='\\u2014';$('snapshot-dept').textContent='\\u2014';
    $('snapshot-table').innerHTML='<tr><td colspan="2" class="empty">Sin snapshots disponibles</td></tr>';
  }
  if(alerts&&alerts.length>0){
    $('alert-count').className='value warn';$('alert-count').textContent=alerts.length;
    $('alerts-list').innerHTML=alerts.slice(0,20).map(a=>{
      const txt=esc(a.descripcion||a.description||JSON.stringify(a));
      const cls=(a.severity==='critical'||a.nivel==='critico')?'alert-item critical':'alert-item';
      return '<div class="'+cls+'">'+txt+'</div>';
    }).join('');
  }else{$('alert-count').className='value ok';$('alert-count').textContent='0';$('alerts-list').innerHTML='<span class="empty">Sin alertas activas.</span>'}
  if(summaries&&summaries.summary&&summaries.summary.length>0){
    $('summary-content').innerHTML=summaries.summary.map(l=>'<p style="margin-bottom:.5rem">'+esc(l)+'</p>').join('');
  }else{$('summary-content').innerHTML='<span class="empty">Sin resumen disponible.</span>'}
}
load();setInterval(load,30000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


register_healthchecks(app)
register_strict_health_endpoints(app)
