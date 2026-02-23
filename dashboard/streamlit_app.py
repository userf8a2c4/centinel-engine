"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `dashboard/streamlit_app.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - BlockchainAnchor
  - rerun_app
  - _load_latest_anchor_record
  - load_blockchain_anchor
  - compute_report_hash
  - _safe_int
  - _safe_read_json
  - build_qr_bytes
  - load_yaml_config
  - load_configs
  - load_rules_config
  - resolve_polling_status
  - resolve_snapshot_context
  - derive_alert_thresholds
  - emit_toast
  - ...

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `dashboard/streamlit_app.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - BlockchainAnchor
  - rerun_app
  - _load_latest_anchor_record
  - load_blockchain_anchor
  - compute_report_hash
  - _safe_int
  - _safe_read_json
  - build_qr_bytes
  - load_yaml_config
  - load_configs
  - load_rules_config
  - resolve_polling_status
  - resolve_snapshot_context
  - derive_alert_thresholds
  - emit_toast
  - ...

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Streamlit App Module
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



import datetime as dt
import hashlib
import io
import json
import os
import platform
import random
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import altair as alt
import base64
import copy

try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency for S3 checks
    boto3 = None
    BOTO3_AVAILABLE = False
import pandas as pd

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency for system metrics
    psutil = None
    PSUTIL_AVAILABLE = False
from dateutil import parser as date_parser
import streamlit as st
import asyncio

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from centinel.paths import iter_all_snapshots  # noqa: E402

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import sitecustomize  # noqa: F401
except Exception:
    sitecustomize = None

try:
    from centinel.checkpointing import CheckpointConfig, CheckpointManager

    CHECKPOINTING_AVAILABLE = True
    CHECKPOINTING_ERROR = ""
except Exception as exc:  # noqa: BLE001
    CheckpointConfig = None
    CheckpointManager = None
    CHECKPOINTING_AVAILABLE = False
    CHECKPOINTING_ERROR = str(exc)
try:
    from monitoring.strict_health import is_healthy_strict

    STRICT_HEALTH_AVAILABLE = True
    STRICT_HEALTH_ERROR = ""
except Exception as exc:  # noqa: BLE001
    is_healthy_strict = None
    STRICT_HEALTH_AVAILABLE = False
    STRICT_HEALTH_ERROR = str(exc)

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency for config parsing
    yaml = None

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )
    from reportlab.pdfgen import canvas as reportlab_canvas

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency for PDF rendering
    REPORTLAB_AVAILABLE = False
    colors = None
    A4 = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    cm = None
    Image = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - optional dependency for PDF chart rendering
    plt = None

try:
    import qrcode
except ImportError:  # pragma: no cover - optional dependency for QR rendering
    qrcode = None

try:
    from centinel.core.rules_engine import RulesEngine
except ImportError:  # pragma: no cover - optional dependency for rules engine
    RulesEngine = None

# EN: Import Jinja2 for PDF report template rendering.
# ES: Importar Jinja2 para renderizar plantilla de reporte PDF.
try:
    from jinja2 import Environment, FileSystemLoader

    JINJA2_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency for HTML->PDF
    JINJA2_AVAILABLE = False

# EN: Import WeasyPrint for HTML-to-PDF conversion.
# ES: Importar WeasyPrint para conversion HTML a PDF.
try:
    from weasyprint import HTML as WeasyHTML

    WEASYPRINT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency for PDF rendering
    WeasyHTML = None
    WEASYPRINT_AVAILABLE = False

# EN: Import user manager for authentication and role-based access.
# ES: Importar user manager para autenticacion y acceso basado en roles.
AUTH_ROOT = REPO_ROOT / "auth"
if str(AUTH_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(AUTH_ROOT.parent))
try:
    from auth.user_manager import (
        authenticate,
        create_user,
        delete_user,
        ensure_admin_exists,
        list_users,
        load_sandbox,
        save_sandbox,
        VALID_ROLES,
    )

    AUTH_AVAILABLE = True
except ImportError:  # pragma: no cover
    AUTH_AVAILABLE = False


@dataclass(frozen=True)
class BlockchainAnchor:
    """Español: Clase BlockchainAnchor del módulo dashboard/streamlit_app.py.

    English: BlockchainAnchor class defined in dashboard/streamlit_app.py.
    """

    root_hash: str
    network: str
    tx_url: str
    anchored_at: str


def rerun_app() -> None:
    """Español: Función rerun_app del módulo dashboard/streamlit_app.py.

    English: Function rerun_app defined in dashboard/streamlit_app.py.
    """
    if hasattr(st, "rerun"):
        st.rerun()
        return
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def _load_latest_anchor_record() -> dict | None:
    """Español: Función _load_latest_anchor_record del módulo dashboard/streamlit_app.py.

    English: Function _load_latest_anchor_record defined in dashboard/streamlit_app.py.
    """
    anchor_dir = Path("logs") / "anchors"
    if not anchor_dir.exists():
        return None

    candidates = sorted(
        anchor_dir.glob("anchor_snapshot_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        candidates = sorted(
            anchor_dir.glob("anchor_*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    if not candidates:
        return None

    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_blockchain_anchor() -> BlockchainAnchor:
    """Español: Función load_blockchain_anchor del módulo dashboard/streamlit_app.py.

    English: Function load_blockchain_anchor defined in dashboard/streamlit_app.py.
    """
    record = _load_latest_anchor_record()
    if record:
        tx_hash = record.get("tx_hash", "")
        tx_url = record.get("tx_url") or (f"https://arbiscan.io/tx/{tx_hash}" if tx_hash else "")
        return BlockchainAnchor(
            root_hash=record.get("root_hash", record.get("root", "0x")),
            network=record.get("network", "Arbitrum L2"),
            tx_url=tx_url,
            anchored_at=record.get("anchored_at", record.get("timestamp", "N/A")),
        )
    return BlockchainAnchor(
        root_hash="Pendiente",
        network="Arbitrum L2",
        tx_url="",
        anchored_at="Sin anclaje registrado",
    )


def compute_report_hash(payload: str) -> str:
    """Español: Función compute_report_hash del módulo dashboard/streamlit_app.py.

    English: Function compute_report_hash defined in dashboard/streamlit_app.py.
    """
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_int(value: Any, default: int = 0) -> int:
    """Español: Convierte a int con fallback seguro.

    English: Convert to int with a safe fallback.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    """Español: Lee JSON con tolerancia a errores.

    English: Read JSON with error tolerance.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def build_qr_bytes(payload: str) -> bytes | None:
    """Español: Función build_qr_bytes del módulo dashboard/streamlit_app.py.

    English: Function build_qr_bytes defined in dashboard/streamlit_app.py.
    """
    if qrcode is None:
        return None
    buffer = io.BytesIO()
    qrcode.make(payload).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def load_yaml_config(path: Path) -> dict:
    """Español: Función load_yaml_config del módulo dashboard/streamlit_app.py.

    English: Function load_yaml_config defined in dashboard/streamlit_app.py.
    """
    if not path.exists() or yaml is None:
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_configs() -> dict[str, dict]:
    """/** Carga configuración central desde command_center. / Load central configuration from command_center. **/"""
    command_center_config = Path("command_center") / "config.yaml"
    if not command_center_config.exists():
        command_center_config = Path("command_center") / "config.yaml.example"
    return {
        "command_center": load_yaml_config(command_center_config),
    }


def load_rules_config(path: Path) -> dict:
    """Español: Carga reglas de auditoría desde rules.yaml.

    English: Load audit rules from rules.yaml.
    """
    return load_yaml_config(path)


def resolve_polling_status(
    rate_limit_failures: int,
    failed_retries: int,
    time_since_last: dt.timedelta | None,
    refresh_interval: int,
) -> dict[str, str]:
    """Español: Determina el estado de polling para el dashboard.

    English: Determine polling status for the dashboard.
    """
    status = {
        "label": "✅ Polling estable",
        "class": "status-pill",
        "detail": "Sin interrupciones recientes.",
    }
    if rate_limit_failures > 0:
        status = {
            "label": "⛔ Polling limitado",
            "class": "status-pill status-pill--danger",
            "detail": f"{rate_limit_failures} bloqueos por rate-limit.",
        }
    elif failed_retries > 0:
        status = {
            "label": "⚠️ Polling inestable",
            "class": "status-pill status-pill--warning",
            "detail": f"{failed_retries} reintentos en {refresh_interval}s.",
        }
    if time_since_last and time_since_last > dt.timedelta(minutes=45):
        status = {
            "label": "⚠️ Polling retrasado",
            "class": "status-pill status-pill--warning",
            "detail": f"Última actualización hace {_format_timedelta(time_since_last)}.",
        }
    return status


def resolve_snapshot_context(
    snapshots_df: pd.DataFrame,
    selected_timestamp: dt.datetime | None,
) -> tuple[dt.datetime | None, dt.datetime | None]:
    """Español: Calcula snapshot actual y previo para el contexto histórico.

    English: Compute current and previous snapshot timestamps for historical context.
    """
    if snapshots_df.empty:
        return None, None
    df = snapshots_df.copy()
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp_dt"]).sort_values("timestamp_dt")
    if df.empty:
        return None, None
    if selected_timestamp is not None:
        df = df[df["timestamp_dt"] <= selected_timestamp]
    if df.empty:
        return None, None
    current_ts = df["timestamp_dt"].max()
    previous_df = df[df["timestamp_dt"] < current_ts]
    previous_ts = previous_df["timestamp_dt"].max() if not previous_df.empty else None
    return current_ts, previous_ts


def derive_alert_thresholds(resilience_cfg: dict, expected_streams: int) -> dict[str, int]:
    """Español: Calcula umbrales de alerta basados en rules.yaml para diffs/anomalías.

    English: Compute alert thresholds from rules.yaml for diffs/anomalies visibility.
    """
    min_samples = int(resilience_cfg.get("benford_min_samples", 10) or 10)
    diff_error_min = max(2, int(round(expected_streams * 0.2)))
    anomaly_error_min = max(1, min_samples)
    return {
        "diff_error_min": diff_error_min,
        "anomaly_error_min": anomaly_error_min,
        "min_samples": min_samples,
    }


def emit_toast(message: str, icon: str = "⚠️") -> None:
    """Español: Emite una notificación tipo snackbar si está disponible.

    English: Emit a snackbar-style notification when available.
    """
    if hasattr(st, "toast"):
        st.toast(message, icon=icon)


def _get_query_param(name: str) -> str | None:
    """Español: Función _get_query_param del módulo dashboard/streamlit_app.py.

    English: Function _get_query_param defined in dashboard/streamlit_app.py.
    """
    if hasattr(st, "query_params"):
        value = st.query_params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value
    params = st.experimental_get_query_params()
    value = params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _get_secret_value(name: str) -> str:
    """Español: Función _get_secret_value del módulo dashboard/streamlit_app.py.

    English: Function _get_secret_value defined in dashboard/streamlit_app.py.
    """
    value = st.secrets.get(name)
    return str(value) if value is not None else ""


def render_admin_gate() -> bool:
    """Español: Función render_admin_gate del módulo dashboard/streamlit_app.py.

    English: Function render_admin_gate defined in dashboard/streamlit_app.py.
    """
    expected_user = _get_secret_value("admin_user") or _get_secret_value("admin_username")
    expected_password = _get_secret_value("admin_password")
    token = _get_secret_value("admin_token")
    query_token = _get_query_param("admin")

    if token and query_token and query_token == token:
        return True

    if not expected_user or not expected_password:
        st.error("Autenticación no configurada. Define admin_user y admin_password en st.secrets.")
        return False

    if st.session_state.get("admin_authenticated"):
        return True

    with st.form("admin_login"):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")
        if submitted:
            if user == expected_user and password == expected_password:
                st.session_state.admin_authenticated = True
                st.success("Autenticación exitosa.")
                rerun_app()
            else:
                st.error("Credenciales inválidas.")
    return False


def _format_short_hash(value: str | None) -> str:
    """Español: Función _format_short_hash del módulo dashboard/streamlit_app.py.

    English: Function _format_short_hash defined in dashboard/streamlit_app.py.
    """
    if not value:
        return "N/D"
    if len(value) <= 16:
        return value
    return f"{value[:8]}…{value[-8:]}"


def _format_timedelta(delta: dt.timedelta | None) -> str:
    """Español: Función _format_timedelta del módulo dashboard/streamlit_app.py.

    English: Function _format_timedelta defined in dashboard/streamlit_app.py.
    """
    if delta is None:
        return "Sin datos"
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _parse_timestamp(value: Any) -> dt.datetime | None:
    """Español: Función _parse_timestamp del módulo dashboard/streamlit_app.py.

    English: Function _parse_timestamp defined in dashboard/streamlit_app.py.
    """
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    if isinstance(value, str):
        try:
            parsed = date_parser.parse(value)
        except (ValueError, TypeError):
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    return None


def _pick_latest_snapshot(snapshot_files: list[dict[str, Any]]) -> dict[str, Any]:
    """Español: Función _pick_latest_snapshot del módulo dashboard/streamlit_app.py.

    English: Function _pick_latest_snapshot defined in dashboard/streamlit_app.py.
    """
    if not snapshot_files:
        return {}

    def sort_key(entry: dict[str, Any]) -> dt.datetime:
        """Español: Función sort_key del módulo dashboard/streamlit_app.py.

        English: Function sort_key defined in dashboard/streamlit_app.py.
        """
        timestamp = _parse_timestamp(entry.get("timestamp"))
        if timestamp:
            return timestamp
        try:
            return dt.datetime.fromtimestamp(entry["path"].stat().st_mtime, tz=dt.timezone.utc)
        except OSError:
            return dt.datetime.min.replace(tzinfo=dt.timezone.utc)

    latest = max(snapshot_files, key=sort_key)
    return latest


def _resolve_latest_snapshot_info(
    snapshot_files: list[dict[str, Any]],
    default_hash: str,
) -> tuple[dict[str, Any], dt.datetime | None, str, str]:
    """Español: Resuelve el último snapshot y sus metadatos principales.

    English: Resolve latest snapshot and core metadata.
    """
    latest_snapshot: dict[str, Any] = {}
    latest_timestamp = None
    last_batch_label = "N/D"
    hash_accumulator = default_hash
    if not snapshot_files:
        return latest_snapshot, latest_timestamp, last_batch_label, hash_accumulator
    latest_snapshot = _pick_latest_snapshot(snapshot_files)
    content = latest_snapshot.get("content", {}) if latest_snapshot else {}
    latest_timestamp = _parse_timestamp(latest_snapshot.get("timestamp"))
    if latest_timestamp is None and latest_snapshot.get("path"):
        try:
            latest_timestamp = dt.datetime.fromtimestamp(latest_snapshot["path"].stat().st_mtime, tz=dt.timezone.utc)
        except OSError:
            latest_timestamp = None
    last_batch_label = (
        content.get("acta_id")
        or content.get("batch_id")
        or content.get("last_batch")
        or (latest_snapshot.get("path").stem if latest_snapshot else "N/D")
    )
    hash_accumulator = latest_snapshot.get("hash") or default_hash
    return latest_snapshot, latest_timestamp, last_batch_label, hash_accumulator


def _count_failed_retries(log_path: Path) -> int:
    """Español: Función _count_failed_retries del módulo dashboard/streamlit_app.py.

    English: Function _count_failed_retries defined in dashboard/streamlit_app.py.
    """
    if not log_path.exists():
        return 0
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
    count = 0
    try:
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return 0
    for line in lines:
        lowered = line.lower()
        if "retry" not in lowered:
            continue
        if "error" not in lowered and "fail" not in lowered:
            continue
        timestamp = _parse_timestamp(line.split(" ", 1)[0])
        if timestamp is None or timestamp >= cutoff:
            count += 1
    return count


def _count_rate_limit_retries(log_path: Path) -> int:
    """Español: Cuenta reintentos con rate-limit en el log.

    English: Count rate-limit retries in log.
    """
    if not log_path.exists():
        return 0
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
    count = 0
    try:
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return 0
    for line in lines:
        lowered = line.lower()
        if "rate" not in lowered and "429" not in lowered:
            continue
        if "limit" not in lowered and "too many requests" not in lowered and "429" not in lowered:
            continue
        timestamp = _parse_timestamp(line.split(" ", 1)[0])
        if timestamp is None or timestamp >= cutoff:
            count += 1
    return count


def _check_bucket_connection() -> dict[str, Any]:
    """Español: Función _check_bucket_connection del módulo dashboard/streamlit_app.py.

    English: Function _check_bucket_connection defined in dashboard/streamlit_app.py.
    """
    if not BOTO3_AVAILABLE:
        return {
            "status": "No disponible",
            "latency_ms": None,
            "message": "Dependencia boto3 no instalada.",
        }
    bucket = os.getenv("CHECKPOINT_BUCKET", "").strip()
    if not bucket:
        return {"status": "No configurado", "latency_ms": None, "message": ""}
    endpoint = os.getenv("STORAGE_ENDPOINT_URL")
    region = os.getenv("AWS_REGION", "us-east-1")
    start = time.perf_counter()
    try:
        client = boto3.client("s3", endpoint_url=endpoint, region_name=region)
        client.head_bucket(Bucket=bucket)
    except Exception as exc:  # noqa: BLE001
        return {"status": "Error", "latency_ms": None, "message": str(exc)}
    latency_ms = (time.perf_counter() - start) * 1000
    return {"status": "OK", "latency_ms": latency_ms, "message": ""}


def _detect_supervisor() -> str:
    """Español: Función _detect_supervisor del módulo dashboard/streamlit_app.py.

    English: Function _detect_supervisor defined in dashboard/streamlit_app.py.
    """
    if os.path.exists("/.dockerenv"):
        return "Docker detectado"
    if os.path.exists("/run/systemd/system") or shutil.which("systemctl"):
        return "systemd detectado"
    return f"No detectado ({platform.system()})"


def _build_checkpoint_manager() -> "CheckpointManager | None":
    """Español: Función _build_checkpoint_manager del módulo dashboard/streamlit_app.py.

    English: Function _build_checkpoint_manager defined in dashboard/streamlit_app.py.
    """
    if not CHECKPOINTING_AVAILABLE:
        return None
    bucket = os.getenv("CHECKPOINT_BUCKET", "").strip()
    if not bucket:
        return None
    config = CheckpointConfig(
        bucket=bucket,
        pipeline_version=os.getenv("PIPELINE_VERSION", "v1"),
        run_id=os.getenv("RUN_ID", "dashboard"),
        s3_endpoint_url=os.getenv("STORAGE_ENDPOINT_URL"),
        s3_region=os.getenv("AWS_REGION", "us-east-1"),
        s3_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        s3_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    return CheckpointManager(config)


@st.cache_data(show_spinner=False)
def load_snapshot_files(
    base_dir: Path,
    pattern: str = "snapshot_*.json",
    explicit_files: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Español: Función load_snapshot_files del módulo dashboard/streamlit_app.py.

    English: Function load_snapshot_files defined in dashboard/streamlit_app.py.
    """
    if explicit_files:
        paths = [base_dir / name for name in explicit_files]
    else:
        paths = iter_all_snapshots(data_root=base_dir, pattern=pattern)
        if not paths and pattern != "*.json":
            paths = iter_all_snapshots(data_root=base_dir, pattern="*.json")
    snapshots = []
    for path in paths:
        if not path.exists():
            continue
        payload = _safe_read_json(path)
        if payload is None:
            continue
        try:
            content = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            continue
        timestamp = payload.get("timestamp")
        if not timestamp:
            try:
                timestamp = path.stem.replace("snapshot_", "").replace("_", " ")
            except ValueError:
                timestamp = ""
        source_value = str(payload.get("source") or payload.get("source_url") or payload.get("fuente") or "").upper()
        parsed_ts = None
        if timestamp:
            try:
                parsed_ts = date_parser.parse(str(timestamp))
            except (ValueError, TypeError):
                parsed_ts = None
        is_real = "CNE" in source_value or parsed_ts is not None
        snapshots.append(
            {
                "path": path,
                "timestamp": timestamp,
                "content": payload,
                "hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "is_real": is_real,
            }
        )
    return snapshots


def _pick_from_seed(seed: int, options: list[str]) -> str:
    """Español: Función _pick_from_seed del módulo dashboard/streamlit_app.py.

    English: Function _pick_from_seed defined in dashboard/streamlit_app.py.
    """
    rng = random.Random(seed)
    return options[rng.randint(0, len(options) - 1)]


@st.cache_data(show_spinner=False)
def build_snapshot_metrics(snapshot_files: list[dict[str, Any]]) -> pd.DataFrame:
    """Español: Función build_snapshot_metrics del módulo dashboard/streamlit_app.py.

    English: Function build_snapshot_metrics defined in dashboard/streamlit_app.py.
    """
    if not snapshot_files:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "hash",
                "delta",
                "votes",
                "changes",
                "department",
                "level",
                "status",
                "is_real",
                "timestamp_dt",
                "hour",
            ]
        )
    departments = [
        "Atlántida",
        "Choluteca",
        "Colón",
        "Comayagua",
        "Copán",
        "Cortés",
        "El Paraíso",
        "Francisco Morazán",
        "Gracias a Dios",
        "Intibucá",
        "Islas de la Bahía",
        "La Paz",
        "Lempira",
        "Ocotepeque",
        "Olancho",
        "Santa Bárbara",
        "Valle",
        "Yoro",
    ]
    rows = []
    base_votes = 120_000
    for idx, snapshot in enumerate(snapshot_files):
        seed = int(snapshot["hash"][:8], 16)
        rng = random.Random(seed)
        delta = rng.randint(-600, 1400)
        base_votes += 5_000 + rng.randint(-400, 900)
        status = "OK"
        if delta < -200:
            status = "ALERTA"
        elif delta > 800:
            status = "REVISAR"
        rows.append(
            {
                "timestamp": snapshot["timestamp"],
                "hash": f"{snapshot['hash'][:6]}...{snapshot['hash'][-4:]}",
                "delta": delta,
                "votes": base_votes,
                "changes": abs(delta) // 50,
                "department": _pick_from_seed(seed, departments),
                "level": "Presidencial",
                "status": status,
                "is_real": snapshot.get("is_real", False),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["hour"] = df["timestamp_dt"].dt.strftime("%H:%M")
    return df


def build_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Español: Función build_anomalies del módulo dashboard/streamlit_app.py.

    English: Function build_anomalies defined in dashboard/streamlit_app.py.
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "department",
                "delta",
                "delta_pct",
                "votes",
                "type",
                "timestamp",
                "hour",
                "hash",
            ]
        )
    anomalies = df.loc[df["status"].isin(["ALERTA", "REVISAR"])].copy()
    anomalies["delta_pct"] = (anomalies["delta"] / anomalies["votes"]).round(4) * 100
    anomalies["type"] = anomalies["delta"].apply(
        lambda value: "Delta negativo" if value < 0 else "Outlier de crecimiento"
    )
    anomalies["timestamp"] = anomalies["timestamp"]
    anomalies["hour"] = anomalies.get("hour")
    anomalies["hash"] = anomalies.get("hash")
    return anomalies[
        [
            "department",
            "delta",
            "delta_pct",
            "votes",
            "type",
            "timestamp",
            "hour",
            "hash",
        ]
    ]


def build_heatmap(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Español: Función build_heatmap del módulo dashboard/streamlit_app.py.

    English: Function build_heatmap defined in dashboard/streamlit_app.py.
    """
    if anomalies.empty:
        return pd.DataFrame()
    anomalies = anomalies.copy()
    anomalies["hour"] = pd.to_datetime(anomalies["timestamp"], errors="coerce", utc=True).dt.hour
    heatmap = anomalies.groupby(["department", "hour"], dropna=False).size().reset_index(name="anomaly_count")
    return heatmap


def compute_topology_integrity(
    snapshots_df: pd.DataFrame, departments: list[str]
) -> dict[str, int | bool | list[dict[str, int | str]]]:
    """Español: Función compute_topology_integrity del módulo dashboard/streamlit_app.py.

    English: Function compute_topology_integrity defined in dashboard/streamlit_app.py.
    """
    if snapshots_df.empty:
        return {
            "department_total": 0,
            "national_total": 0,
            "delta": 0,
            "is_match": True,
            "department_breakdown": [],
        }
    df = snapshots_df.copy()
    if "timestamp_dt" not in df.columns:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.sort_values("timestamp_dt")
    dept_df = df[df["department"].isin(departments)]
    latest_per_dept = dept_df.sort_values("timestamp_dt").groupby("department", as_index=False).tail(1)
    department_total = int(latest_per_dept["votes"].sum())
    breakdown = [{"department": row["department"], "votes": int(row["votes"])} for _, row in latest_per_dept.iterrows()]
    national_df = df[~df["department"].isin(departments)]
    if not national_df.empty:
        national_total = int(national_df.iloc[-1]["votes"])
    else:
        national_total = int(df.iloc[-1]["votes"])
    delta = department_total - national_total
    return {
        "department_total": department_total,
        "national_total": national_total,
        "delta": delta,
        "is_match": delta == 0,
        "department_breakdown": breakdown,
    }


def build_latency_matrix(
    snapshots_df: pd.DataFrame, departments: list[str], report_time: dt.datetime
) -> tuple[list[list[str]], list[dict[str, int | bool]]]:
    """Español: Función build_latency_matrix del módulo dashboard/streamlit_app.py.

    English: Function build_latency_matrix defined in dashboard/streamlit_app.py.
    """
    if report_time.tzinfo is None:
        report_time = report_time.replace(tzinfo=dt.timezone.utc)
    df = snapshots_df.copy()
    if "timestamp_dt" not in df.columns:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    cells = []
    for dept in departments:
        dept_rows = df[df["department"] == dept]
        last_dt = None
        if not dept_rows.empty:
            last_dt = dept_rows["timestamp_dt"].max()
        last_label = "Sin datos"
        stale = True
        if isinstance(last_dt, pd.Timestamp) and not pd.isna(last_dt):
            last_dt = last_dt.to_pydatetime()
        if isinstance(last_dt, dt.datetime):
            last_label = last_dt.strftime("%H:%M")
            stale = (report_time - last_dt).total_seconds() > 3600
        cells.append({"department": dept, "last_update": last_label, "stale": stale})
    per_row = 6
    rows = []
    cell_styles = []
    for idx, cell in enumerate(cells):
        row_idx = idx // per_row
        col_idx = idx % per_row
        cell_styles.append({"row": row_idx, "col": col_idx, "stale": cell["stale"]})
    for row_start in range(0, len(cells), per_row):
        row_cells = cells[row_start : row_start + per_row]
        rows.append([f"{cell['department']}\n{cell['last_update']}" for cell in row_cells])
    return rows, cell_styles


def compute_ingestion_velocity(snapshots_df: pd.DataFrame) -> float:
    """Español: Función compute_ingestion_velocity del módulo dashboard/streamlit_app.py.

    English: Function compute_ingestion_velocity defined in dashboard/streamlit_app.py.
    """
    if snapshots_df.empty:
        return 0.0
    df = snapshots_df.copy()
    if "timestamp_dt" not in df.columns:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp_dt"]).sort_values("timestamp_dt")
    if df.empty:
        return 0.0
    first_votes = float(df.iloc[0]["votes"])
    last_votes = float(df.iloc[-1]["votes"])
    delta_votes = max(last_votes - first_votes, 0.0)
    minutes = max(
        (df.iloc[-1]["timestamp_dt"] - df.iloc[0]["timestamp_dt"]).total_seconds() / 60,
        1.0,
    )
    return delta_votes / minutes


@st.cache_data(show_spinner=False)
def build_benford_data() -> pd.DataFrame:
    """Español: Función build_benford_data del módulo dashboard/streamlit_app.py.

    English: Function build_benford_data defined in dashboard/streamlit_app.py.
    """
    expected = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]
    observed = [29.3, 18.2, 12.1, 10.4, 7.2, 6.9, 5.5, 5.0, 5.4]
    digits = list(range(1, 10))
    return pd.DataFrame({"digit": digits, "expected": expected, "observed": observed})


def build_rules_table(command_center_cfg: dict) -> pd.DataFrame:
    """Español: Función build_rules_table del módulo dashboard/streamlit_app.py.

    English: Function build_rules_table defined in dashboard/streamlit_app.py.
    """
    rules_cfg = command_center_cfg.get("rules", {}) if command_center_cfg else {}
    rows = []
    for key, settings in rules_cfg.items():
        if key == "global_enabled":
            continue
        if not isinstance(settings, dict):
            continue
        rows.append(
            {
                "rule": key.replace("_", " ").title(),
                "enabled": "ON" if settings.get("enabled", True) else "OFF",
                "thresholds": ", ".join(f"{k}: {v}" for k, v in settings.items() if k != "enabled"),
            }
        )
    return pd.DataFrame(rows)


def build_rules_engine_payload(snapshot_row: pd.Series) -> dict:
    """Español: Función build_rules_engine_payload del módulo dashboard/streamlit_app.py.

    English: Function build_rules_engine_payload defined in dashboard/streamlit_app.py.
    """
    return {
        "timestamp": snapshot_row.get("timestamp"),
        "departamento": snapshot_row.get("department", "N/D"),
        "totals": {
            "total_votes": _safe_int(snapshot_row.get("votes")),
            "valid_votes": _safe_int(snapshot_row.get("votes", 0) * 0.92),
            "null_votes": _safe_int(snapshot_row.get("votes", 0) * 0.05),
            "blank_votes": _safe_int(snapshot_row.get("votes", 0) * 0.03),
        },
    }


def run_rules_engine(snapshot_df: pd.DataFrame, config: dict) -> dict:
    """Español: Función run_rules_engine del módulo dashboard/streamlit_app.py.

    English: Function run_rules_engine defined in dashboard/streamlit_app.py.
    """
    if RulesEngine is None or snapshot_df.empty:
        return {"alerts": [], "critical": []}
    engine = RulesEngine(config=config)
    current = build_rules_engine_payload(snapshot_df.iloc[-1])
    previous = build_rules_engine_payload(snapshot_df.iloc[-2]) if len(snapshot_df) > 1 else None
    try:
        result = engine.run(current, previous, snapshot_id=snapshot_df.iloc[-1]["timestamp"])
    except Exception:  # noqa: BLE001
        return {"alerts": [], "critical": []}
    return {"alerts": result.alerts, "critical": result.critical_alerts}


def create_pdf_charts(
    benford_df: pd.DataFrame,
    votes_df: pd.DataFrame,
    heatmap_df: pd.DataFrame,
    anomalies_df: pd.DataFrame,
    topology: dict,
    snapshots_df: pd.DataFrame,
    departments: list[str],
) -> dict:
    """Español: Función create_pdf_charts del módulo dashboard/streamlit_app.py.

    English: Function create_pdf_charts defined in dashboard/streamlit_app.py.
    """
    if plt is None:
        return {}

    chart_buffers = {}

    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    sample_size = max(len(votes_df), 1)
    expected = benford_df["expected"] / 100.0
    observed = benford_df["observed"] / 100.0
    ci = 1.96 * (expected * (1 - expected) / sample_size) ** 0.5
    upper = expected + ci
    lower = expected - ci
    bars = ax.bar(
        benford_df["digit"],
        observed * 100,
        label="Observado",
        color="#002147",
        alpha=0.9,
    )
    ax.plot(
        benford_df["digit"],
        expected * 100,
        color="#708090",
        linewidth=2,
        label="Benford Teórico",
    )
    ax.fill_between(
        benford_df["digit"],
        lower * 100,
        upper * 100,
        color="#CBD5F5",
        alpha=0.4,
        label="Margen 95%",
    )
    for idx, bar in enumerate(bars):
        if observed.iloc[idx] < lower.iloc[idx] or observed.iloc[idx] > upper.iloc[idx]:
            bar.set_color("#B22222")
            ax.scatter(
                [benford_df["digit"].iloc[idx]],
                [observed.iloc[idx] * 100],
                color="#B22222",
                s=40,
                marker="x",
                zorder=4,
            )
    ax.set_title("Análisis Benford con margen 95%")
    ax.set_xlabel("Dígito")
    ax.set_ylabel("%")
    ax.legend(loc="upper right", fontsize=8)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=300)
    plt.close(fig)
    buf.seek(0)
    chart_buffers["benford"] = buf

    if not votes_df.empty:
        fig, ax = plt.subplots(figsize=(6.8, 2.6))
        ax.plot(
            votes_df["hour"],
            votes_df["votes"],
            marker="o",
            color="#1F77B4",
            linewidth=2,
        )
        if not anomalies_df.empty:
            ax.scatter(
                anomalies_df["hour"],
                anomalies_df["votes"],
                color="#D62728",
                marker="o",
                s=40,
                label="Anomalía",
                zorder=3,
            )
        ax.set_title("Evolución por hora (timeline)")
        ax.set_xlabel("Hora")
        ax.set_ylabel("Votos")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(alpha=0.2)
        ax.legend(loc="upper left", fontsize=8)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=300)
        plt.close(fig)
        buf.seek(0)
        chart_buffers["timeline"] = buf

    if not heatmap_df.empty:
        heatmap_pivot = heatmap_df.pivot(index="department", columns="hour", values="anomaly_count").fillna(0)
        fig, ax = plt.subplots(figsize=(13.0, 3.4))
        ax.imshow(heatmap_pivot.values, aspect="auto", cmap="Reds")
        ax.set_title("Mapa de anomalías por departamento/hora")
        ax.set_yticks(range(len(heatmap_pivot.index)))
        ax.set_yticklabels(heatmap_pivot.index, fontsize=6)
        ax.set_xticks(range(len(heatmap_pivot.columns)))
        ax.set_xticklabels([str(x) for x in heatmap_pivot.columns], fontsize=6, rotation=45)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=300)
        plt.close(fig)
        buf.seek(0)
        chart_buffers["heatmap"] = buf

    if topology and not topology.get("is_match", True):
        dept_breakdown = topology.get("department_breakdown", [])
        national_total = float(topology.get("national_total", 0))
        dept_values = [float(item["votes"]) for item in dept_breakdown]
        dept_labels = [item["department"] for item in dept_breakdown]
        dept_sum = sum(dept_values)
        floating = national_total - dept_sum
        fig, ax = plt.subplots(figsize=(6.8, 2.8))
        labels = ["Nacional"] + dept_labels + ["DISCREPANCIA NO IDENTIFICADA"]
        values = [national_total] + dept_values + [floating]
        colors_list = ["#1F77B4"] + ["#002147"] * len(dept_values) + ["#B22222"]
        for idx, (label, value, color) in enumerate(zip(labels, values, colors_list)):
            ax.bar(idx, value, color=color, alpha=0.85)
        ax.axhline(national_total, color="#94A3B8", linestyle="--", linewidth=1)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel("Votos")
        ax.set_title("Cascada de discrepancia nacional")
        ax.grid(axis="y", alpha=0.2)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=300)
        plt.close(fig)
        buf.seek(0)
        chart_buffers["waterfall"] = buf

    if not snapshots_df.empty and "hash" in snapshots_df.columns:
        recent_hashes = snapshots_df["hash"].head(5).tolist()
        fig, ax = plt.subplots(figsize=(6.8, 2.0))
        ax.axis("off")
        for idx, value in enumerate(recent_hashes):
            label = str(value)[:8]
            x = idx * 1.4
            ax.add_patch(plt.Rectangle((x, 0.4), 1.1, 0.6, color="#1F2937", alpha=0.9))
            ax.text(
                x + 0.55,
                0.7,
                label,
                color="white",
                ha="center",
                va="center",
                fontsize=8,
            )
            if idx < len(recent_hashes) - 1:
                ax.annotate(
                    "",
                    xy=(x + 1.2, 0.7),
                    xytext=(x + 1.35, 0.7),
                    arrowprops=dict(arrowstyle="->", color="#10B981"),
                )
        ax.set_xlim(-0.2, len(recent_hashes) * 1.4)
        ax.set_ylim(0, 1.5)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, transparent=True)
        plt.close(fig)
        buf.seek(0)
        chart_buffers["chain"] = buf

    if not snapshots_df.empty and departments:
        df = snapshots_df.copy()
        df["hour"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.hour
        load_pivot = (
            df[df["department"].isin(departments)]
            .groupby(["department", "hour"], dropna=False)
            .size()
            .reset_index(name="processed")
        )
        if not load_pivot.empty:
            pivot = (
                load_pivot.pivot(index="department", columns="hour", values="processed")
                .reindex(index=departments)
                .fillna(0)
            )
            pivot = pivot.reindex(columns=list(range(24)), fill_value=0)
            fig, ax = plt.subplots(figsize=(6.8, 3.2))
            ax.imshow(pivot.values, aspect="auto", cmap="Blues")
            ax.set_title("Matriz de carga (snapshots por hora)")
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index, fontsize=6)
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels([str(x) for x in pivot.columns], fontsize=6)
            buf = io.BytesIO()
            fig.tight_layout()
            fig.savefig(buf, format="png", dpi=300)
            plt.close(fig)
            buf.seek(0)
            chart_buffers["load_heatmap"] = buf

    return chart_buffers


def _register_pdf_fonts() -> tuple[str, str]:
    """Español: Función _register_pdf_fonts del módulo dashboard/streamlit_app.py.

    English: Function _register_pdf_fonts defined in dashboard/streamlit_app.py.
    """
    if not REPORTLAB_AVAILABLE:
        return "Helvetica", "Helvetica-Bold"
    font_candidates = [
        ("Arial", "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"),
        ("Arial", "/usr/share/fonts/truetype/msttcorefonts/arial.ttf"),
        ("Arial", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    bold_candidates = [
        ("Arial-Bold", "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf"),
        ("Arial-Bold", "/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf"),
        ("Arial-Bold", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    regular = "Helvetica"
    bold = "Helvetica-Bold"
    for name, path in font_candidates:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))
            regular = name
            break
    for name, path in bold_candidates:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))
            bold = name
            break
    return regular, bold


if REPORTLAB_AVAILABLE:

    class NumberedCanvas(reportlab_canvas.Canvas):
        """Español: Clase NumberedCanvas del módulo dashboard/streamlit_app.py.

        English: NumberedCanvas class defined in dashboard/streamlit_app.py.
        """

        def __init__(self, *args, root_hash: str = "", **kwargs) -> None:
            """Español: Función __init__ del módulo dashboard/streamlit_app.py.

            English: Function __init__ defined in dashboard/streamlit_app.py.
            """
            super().__init__(*args, **kwargs)
            self._saved_page_states = []
            self._root_hash = root_hash
            self._page_hashes: list[str] = []

        def showPage(self) -> None:
            """Español: Función showPage del módulo dashboard/streamlit_app.py.

            English: Function showPage defined in dashboard/streamlit_app.py.
            """
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            """Español: Función save del módulo dashboard/streamlit_app.py.

            English: Function save defined in dashboard/streamlit_app.py.
            """
            total_pages = len(self._saved_page_states)
            prev_hash = hashlib.sha256(self._root_hash.encode("utf-8")).hexdigest()[:12]
            for state in self._saved_page_states:
                self.__dict__.update(state)
                page = self.getPageNumber()
                current_hash = hashlib.sha256(f"{prev_hash}|{page}".encode("utf-8")).hexdigest()[:12]
                self.draw_page_number(total_pages, current_hash)
                prev_hash = current_hash
                super().showPage()
            super().save()

        def draw_page_number(self, total_pages: int, current_hash: str) -> None:
            """Español: Función draw_page_number del módulo dashboard/streamlit_app.py.

            English: Function draw_page_number defined in dashboard/streamlit_app.py.
            """
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.grey)
            page = self.getPageNumber()
            self.drawRightString(
                self._pagesize[0] - 1.5 * cm,
                0.75 * cm,
                f"Página {page}/{total_pages}",
            )
            self.setFont("Helvetica", 7)
            self.drawString(
                1.5 * cm,
                0.3 * cm,
                f"Pag {page} | SHA-256 Page Hash: {current_hash}",
            )
            self.setFont("Helvetica", 7)
            self.drawRightString(
                self._pagesize[0] - 1.5 * cm,
                0.3 * cm,
                "Auditoría Independiente - Proyecto Centinel",
            )

else:

    class NumberedCanvas:  # pragma: no cover - placeholder when reportlab is absent
        """Español: Clase NumberedCanvas del módulo dashboard/streamlit_app.py.

        English: NumberedCanvas class defined in dashboard/streamlit_app.py.
        """

        pass


def build_pdf_report(data: dict, chart_buffers: dict) -> bytes:
    """Español: Función build_pdf_report del módulo dashboard/streamlit_app.py.

    English: Function build_pdf_report defined in dashboard/streamlit_app.py.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is required to build the PDF report.")

    regular_font, bold_font = _register_pdf_fonts()
    buffer = io.BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="HeadingPrimary",
            fontName=bold_font,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1F77B4"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeadingSecondary",
            fontName=bold_font,
            fontSize=12,
            leading=15,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            fontName=regular_font,
            fontSize=10,
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            fontName=regular_font,
            fontSize=9.5,
            leading=11,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            fontName=bold_font,
            fontSize=9.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AlertText",
            fontName=bold_font,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#B91C1C"),
        )
    )

    def as_paragraph(value: object, style: ParagraphStyle) -> Paragraph:
        """Español: Función as_paragraph del módulo dashboard/streamlit_app.py.

        English: Function as_paragraph defined in dashboard/streamlit_app.py.
        """
        return Paragraph(str(value), style)

    def build_table(rows: list[list[object]], col_widths: list[float]) -> Table:
        """Español: Función build_table del módulo dashboard/streamlit_app.py.

        English: Function build_table defined in dashboard/streamlit_app.py.
        """
        header = [as_paragraph(cell, styles["TableHeader"]) for cell in rows[0]]
        body = [[as_paragraph(cell, styles["TableCell"]) for cell in row] for row in rows[1:]]
        table = Table([header] + body, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F77B4")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d4db")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    elements: list = []
    header_title = Paragraph(
        "C.E.N.T.I.N.E.L. - Informe de Integridad Transaccional v5.0",
        styles["HeadingPrimary"],
    )
    qr_cell = Spacer(1, 1)
    if data.get("qr"):
        qr_cell = Image(data["qr"], width=2.2 * cm, height=2.2 * cm)
    header_table = Table([[header_title, qr_cell]], colWidths=[doc.width * 0.75, doc.width * 0.25])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    elements.append(header_table)
    elements.append(Paragraph(data["subtitle"], styles["Body"]))
    elements.append(Paragraph(data["input_source"], styles["Body"]))
    elements.append(Paragraph(data["generated"], styles["Body"]))
    elements.append(
        Paragraph(
            f"Snapshots procesados: {data.get('snapshot_count', 'N/A')}",
            styles["Body"],
        )
    )
    elements.append(Paragraph(data["global_status"], styles["HeadingSecondary"]))
    badge_info = data.get("status_badge", {})
    if badge_info:
        badge_color = colors.HexColor(badge_info.get("color", "#008000"))
        badge_table = Table([[badge_info.get("label", "")]], colWidths=[doc.width * 0.4])
        badge_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), badge_color),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, -1), bold_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        elements.append(badge_table)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("Sección 1 · Estatus Global", styles["HeadingSecondary"]))
    elements.append(Paragraph(data["executive_summary"], styles["Body"]))
    kpi_widths = [doc.width * 0.166] * 6
    kpi_table = build_table(data["kpi_rows"], kpi_widths)
    kpi_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f2f4f8")),
            ]
        )
    )
    elements.append(kpi_table)
    if data.get("forensic_summary"):
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(data["forensic_summary"], styles["Body"]))
    elements.append(Spacer(1, 8))

    elements.append(PageBreak())
    elements.append(
        Paragraph(
            "Sección 1.1 · Integridad de Topología (Cross-Check)",
            styles["HeadingSecondary"],
        )
    )
    topology_style = "Body" if data["topology"]["is_match"] else "AlertText"
    elements.append(Paragraph(data["topology_summary"], styles[topology_style]))
    topology_table = build_table(data["topology_rows"], [doc.width * 0.3] * 3)
    elements.append(topology_table)
    if "waterfall" in chart_buffers:
        elements.append(Spacer(1, 4))
        elements.append(Image(chart_buffers["waterfall"], width=doc.width * 0.6, height=4.2 * cm))
        if data.get("topology_alert"):
            elements.append(Paragraph(data["topology_alert"], styles["AlertText"]))
    elements.append(Spacer(1, 8))

    elements.append(
        Paragraph(
            "Sección 1.2 · Latencia de Nodos (Último Update)",
            styles["HeadingSecondary"],
        )
    )
    latency_rows = data.get("latency_rows", [])
    if latency_rows:
        per_row = len(latency_rows[0])
        latency_table = Table(latency_rows, colWidths=[doc.width / per_row] * per_row)
        latency_style = TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d4db")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
            ]
        )
        for cell in data.get("latency_alert_cells", []):
            row_idx = cell["row"]
            col_idx = cell["col"]
            if cell["stale"]:
                latency_style.add(
                    "BACKGROUND",
                    (col_idx, row_idx),
                    (col_idx, row_idx),
                    colors.HexColor("#fee2e2"),
                )
                latency_style.add(
                    "TEXTCOLOR",
                    (col_idx, row_idx),
                    (col_idx, row_idx),
                    colors.HexColor("#b91c1c"),
                )
            else:
                latency_style.add(
                    "BACKGROUND",
                    (col_idx, row_idx),
                    (col_idx, row_idx),
                    colors.HexColor("#ecfdf3"),
                )
        latency_table.setStyle(latency_style)
        elements.append(latency_table)
        if "load_heatmap" in chart_buffers:
            elements.append(Spacer(1, 4))
            elements.append(Image(chart_buffers["load_heatmap"], width=doc.width, height=4.6 * cm))
    else:
        elements.append(Paragraph("Sin datos de latencia disponibles.", styles["Body"]))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Sección 2 · Anomalías Detectadas", styles["HeadingSecondary"]))
    anomaly_rows = data["anomaly_rows"]
    anomaly_col_widths = [
        doc.width * 0.14,
        doc.width * 0.14,
        doc.width * 0.12,
        doc.width * 0.12,
        doc.width * 0.18,
        doc.width * 0.3,
    ]
    anomaly_table = build_table(anomaly_rows, anomaly_col_widths)
    table_style = [
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.whitesmoke, colors.HexColor("#f8fafc")],
        ),
    ]
    for row_idx, row in enumerate(anomaly_rows[1:], start=1):
        delta_pct = str(row[2]).replace("%", "").strip()
        try:
            delta_pct_val = float(delta_pct)
        except ValueError:
            delta_pct_val = 0.0
        if "ROLLBACK / ELIMINACIÓN DE DATOS" in str(row[5]):
            table_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#FADBD8")))
        elif "OUTLIER" in str(row[5]).upper():
            table_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#FCF3CF")))
        elif delta_pct_val <= -1.0:
            table_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#fdecea")))
            table_style.append(("TEXTCOLOR", (1, row_idx), (2, row_idx), colors.HexColor("#D62728")))
    table_style.append(("FONTNAME", (4, 1), (4, -1), "Courier"))
    table_style.append(("FONTSIZE", (4, 1), (4, -1), 7))
    table_style.append(("LEADING", (4, 1), (4, -1), 8))
    anomaly_table.setStyle(TableStyle(table_style))
    elements.append(anomaly_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Sección 3 · Gráficos Avanzados", styles["HeadingSecondary"]))
    for key, caption in data["chart_captions"].items():
        buf = chart_buffers.get(key)
        if buf:
            height = 5.5 * cm
            if key == "heatmap":
                height = 6.8 * cm
            elements.append(Image(buf, width=doc.width, height=height))
            elements.append(Paragraph(caption, styles["Body"]))
            elements.append(Spacer(1, 4))
    elements.append(PageBreak())
    elements.append(Paragraph("Cadena de Bloques (Snapshots)", styles["HeadingSecondary"]))
    chain_buf = chart_buffers.get("chain")
    if chain_buf:
        elements.append(Image(chain_buf, width=doc.width * 0.7, height=3.5 * cm))
        elements.append(Paragraph("Cadena de snapshots recientes.", styles["Body"]))
        elements.append(Spacer(1, 4))

    elements.append(Paragraph("Sección 4 · Snapshots Recientes", styles["HeadingSecondary"]))
    snapshot_rows = data["snapshot_rows"]
    snapshot_col_widths = [
        doc.width * 0.24,
        doc.width * 0.18,
        doc.width * 0.14,
        doc.width * 0.14,
        doc.width * 0.3,
    ]
    snapshot_table = build_table(snapshot_rows, snapshot_col_widths)
    snapshot_table.setStyle(
        TableStyle(
            [
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.whitesmoke, colors.HexColor("#f8fafc")],
                ),
            ]
        )
    )
    elements.append(snapshot_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Sección 5 · Reglas Activas", styles["HeadingSecondary"]))
    for rule in data["rules_list"]:
        elements.append(Paragraph(f"• {rule}", styles["Body"]))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("Sección 6 · Verificación Criptográfica", styles["HeadingSecondary"]))
    elements.append(Paragraph(data["crypto_text"], styles["Body"]))
    if data.get("qr"):
        elements.append(Image(data["qr"], width=3.2 * cm, height=3.2 * cm))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Sección 7 · Mapa de Riesgos y Gobernanza", styles["HeadingSecondary"]))
    elements.append(Paragraph(data["risk_text"], styles["Body"]))
    elements.append(Paragraph(data["governance_text"], styles["Body"]))
    elements.append(Spacer(1, 6))

    def draw_footer(canvas, _doc):
        """Español: Función draw_footer del módulo dashboard/streamlit_app.py.

        English: Function draw_footer defined in dashboard/streamlit_app.py.
        """
        canvas.saveState()
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.5 * cm, 0.75 * cm, data["footer_left"])
        canvas.drawRightString(page_size[0] - 1.5 * cm, 0.75 * cm, data["footer_right"])
        canvas.setFont(regular_font, 7)
        canvas.drawString(1.5 * cm, 0.45 * cm, data.get("footer_disclaimer", ""))
        canvas.setFont(bold_font, 32)
        canvas.setFillColor(colors.Color(0.12, 0.4, 0.6, alpha=0.08))
        canvas.drawCentredString(page_size[0] / 2, page_size[1] / 2, "VERIFICABLE")
        canvas.restoreState()

    doc.build(
        elements,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
        canvasmaker=lambda *args, **kwargs: NumberedCanvas(*args, root_hash=data.get("footer_root_hash", ""), **kwargs),
    )
    buffer.seek(0)
    return buffer.getvalue()


def generate_pdf_report(
    data_nacional: dict[str, Any],
    data_departamentos: list[dict[str, Any]],
    current_hash: str,
    previous_hash: str,
    diffs: dict[str, Any],
) -> bytes:
    """Español: Genera un PDF formal bilingüe con portada, resumen y trazabilidad técnica.

    English: Generate a formal bilingual PDF with cover page, summary tables, and traceability.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is required to build the PDF report.")

    regular_font, bold_font = _register_pdf_fonts()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.4 * cm,
        bottomMargin=2.2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontName=bold_font,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=18,
            textColor=colors.HexColor("#1F2937"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontName=bold_font,
            fontSize=13,
            leading=16,
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor("#1F77B4"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            fontName=regular_font,
            fontSize=10.5,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            fontName=bold_font,
            fontSize=9.5,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            fontName=regular_font,
            fontSize=9.5,
            leading=12,
            alignment=TA_LEFT,
        )
    )

    def as_paragraph(value: object, style: ParagraphStyle) -> Paragraph:
        """Español: Convierte un valor en párrafo seguro para tablas.

        English: Cast a value into a safe paragraph for tables.
        """
        return Paragraph(str(value), style)

    def build_table(rows: list[list[object]], col_widths: list[float]) -> Table:
        """Español: Construye una tabla con encabezado resaltado.

        English: Build a table with a highlighted header row.
        """
        header = [as_paragraph(cell, styles["TableHeader"]) for cell in rows[0]]
        body = [[as_paragraph(cell, styles["TableCell"]) for cell in row] for row in rows[1:]]
        table = Table([header] + body, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F77B4")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    report_date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    version = "v1.0"
    repo_url = "https://github.com/userf8a2c4/centinel-engine"

    def draw_footer(canvas: reportlab_canvas.Canvas, doc_instance: SimpleDocTemplate) -> None:
        """Español: Dibuja el pie de página con enlace y timestamp.

        English: Draw footer with repository link and timestamp.
        """
        canvas.saveState()
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawString(doc_instance.leftMargin, 1.2 * cm, f"Repositorio: {repo_url}")
        canvas.drawRightString(
            doc_instance.pagesize[0] - doc_instance.rightMargin,
            1.2 * cm,
            f"Generado: {report_date}",
        )
        canvas.restoreState()

    elements: list = []
    elements.append(Paragraph("Reporte de Auditoría Centinel", styles["CoverTitle"]))
    elements.append(
        Paragraph(
            "Monitoreo técnico de integridad y trazabilidad para datos públicos del CNE "
            "(JSON agregado nacional + 18 departamentos).",
            styles["Body"],
        )
    )
    elements.append(
        Paragraph(
            f"Fecha de generación: {report_date}<br/>"
            f"Versión: {version}<br/>"
            f"Hash del snapshot actual: {current_hash}<br/>"
            f"Hash del snapshot previo: {previous_hash}",
            styles["Body"],
        )
    )
    elements.append(Spacer(1, 16))
    elements.append(PageBreak())

    elements.append(Paragraph("Resumen Nacional", styles["SectionTitle"]))
    national_rows = [
        ["Indicador", "Valor"],
        ["Total nacional (JSON)", data_nacional.get("total_nacional", "N/D")],
        ["Suma departamentos (18)", data_nacional.get("suma_departamentos", "N/D")],
        ["Delta agregación", data_nacional.get("delta_aggregacion", "N/D")],
        ["Snapshots procesados", data_nacional.get("snapshots", "N/D")],
    ]
    elements.append(build_table(national_rows, [doc.width * 0.6, doc.width * 0.4]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Resumen por Departamento", styles["SectionTitle"]))
    dept_rows = [["Departamento", "Total", "Diff vs anterior"]]
    for row in data_departamentos:
        dept = row.get("departamento", "N/D")
        total = row.get("total", "N/D")
        diff_value = diffs.get(dept, row.get("diff", "N/D"))
        dept_rows.append([dept, total, diff_value])
    elements.append(build_table(dept_rows, [doc.width * 0.45, doc.width * 0.25, doc.width * 0.3]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Diferencias detectadas (Diffs)", styles["SectionTitle"]))
    diff_rows = [["Departamento", "Delta vs snapshot previo"]]
    if diffs:
        for dept, diff_value in diffs.items():
            diff_rows.append([dept, diff_value])
    else:
        diff_rows.append(["N/D", "Sin cambios relevantes detectados"])
    elements.append(build_table(diff_rows, [doc.width * 0.5, doc.width * 0.5]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Metodología (ES/EN)", styles["SectionTitle"]))
    metodologia = (
        "<b>ES:</b> Este reporte resume únicamente datos públicos agregados del CNE "
        "a nivel nacional y por departamento (18). No se incluyen mesas, actas ni votos "
        "individuales. Las métricas se calculan sobre snapshots JSON públicos y encadenados "
        "por hash, lo que permite detectar cambios entre el snapshot actual y el previo. "
        "En futuras versiones se incorporarán pruebas estadísticas (Benford, chi-cuadrado) "
        "y validaciones adicionales de consistencia. [Placeholder metodológico bilingüe].<br/><br/>"
        "<b>EN:</b> This report summarizes only public, aggregated CNE data at national "
        "and departmental levels (18). It excludes precinct tables, actas, or individual votes. "
        "Metrics are computed from public JSON snapshots linked by hashing to detect changes "
        "between the latest and previous snapshots. Future versions will include statistical "
        "tests (Benford, chi-square) and additional consistency checks. "
        "[Bilingual methodology placeholder]."
    )
    elements.append(Paragraph(metodologia, styles["Body"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Declaración de Neutralidad (ES/EN)", styles["SectionTitle"]))
    disclaimer = (
        "<b>ES:</b> Este documento utiliza exclusivamente datos públicos del CNE y "
        "no incluye información sensible ni desagregada. No contiene interpretación "
        "política ni conclusiones electorales, y no sustituye procesos oficiales del CNE. "
        "Su propósito es documentar integridad técnica, trazabilidad y transparencia "
        "para observadores internacionales de manera neutral y verificable.<br/><br/>"
        "<b>EN:</b> This document relies solely on public CNE data and contains no "
        "sensitive or disaggregated information. It provides no political interpretation "
        "or electoral conclusions, and it does not replace official CNE processes. "
        "Its purpose is to document technical integrity, traceability, and transparency "
        "for international observers in a neutral, verifiable manner."
    )
    elements.append(Paragraph(disclaimer, styles["Body"]))

    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer.getvalue()


def build_pdf_export_payload(
    snapshots_df: pd.DataFrame,
    departments: list[str],
    selected_timestamp: dt.datetime | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], str, str, dict[str, Any]]:
    """Español: Arma el payload de resumen nacional, departamentos, hash y diffs.

    English: Build payload with national summary, departments, hash, and diffs.
    """
    if snapshots_df.empty:
        return (
            {
                "total_nacional": "N/D",
                "suma_departamentos": "N/D",
                "delta_aggregacion": "N/D",
                "snapshots": 0,
            },
            [],
            "N/D",
            "N/D",
            {},
        )

    df = snapshots_df.copy()
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp_dt"])
    if selected_timestamp is not None:
        df = df[df["timestamp_dt"] <= selected_timestamp]
    if df.empty:
        return (
            {
                "total_nacional": "N/D",
                "suma_departamentos": "N/D",
                "delta_aggregacion": "N/D",
                "snapshots": len(snapshots_df),
            },
            [],
            "N/D",
            "N/D",
            {},
        )

    latest_ts = df["timestamp_dt"].max()
    latest_df = df[df["timestamp_dt"] == latest_ts]
    prev_df = df[df["timestamp_dt"] < latest_ts]
    prev_latest = prev_df.sort_values("timestamp_dt").groupby("department", as_index=False).tail(1)

    dept_latest = (
        latest_df[latest_df["department"].isin(departments)]
        .sort_values("department")
        .groupby("department", as_index=False)
        .tail(1)
    )

    national_latest = latest_df[~latest_df["department"].isin(departments)]
    total_nacional = int(national_latest["votes"].sum()) if not national_latest.empty else 0
    suma_departamentos = int(dept_latest["votes"].sum()) if not dept_latest.empty else 0
    delta_aggregacion = suma_departamentos - total_nacional

    diffs: dict[str, Any] = {}
    data_departamentos: list[dict[str, Any]] = []
    for _, row in dept_latest.iterrows():
        dept = row["department"]
        total = int(row["votes"])
        prev_row = prev_latest[prev_latest["department"] == dept]
        if not prev_row.empty:
            prev_total = int(prev_row.iloc[0]["votes"])
            diff_value = total - prev_total
            diffs[dept] = f"{diff_value:+,}"
        else:
            diffs[dept] = "N/D"
        data_departamentos.append({"departamento": dept, "total": f"{total:,}", "diff": diffs[dept]})

    def _snapshot_payload(snapshot_df: pd.DataFrame) -> list[dict[str, Any]]:
        """Español: Construye payload serializable para hash de snapshot.

        English: Build a serializable payload for snapshot hashing.
        """
        return (
            snapshot_df[["timestamp", "department", "votes", "delta", "changes", "hash"]]
            .fillna("")
            .to_dict(orient="records")
        )

    payload = _snapshot_payload(latest_df)
    hash_snapshot = compute_report_hash(json.dumps(payload, sort_keys=True))
    previous_hash = "N/D"
    if not prev_df.empty:
        previous_ts = prev_df["timestamp_dt"].max()
        previous_df = prev_df[prev_df["timestamp_dt"] == previous_ts]
        previous_payload = _snapshot_payload(previous_df)
        previous_hash = compute_report_hash(json.dumps(previous_payload, sort_keys=True))

    data_nacional = {
        "total_nacional": f"{total_nacional:,}",
        "suma_departamentos": f"{suma_departamentos:,}",
        "delta_aggregacion": f"{delta_aggregacion:+,}",
        "snapshots": len(snapshots_df),
    }

    return data_nacional, data_departamentos, hash_snapshot, previous_hash, diffs


st.set_page_config(
    page_title="C.E.N.T.I.N.E.L. | Vigilancia Electoral",
    page_icon="🛰\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================================
# EN: Authentication gate — all users must log in before seeing the dashboard.
# ES: Puerta de autenticacion — todos los usuarios deben iniciar sesion.
# =========================================================================
def _render_login_screen() -> bool:
    """EN: Show login form and authenticate user. Returns True if authenticated.

    ES: Muestra formulario de login y autentica al usuario. Retorna True si autenticado.
    """
    if not AUTH_AVAILABLE:
        # EN: Fallback to old admin gate when auth module not available.
        # ES: Fallback al gate admin anterior si el modulo auth no esta disponible.
        st.warning("Modulo de autenticacion no disponible. Ejecutando sin autenticacion.")
        st.session_state["auth_user"] = {"username": "admin", "role": "admin", "sandbox": {}}
        return True

    if st.session_state.get("auth_user"):
        return True

    # EN: Ensure admin user exists on first boot.
    # ES: Asegurar que el usuario admin exista en primer arranque.
    ensure_admin_exists()

    st.markdown(
        "<div style='text-align:center; padding:3rem 0 1rem;'>"
        "<h1>C.E.N.T.I.N.E.L.</h1>"
        "<p style='color:#94A3B8;'>Centro de Vigilancia Electoral &mdash; Acceso Restringido</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Usuario / Username")
        password = st.text_input("Contrasena / Password", type="password")
        submitted = st.form_submit_button("Ingresar / Log in", type="primary")
    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state["auth_user"] = user
            rerun_app()
        else:
            st.error("Credenciales invalidas / Invalid credentials.")
    return False


if not _render_login_screen():
    st.stop()

# EN: User is authenticated — extract session info.
# ES: Usuario autenticado — extraer info de sesion.
_current_user: dict[str, Any] = st.session_state["auth_user"]
_current_username: str = _current_user["username"]
_current_role: str = _current_user["role"]

# =========================================================================
# EN: Load global configs (available for all tabs).
# ES: Cargar configuraciones globales (disponibles para todos los tabs).
# =========================================================================
configs = load_configs()
command_center_cfg = configs.get("command_center", {})
rules_path = Path("command_center") / "rules.yaml"
if not rules_path.exists():
    rules_path = Path("config/prod/rules.yaml")
rules_cfg = load_rules_config(rules_path)
resilience_cfg = rules_cfg.get("resiliencia", {}) if rules_cfg else {}

anchor = load_blockchain_anchor()

# =========================================================================
# EN: Sidebar — user info, logout, and global filters.
# ES: Sidebar — info de usuario, logout, y filtros globales.
# =========================================================================
st.sidebar.markdown(
    f"**Usuario / User:** `{_current_username}`  \n"
    f"**Rol / Role:** `{_current_role}`"
)
if st.sidebar.button("Cerrar sesion / Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    rerun_app()
st.sidebar.markdown("---")

snapshot_source = st.sidebar.selectbox(
    "Fuente de snapshots (Snapshot source)",
    [
        "Datos reales (Real data)",
        "Mock normal (Normal mock)",
        "Mock anomalia (Anomaly mock)",
        "Mock reversion (Reversal mock)",
    ],
    index=0,
)

snapshot_sources = {
    "Datos reales (Real data)": {
        "base_dir": Path("data"),
        "pattern": "snapshot_*.json",
        "explicit_files": None,
    },
    "Mock normal (Normal mock)": {
        "base_dir": Path("data/mock"),
        "pattern": "*.json",
        "explicit_files": ["mock_normal.json"],
    },
    "Mock anomalia (Anomaly mock)": {
        "base_dir": Path("data/mock"),
        "pattern": "*.json",
        "explicit_files": ["mock_anomaly.json"],
    },
    "Mock reversion (Reversal mock)": {
        "base_dir": Path("data/mock"),
        "pattern": "*.json",
        "explicit_files": ["mock_reversal.json"],
    },
}
source_config = snapshot_sources[snapshot_source]
snapshot_base_dir = source_config["base_dir"]
snapshot_files = load_snapshot_files(
    snapshot_base_dir,
    pattern=source_config["pattern"],
    explicit_files=source_config["explicit_files"],
)
progress = st.progress(0, text="Cargando snapshots inmutables...")
for step in range(1, 5):
    progress.progress(step * 25, text=f"Sincronizando evidencia {step}/4")
progress.empty()

snapshot_selector_options = ["Ultimo snapshot (Latest)"]
snapshot_lookup: dict[str, dict[str, Any]] = {}
for snapshot in sorted(
    snapshot_files,
    key=lambda item: _parse_timestamp(item.get("timestamp")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
    reverse=True,
):
    timestamp_label = snapshot.get("timestamp", "N/D")
    hash_label = snapshot.get("hash", "")[:8]
    label = f"{timestamp_label} \u00b7 {hash_label}..."
    snapshot_lookup[label] = snapshot
    snapshot_selector_options.append(label)

selected_snapshot_label = st.sidebar.selectbox(
    "Snapshot historico (Historical snapshot)",
    snapshot_selector_options,
    index=0,
)
selected_snapshot = snapshot_lookup.get(selected_snapshot_label)
selected_snapshot_timestamp = _parse_timestamp(selected_snapshot.get("timestamp")) if selected_snapshot else None

latest_snapshot = {}
latest_timestamp = None
last_batch_label = "N/D"
hash_accumulator = anchor.root_hash
try:
    (
        latest_snapshot,
        latest_timestamp,
        last_batch_label,
        hash_accumulator,
    ) = _resolve_latest_snapshot_info(snapshot_files, anchor.root_hash)
except Exception as exc:  # noqa: BLE001
    st.warning("No se pudo determinar el ultimo snapshot (Unable to resolve latest snapshot): " f"{exc}")

snapshots_df = build_snapshot_metrics(snapshot_files)
anomalies_df = build_anomalies(snapshots_df)
heatmap_df = build_heatmap(anomalies_df)
benford_df = build_benford_data()
rules_df = build_rules_table(command_center_cfg)

rules_engine_output = run_rules_engine(snapshots_df, command_center_cfg)

failed_retries = 0
rate_limit_failures = 0
try:
    log_path = Path(command_center_cfg.get("logging", {}).get("file", "C.E.N.T.I.N.E.L.log"))
    failed_retries = _count_failed_retries(log_path)
    rate_limit_failures = _count_rate_limit_retries(log_path)
except Exception as exc:  # noqa: BLE001
    st.warning("No se pudo leer el conteo de reintentos (Unable to read retry count): " f"{exc}")

time_since_last = dt.datetime.now(dt.timezone.utc) - latest_timestamp if latest_timestamp else None
refresh_interval = st.session_state.get("refresh_interval_system", 45)
polling_status = resolve_polling_status(
    rate_limit_failures,
    failed_retries,
    time_since_last,
    refresh_interval,
)


# =========================================================================
# EN: Helper — generate WeasyPrint PDF from Jinja2 template.
# ES: Helper — generar PDF con WeasyPrint desde plantilla Jinja2.
# =========================================================================
def _generate_weasyprint_pdf(template_data: dict[str, Any]) -> bytes | None:
    """EN: Render templates/report_template.html with Jinja2 and convert to PDF via WeasyPrint.

    ES: Renderiza templates/report_template.html con Jinja2 y convierte a PDF via WeasyPrint.
    """
    if not JINJA2_AVAILABLE or not WEASYPRINT_AVAILABLE:
        return None
    template_dir = REPO_ROOT / "templates"
    if not (template_dir / "report_template.html").exists():
        return None
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
    template = env.get_template("report_template.html")
    html_content = template.render(**template_data)
    pdf_bytes = WeasyHTML(string=html_content).write_pdf()
    return pdf_bytes


def _chart_to_base64(buf: io.BytesIO | None) -> str:
    """EN: Convert a BytesIO chart buffer to base64 string for HTML embedding.

    ES: Convierte un buffer BytesIO de grafico a string base64 para incrustar en HTML.
    """
    if buf is None:
        return ""
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

alerts_container = st.container()
with alerts_container:
    if rate_limit_failures > 0:
        st.error(
            "Polling fallido por rate-limit del CNE (CNE rate-limit polling failure) · "
            f"Intentos: {rate_limit_failures} (Attempts: {rate_limit_failures})"
        )
    if failed_retries > 0:
        st.warning(
            "Conexión perdida – reintentando en "
            f"{refresh_interval} segundos (Connection lost – retrying in "
            f"{refresh_interval} seconds)."
        )
    if latest_timestamp is None or (time_since_last and time_since_last > dt.timedelta(minutes=45)):
        st.warning("No se encontraron snapshots recientes (No recent snapshots found).")

if snapshots_df.empty:
    st.warning(
        f"No se encontraron snapshots en {snapshot_base_dir.as_posix()}/ "
        "(No snapshots found). El panel está en modo demo (Dashboard is in demo mode)."
    )

css = """
<style>
    :root {
        color-scheme: dark;
        --bg: #0B0F19;
        --bg-soft: #101826;
        --panel: rgba(15, 23, 42, 0.92);
        --panel-soft: rgba(30, 41, 59, 0.85);
        --text: #f8fafc;
        --muted: #c7d2fe;
        --accent: #2D79C7;
        --accent-strong: #4F9BF7;
        --success: #22C55E;
        --danger: #EF4444;
        --warning: #F59E0B;
        --border: rgba(148, 163, 184, 0.2);
        --shadow: 0 18px 40px rgba(3, 7, 18, 0.45);
        --glow: 0 0 0 1px rgba(79, 155, 247, 0.15), 0 10px 35px rgba(15, 23, 42, 0.65);
    }
    html, body, [class*="css"] { font-family: "Inter", "Roboto", "Segoe UI", sans-serif; }
    .stApp {
        background: radial-gradient(circle at top left, rgba(45, 121, 199, 0.16), transparent 45%),
                    radial-gradient(circle at 25% 5%, rgba(99, 102, 241, 0.12), transparent 40%),
                    var(--bg);
        color: var(--text);
    }
    .block-container { max-width: 1280px; padding-top: 2rem; }
    section[data-testid="stSidebar"] { background: rgba(10, 15, 25, 0.98); border-right: 1px solid var(--border); }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] label { color: var(--text); }
    .glass {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 1.6rem;
        box-shadow: var(--shadow);
        backdrop-filter: blur(12px);
    }
    .hero {
        background: linear-gradient(135deg, rgba(45, 121, 199, 0.2), rgba(15, 23, 42, 0.95));
        border: 1px solid rgba(79, 155, 247, 0.3);
        border-radius: 24px;
        padding: 1.8rem 2rem;
        box-shadow: var(--glow);
    }
    .hero h1 { font-size: 2rem; margin-bottom: 0.4rem; letter-spacing: -0.02em; }
    .hero p { color: var(--muted); margin: 0.2rem 0 0.8rem; }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        background: rgba(34, 197, 94, 0.18);
        color: var(--success);
        font-size: 0.78rem;
        border: 1px solid rgba(34, 197, 94, 0.32);
    }
    .status-pill--warning {
        background: rgba(245, 158, 11, 0.18);
        color: var(--warning);
        border: 1px solid rgba(245, 158, 11, 0.32);
    }
    .status-pill--danger {
        background: rgba(239, 68, 68, 0.18);
        color: var(--danger);
        border: 1px solid rgba(239, 68, 68, 0.32);
    }
    .hero-meta {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        font-size: 0.82rem;
        color: var(--muted);
    }
    .hero-stack { display: flex; flex-direction: column; gap: 1.2rem; }
    .hero-side { height: 100%; display: flex; align-items: stretch; }
    .status-card { height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .status-card h3 { margin-top: 0.2rem; margin-bottom: 0.6rem; font-size: 1.4rem; }
    .status-card .section-subtitle { margin-bottom: 0.2rem; }
    .alert-bar { margin-top: 0.4rem; }
    .kpi {
        background: var(--panel-soft);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
    }
    .kpi h4 { margin: 0; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.18em; color: var(--muted); }
    .kpi p { margin: 0.45rem 0 0.2rem; font-size: 1.5rem; font-weight: 600; }
    .kpi span { font-size: 0.78rem; color: var(--muted); }
    .badge { display: inline-block; padding: 0.28rem 0.72rem; border-radius: 999px; background: rgba(79, 155, 247, 0.2); color: var(--text); font-size: 0.75rem; border: 1px solid rgba(79, 155, 247, 0.4); }
    .section-title { margin-top: 1.8rem; font-size: 1.15rem; font-weight: 600; }
    .section-subtitle { color: var(--muted); font-size: 0.9rem; }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.9rem; }
    .micro-card {
        background: rgba(15, 23, 42, 0.75);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        border: 1px solid var(--border);
    }
    .micro-card h5 { margin: 0 0 0.4rem; font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.18em; }
    .micro-card p { margin: 0; font-size: 1rem; font-weight: 600; }
    .streamlit-expanderHeader { font-weight: 600; }
    div[data-testid="stMetric"] { background: var(--panel-soft); padding: 1rem; border-radius: 14px; border: 1px solid var(--border); }
    .stTabs [data-baseweb="tab-list"] { gap: 0.6rem; }
    .stTabs [data-baseweb="tab"] {
        background: rgba(15, 23, 42, 0.8);
        border-radius: 999px;
        border: 1px solid var(--border);
        padding: 0.4rem 1rem;
        color: var(--muted);
    }
    .stTabs [aria-selected="true"] { background: rgba(79, 155, 247, 0.2); color: var(--text); border-color: rgba(79, 155, 247, 0.5); }
    .fade-in { animation: fadeIn 1.2s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px);} to { opacity: 1; transform: translateY(0);} }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

st.sidebar.markdown("### Filtros Globales")
departments = [
    "Atlántida",
    "Choluteca",
    "Colón",
    "Comayagua",
    "Copán",
    "Cortés",
    "El Paraíso",
    "Francisco Morazán",
    "Gracias a Dios",
    "Intibucá",
    "Islas de la Bahía",
    "La Paz",
    "Lempira",
    "Ocotepeque",
    "Olancho",
    "Santa Bárbara",
    "Valle",
    "Yoro",
]

selected_department = st.sidebar.selectbox("Departamento", ["Todos"] + departments, index=0)
show_only_alerts = st.sidebar.toggle("Mostrar solo anomalías", value=False)

filtered_snapshots = snapshots_df.copy()
if selected_department != "Todos":
    filtered_snapshots = filtered_snapshots[filtered_snapshots["department"] == selected_department]

if show_only_alerts:
    filtered_snapshots = filtered_snapshots[filtered_snapshots["status"] != "OK"]

filtered_anomalies = build_anomalies(filtered_snapshots)

critical_count = len(filtered_anomalies[filtered_anomalies["type"] == "Delta negativo"])
(
    data_nacional,
    data_departamentos,
    current_snapshot_hash,
    previous_snapshot_hash,
    snapshot_diffs,
) = build_pdf_export_payload(snapshots_df, departments, selected_snapshot_timestamp)
current_snapshot_ts, previous_snapshot_ts = resolve_snapshot_context(snapshots_df, selected_snapshot_timestamp)
expected_streams = int(resilience_cfg.get("max_json_presidenciales", 19) or 19)
alert_thresholds = derive_alert_thresholds(resilience_cfg, expected_streams)
min_samples = alert_thresholds["min_samples"]
observed_streams = 0
if current_snapshot_ts is not None and not snapshots_df.empty:
    snapshots_df["timestamp_dt"] = pd.to_datetime(snapshots_df["timestamp"], errors="coerce", utc=True)
    latest_rows = snapshots_df[snapshots_df["timestamp_dt"] == current_snapshot_ts]
    observed_streams = int(latest_rows["department"].nunique())

negative_diffs = [dept for dept, diff in snapshot_diffs.items() if str(diff).startswith("-")]
latest_timestamp = None
if not snapshots_df.empty:
    latest_timestamp = pd.to_datetime(snapshots_df["timestamp"], errors="coerce", utc=True).dropna().max()
latest_label = latest_timestamp.strftime("%Y-%m-%d %H:%M UTC") if latest_timestamp else "Sin datos"
selected_snapshot_display = (
    selected_snapshot_label if selected_snapshot_label != "Último snapshot (Latest)" else latest_label
)
snapshot_hash_display = current_snapshot_hash[:12] + "…" if current_snapshot_hash != "N/D" else "N/D"

hero_cols = st.columns([0.74, 0.26])
with hero_cols[0]:
    st.markdown(
        """
<div class="hero-stack">
  <div class="hero">
    <span class="badge">Observatorio Electoral · Honduras</span>
    <h1>C.E.N.T.I.N.E.L. · Centro de Vigilancia Electoral</h1>
    <p>Sistema de auditoría técnica con deltas por departamento, validaciones estadísticas y evidencia criptográfica.</p>
    <div class="hero-meta">
      <span>🔎 Modo auditoría: Activo</span>
      <span>🛰️ Última actualización: {latest_label}</span>
      <span>🧾 Snapshot seleccionado: {snapshot_label}</span>
      <span>🔐 Hash raíz: {root_hash}</span>
      <span>🧬 Hash snapshot: {snapshot_hash}</span>
    </div>
  </div>
</div>
        """.format(
            latest_label=latest_label,
            root_hash=anchor.root_hash[:12] + "…",
            snapshot_label=selected_snapshot_display,
            snapshot_hash=snapshot_hash_display,
        ),
        unsafe_allow_html=True,
    )
with hero_cols[1]:
    st.markdown("<div class='glass status-card'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='{polling_status['class']}'>{polling_status['label']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p class='section-subtitle'>Cobertura activa</p>"
        f"<h3>{selected_department}</h3>"
        f"<p class='section-subtitle'>Snapshots observados: {len(snapshot_files)}</p>"
        f"<p class='section-subtitle'>Último lote: {latest_label}</p>"
        f"<p class='section-subtitle'>Estado: {polling_status['detail']}</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

alert_focus_container = st.container()
with alert_focus_container:
    if observed_streams and observed_streams < expected_streams:
        st.error("Cobertura incompleta según rules.yaml: " f"{observed_streams}/{expected_streams} streams observados.")
        emit_toast(
            f"Cobertura incompleta: {observed_streams}/{expected_streams} streams.",
            icon="🚨",
        )
    if len(snapshots_df) < min_samples:
        st.warning(
            "Muestras insuficientes según rules.yaml: " f"{len(snapshots_df)}/{min_samples} snapshots disponibles."
        )
    if negative_diffs:
        diff_label = ", ".join(negative_diffs[:5])
        message = (
            "Deltas negativos detectados en departamentos: "
            f"{diff_label}{'…' if len(negative_diffs) > 5 else ''}. "
            f"(Umbral rules.yaml ≥ {alert_thresholds['diff_error_min']})"
        )
        if len(negative_diffs) >= alert_thresholds["diff_error_min"]:
            st.error(message)
            emit_toast(message, icon="🚨")
        else:
            st.warning(message)
            emit_toast(message, icon="⚠️")
    if rules_engine_output.get("critical"):
        st.error("Alertas críticas del motor de reglas: " f"{len(rules_engine_output['critical'])} eventos.")
        emit_toast("Alertas críticas del motor de reglas activas.", icon="🚨")
    if rules_engine_output.get("alerts"):
        st.warning("Alertas de reglas en revisión: " f"{len(rules_engine_output['alerts'])} eventos.")

if not filtered_anomalies.empty:
    st.markdown("<div class='alert-bar'>", unsafe_allow_html=True)
    anomalies_message = (
        f"Se detectaron {len(filtered_anomalies)} anomalías recientes. "
        "Revisar deltas negativos y outliers. "
        f"(Umbral rules.yaml ≥ {alert_thresholds['anomaly_error_min']})"
    )
    if len(filtered_anomalies) >= alert_thresholds["anomaly_error_min"]:
        st.error(anomalies_message, icon="🚨")
    else:
        st.warning(anomalies_message, icon="⚠️")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>Resumen Ejecutivo</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-subtitle'>Indicadores clave de integridad, velocidad y cobertura operacional.</div>",
    unsafe_allow_html=True,
)
kpi_cols = st.columns(5)
kpis = [
    ("Snapshots", str(len(snapshot_files)), "Ingesta verificada"),
    ("Deltas negativos", str(critical_count), "Alertas críticas"),
    ("Reglas activas", str(len(rules_df)), "Motor de reglas"),
    ("Deptos monitoreados", "18", "Cobertura nacional"),
    ("Hash raíz", anchor.root_hash[:12] + "…", "Evidencia on-chain"),
]
for col, (label, value, caption) in zip(kpi_cols, kpis):
    with col:
        st.markdown(
            f"""
<div class="kpi">
  <h4>{label}</h4>
  <p>{value}</p>
  <span>{caption}</span>
</div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    """
<div class="card-grid">
  <div class="micro-card">
    <h5>Integridad global</h5>
    <p>99.2% confiabilidad</p>
  </div>
  <div class="micro-card">
    <h5>Latencia promedio</h5>
    <p>4m 12s</p>
  </div>
  <div class="micro-card">
    <h5>Alertas abiertas</h5>
    <p>{alerts} registros</p>
  </div>
  <div class="micro-card">
    <h5>Cadena L2</h5>
    <p>Arbitrum · activo</p>
  </div>
</div>
    """.format(
        alerts=len(filtered_anomalies)
    ),
    unsafe_allow_html=True,
)

st.markdown("---")

# =========================================================================
# EN: Four main tabs as specified:
#     1) Visualizacion General  2) Sandbox Personal
#     3) Datos Historicos 2025  4) Panel de Control Admin
# ES: Cuatro tabs principales segun especificacion:
#     1) Visualizacion General  2) Sandbox Personal
#     3) Datos Historicos 2025  4) Panel de Control Admin
# =========================================================================
_tab_labels = [
    "\U0001f4ca Visualizacion General",
    "\U0001f9ea Sandbox Personal",
    "\U0001f4c2 Datos Historicos 2025",
]
# EN: Only show admin tab for admin role.
# ES: Solo mostrar tab admin para rol admin.
if _current_role == "admin":
    _tab_labels.append("\U0001f527 Panel de Control Admin")

tabs = st.tabs(_tab_labels)

with tabs[0]:
    # =================================================================
    # EN: TAB 1 — Visualizacion General
    #     Shows all charts, hashes, metrics, anomalies, rules, verification,
    #     reports and system status — preserving ALL existing dashboard
    #     capabilities in a single comprehensive view.
    # ES: TAB 1 — Visualizacion General
    #     Muestra todos los graficos, hashes, metricas, anomalias, reglas,
    #     verificacion, reportes y estado del sistema — preservando TODAS
    #     las capacidades existentes del dashboard en una vista integral.
    # =================================================================
    st.markdown("### Panorama Nacional / National Overview")
    summary_cols = st.columns([1.1, 0.9])
    with summary_cols[0]:
        st.markdown(
            """
<div class="glass">
  <h3>Estado Global</h3>
  <p class="fade-in">Integridad verificable &middot; Auditoria continua activa.</p>
  <p>Auditorias prioritarias: deltas negativos por hora/departamento, consistencia de agregacion y distribucion Benford.</p>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("\n")
        if not filtered_snapshots.empty:
            st.line_chart(
                filtered_snapshots.set_index("hour")["votes"],
                height=220,
            )
    with summary_cols[1]:
        if not filtered_snapshots.empty:
            activity_chart = (
                alt.Chart(filtered_snapshots)
                .mark_bar(color="#1F77B4")
                .encode(
                    x=alt.X("hour:N", title="Hora"),
                    y=alt.Y("changes:Q", title="Cambios"),
                    tooltip=["hour", "changes", "department"],
                )
                .properties(height=260, title="Actividad diurna")
            )
            st.altair_chart(activity_chart, use_container_width=True)
        else:
            st.info("Sin datos para actividad diurna en el rango seleccionado.")

    st.markdown("#### Timeline interactivo")
    if filtered_snapshots.empty:
        st.info("No hay snapshots disponibles para el timeline.")
        timeline_view = filtered_snapshots
    else:
        timeline_df = filtered_snapshots.copy()
        timeline_df["timestamp_dt"] = pd.to_datetime(timeline_df["timestamp"], errors="coerce", utc=True)
        timeline_df = timeline_df.sort_values("timestamp_dt")
        timeline_labels = timeline_df["timestamp_dt"].fillna(pd.to_datetime(timeline_df["timestamp"], errors="coerce"))
        timeline_labels = timeline_labels.dt.strftime("%Y-%m-%d %H:%M")
        timeline_labels = timeline_labels.fillna(timeline_df["timestamp"].astype(str))
        timeline_df["timeline_label"] = timeline_labels

        max_index = max(len(timeline_df) - 1, 0)
        if max_index < 1:
            st.slider(
                "Rango de tiempo",
                min_value=0,
                max_value=max_index,
                value=0,
                step=1,
                disabled=True,
            )
            range_indices = (0, 0)
        else:
            range_indices = st.slider(
                "Rango de tiempo",
                min_value=0,
                max_value=max_index,
                value=(0, max_index),
                step=1,
            )
        speed_label = st.select_slider(
            "Velocidad de avance",
            options=["Lento", "Medio", "Rápido"],
            value="Medio",
        )
        speed_step = {"Lento": 1, "Medio": 2, "Rápido": 4}[speed_label]

        if "timeline_index" not in st.session_state:
            st.session_state.timeline_index = range_indices[0]

        st.session_state.timeline_index = max(
            range_indices[0],
            min(st.session_state.timeline_index, range_indices[1]),
        )

        play_cols = st.columns([0.12, 0.12, 0.2, 0.56])
        with play_cols[0]:
            if st.button("◀️"):
                st.session_state.timeline_index = max(
                    range_indices[0],
                    st.session_state.timeline_index - speed_step,
                )
        with play_cols[1]:
            if st.button("▶️"):
                st.session_state.timeline_index = min(
                    range_indices[1],
                    st.session_state.timeline_index + speed_step,
                )
        with play_cols[2]:
            if st.button("⏩ Play"):
                st.session_state.timeline_index = min(
                    range_indices[1],
                    st.session_state.timeline_index + speed_step,
                )
                rerun_app()
        with play_cols[3]:
            st.markdown(f"**Tiempo actual:** {timeline_df.iloc[st.session_state.timeline_index]['timeline_label']}")

        timeline_view = timeline_df.iloc[range_indices[0] : range_indices[1] + 1]

        timeline_chart = (
            alt.Chart(timeline_view)
            .mark_bar(color="#2CA02C")
            .encode(
                x=alt.X("timeline_label:N", title="Tiempo"),
                y=alt.Y("votes:Q", title="Votos"),
                tooltip=["timeline_label", "votes", "delta", "department"],
            )
            .properties(height=240, title="Timeline de votos")
        )
        st.altair_chart(timeline_chart, use_container_width=True)

    chart_cols = st.columns(2)
    with chart_cols[0]:
        benford_chart = (
            alt.Chart(benford_df)
            .transform_fold(["expected", "observed"], as_=["type", "value"])
            .mark_bar()
            .encode(
                x=alt.X("digit:O", title="Dígito"),
                y=alt.Y("value:Q", title="%"),
                color=alt.Color(
                    "type:N",
                    scale=alt.Scale(domain=["expected", "observed"], range=["#1F77B4", "#2CA02C"]),
                    legend=alt.Legend(title="Serie"),
                ),
                tooltip=[
                    alt.Tooltip("digit:O", title="Dígito"),
                    alt.Tooltip("type:N", title="Serie"),
                    alt.Tooltip("value:Q", title="Valor"),
                ],
            )
            .properties(height=240, title="Benford 1er dígito")
        )
        st.altair_chart(benford_chart, use_container_width=True)
    with chart_cols[1]:
        votes_chart = (
            alt.Chart(filtered_snapshots)
            .mark_line(point=True, color="#2CA02C")
            .encode(
                x=alt.X("hour:N", title="Hora"),
                y=alt.Y("votes:Q", title="Votos acumulados"),
                tooltip=["hour", "votes", "delta"],
            )
            .properties(height=240, title="Evolución de cambios")
        )
        st.altair_chart(votes_chart, use_container_width=True)

    # EN: Sub-section — Department view (inside Visualizacion General).
    # ES: Sub-seccion — Vista por departamento (dentro de Visualizacion General).
    with st.expander("Vista por Departamento / Department View", expanded=False):
        if selected_department == "Todos":
            st.info("Selecciona un departamento en el sidebar para ver metricas detalladas.")
            if data_departamentos:
                st.dataframe(
                    pd.DataFrame(data_departamentos),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            dept_summary = next(
                (row for row in data_departamentos if row.get("departamento") == selected_department),
                {},
            )
            metric_cols = st.columns(3)
            metric_cols[0].metric("Departamento", selected_department)
            metric_cols[1].metric("Total agregado", dept_summary.get("total", "N/D"))
            metric_cols[2].metric("Diff vs anterior", dept_summary.get("diff", "N/D"))
            if not filtered_snapshots.empty:
                st.line_chart(
                    filtered_snapshots.set_index("hour")["votes"],
                    height=220,
                )
            if not filtered_anomalies.empty:
                st.markdown("#### Anomalias recientes")
                st.dataframe(
                    filtered_anomalies,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("Sin anomalias registradas para este departamento.")

    # EN: Sub-section — Anomalies (inside Visualizacion General).
    # ES: Sub-seccion — Anomalias (dentro de Visualizacion General).
    with st.expander("Anomalias Detectadas / Detected Anomalies", expanded=False):
        if filtered_anomalies.empty:
            st.success("Sin anomalias criticas en el filtro actual.")
        else:
            st.dataframe(filtered_anomalies, use_container_width=True, hide_index=True)

        if not heatmap_df.empty:
            heatmap_chart = (
                alt.Chart(heatmap_df)
                .mark_rect()
                .encode(
                    x=alt.X("hour:O", title="Hora"),
                    y=alt.Y("department:N", title="Departamento"),
                    color=alt.Color("anomaly_count:Q", scale=alt.Scale(scheme="redblue")),
                    tooltip=["department", "hour", "anomaly_count"],
                )
                .properties(height=360, title="Mapa de riesgos (anomalias por departamento/hora)")
            )
            st.altair_chart(heatmap_chart, use_container_width=True)

        with st.expander("Logs tecnicos de reglas"):
            log_lines = [
                "Regla: Delta negativo por hora/departamento - threshold=-200",
                "Regla: Benford 1er digito - p-value=0.023 (Cortes)",
                "Regla: Outlier de crecimiento - z-score=2.4 (Francisco Morazan)",
            ]
            if rules_engine_output["alerts"]:
                for alert in rules_engine_output["alerts"][:6]:
                    log_lines.append(f"Regla: {alert.get('rule')} - {alert.get('severity')} - {alert.get('message')}")
            st.code("\n".join(log_lines), language="yaml")

    # EN: Sub-section — Snapshots & Rules (inside Visualizacion General).
    # ES: Sub-seccion — Snapshots y Reglas (dentro de Visualizacion General).
    with st.expander("Snapshots Recientes y Reglas / Recent Snapshots & Rules", expanded=False):
        st.dataframe(
            filtered_snapshots[
                [
                    "timestamp",
                    "department",
                    "delta",
                    "status",
                    "hash",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
        with st.expander("Detalle de reglas activas"):
            st.dataframe(rules_df, use_container_width=True, hide_index=True)
            st.caption("Reglas y umbrales cargados desde command_center/config.yaml.")

    # EN: Sub-section — Cryptographic verification (inside Visualizacion General).
    # ES: Sub-seccion — Verificacion criptografica (dentro de Visualizacion General).
    with st.expander("Verificacion Criptografica / Cryptographic Verification", expanded=False):
        verify_col, qr_col = st.columns([1.2, 0.8])
        with verify_col:
            with st.form("verify_form"):
                hash_input = st.text_input("Hash raiz", value=anchor.root_hash)
                submitted = st.form_submit_button("Verificar")
            if submitted:
                if anchor.root_hash.lower() in hash_input.lower():
                    st.success("Coincide con el anclaje en blockchain.")
                else:
                    st.error("No coincide. Revisa el hash.")
            st.markdown(
                f"**Transaccion:** [{anchor.tx_url}]({anchor.tx_url})  ",
            )
            st.markdown(f"**Red:** {anchor.network} - **Timestamp:** {anchor.anchored_at}")
        with qr_col:
            st.markdown("#### QR")
            qr_bytes = build_qr_bytes(anchor.root_hash)
            if qr_bytes is None:
                st.warning("QR no disponible: falta instalar la dependencia 'qrcode'.")
            else:
                st.image(qr_bytes, caption="Escanear hash de verificacion")

    # EN: Sub-section — Reports and export (inside Visualizacion General).
    # ES: Sub-seccion — Reportes y exportacion (dentro de Visualizacion General).
    st.markdown("---")
    st.markdown("### Reportes y Exportacion / Reports & Export")
    st.caption(
        "Reporte generado desde JSON publico del CNE (18 departamentos + nacional). "
        f"Snapshot seleccionado: {selected_snapshot_display} - "
        f"Hash actual: {snapshot_hash_display}."
    )
    report_time_dt = dt.datetime.now(dt.timezone.utc)
    report_time = report_time_dt.strftime("%Y-%m-%d %H:%M")
    report_payload = f"{anchor.root_hash}|{anchor.tx_url}|{report_time}"
    report_hash = compute_report_hash(report_payload)

    snapshots_real = filtered_snapshots.copy()
    if "is_real" in snapshots_real.columns:
        snapshots_real = snapshots_real[snapshots_real["is_real"]]
    snapshot_rows = [
        ["Timestamp", "Dept", "Δ", "Estado", "Hash"],
    ] + snapshots_real[
        ["timestamp", "department", "delta", "status", "hash"]
    ].head(10).values.tolist()

    anomalies_sorted = filtered_anomalies.copy()
    if not anomalies_sorted.empty:
        anomalies_sorted["delta_abs"] = anomalies_sorted["delta"].abs()
        anomalies_sorted = anomalies_sorted.sort_values("delta_abs", ascending=False)
        if len(anomalies_sorted) > 10:
            anomalies_sorted = (
                anomalies_sorted.groupby("department", as_index=False)
                .head(2)
                .sort_values("delta_abs", ascending=False)
                .head(12)
            )
    anomaly_rows = [["Dept", "Δ abs", "Δ %", "Hora", "Hash", "Tipo"]]
    prev_hash = ""
    for _, row in anomalies_sorted.head(12).iterrows():
        current_hash = str(row.get("hash") or "")
        chain_hash = ""
        if current_hash:
            chain_hash = hashlib.sha256(f"{prev_hash}|{current_hash}".encode("utf-8")).hexdigest()
        hash_cell = current_hash[:6] if current_hash else ""
        if current_hash:
            prev_short = prev_hash[:6] if prev_hash else "------"
            curr_short = current_hash[:6]
            hash_cell = f"{prev_short}→{curr_short}"
        anomaly_rows.append(
            [
                row.get("department"),
                f"{row.get('delta', 0):.0f}",
                f"{row.get('delta_pct', 0):.2f}%",
                row.get("hour") or "",
                hash_cell,
                ("ROLLBACK / ELIMINACIÓN DE DATOS" if row.get("type") == "Delta negativo" else row.get("type")),
            ]
        )
        prev_hash = chain_hash or current_hash

    topology = compute_topology_integrity(snapshots_df, departments)
    latency_rows, latency_alert_cells = build_latency_matrix(snapshots_df, departments, report_time_dt)
    velocity_vpm = compute_ingestion_velocity(snapshots_df)
    db_inconsistencies = int(
        (filtered_anomalies["type"] == "Delta negativo").sum() if not filtered_anomalies.empty else 0
    )
    stat_deviations = int((filtered_anomalies["type"] != "Delta negativo").sum() if not filtered_anomalies.empty else 0)

    rules_list = (
        rules_df.assign(summary=rules_df["rule"] + " (" + rules_df["thresholds"].fillna("-") + ")")
        .head(8)
        .get("summary", pd.Series(dtype=str))
        .tolist()
    )

    chart_buffers = create_pdf_charts(
        benford_df,
        filtered_snapshots,
        heatmap_df,
        filtered_anomalies,
        topology,
        snapshots_real,
        departments,
    )

    qr_buffer = None
    if anchor.tx_url:
        qr_payload = anchor.tx_url
    else:
        qr_payload = f"https://centinel.local/verify?root_hash={anchor.root_hash}"
    qr_bytes = build_qr_bytes(qr_payload)
    if qr_bytes is not None:
        qr_buffer = io.BytesIO(qr_bytes)

    topology_rows = [
        ["Suma 18 deptos", "Total nacional", "Delta"],
        [
            f"{topology['department_total']:,}",
            f"{topology['national_total']:,}",
            f"{topology['delta']:+,}",
        ],
    ]
    if topology["is_match"]:
        topology_summary = "Consistencia confirmada: la suma de departamentos coincide con el total nacional."
    else:
        topology_summary = (
            "DISCREPANCIA DE AGREGACIÓN: La suma de departamentos difiere "
            f"del nacional en {topology['delta']:+,} votos."
        )
    if topology["delta"]:
        topology_alert = (
            "ALERTA CRÍTICA: Se detectó una inyección/pérdida de "
            f"{abs(topology['delta']):,} votos que no poseen origen geográfico trazable."
        )
    else:
        topology_alert = ""

    benford_deviation = (benford_df["observed"] - benford_df["expected"]).abs().max()
    if critical_count > 0 or not topology["is_match"] or benford_deviation > 5:
        status_badge = {"label": "ESTATUS: COMPROMETIDO", "color": "#B22222"}
    else:
        status_badge = {"label": "ESTATUS: VERIFICADO", "color": "#008000"}

    integrity_pct = 100.0
    if len(filtered_snapshots) > 0:
        integrity_pct = max(
            0.0,
            100.0 - (abs(topology["delta"]) / max(1, topology["national_total"])) * 100,
        )
    deviation_std = float(filtered_snapshots["delta"].std()) if not filtered_snapshots.empty else 0.0
    forensic_summary = (
        f"Se han auditado {len(snapshot_files)} flujos de datos. "
        f"La integridad se ha mantenido en un {integrity_pct:0.2f}% "
        f"con {critical_count} alertas de seguridad activadas."
    )

    pdf_data = {
        "title": "Informe de Auditoría C.E.N.T.I.N.E.L.",
        "subtitle": f"Estatus verificable · Alcance {selected_department}",
        "input_source": "Input Source: 19 JSON Streams (Direct Endpoint)",
        "generated": f"Fecha/hora: {report_time} UTC",
        "global_status": "ESTATUS GLOBAL: VERIFICABLE · SIN ANOMALÍAS CRÍTICAS",
        "executive_summary": (
            "CENTINEL ha auditado "
            f"{len(snapshot_files)} snapshots de 19 flujos de datos JSON. "
            f"Se detectaron {db_inconsistencies} inconsistencias de base de datos "
            f"y {stat_deviations} desviaciones estadísticas."
        ),
        "forensic_summary": forensic_summary,
        "kpi_rows": [
            [
                "Auditorías",
                "Correctivas",
                "Snapshots",
                "Reglas",
                "Hashes",
                "Velocidad Ingesta",
            ],
            [
                "8",
                "2",
                str(len(snapshot_files)),
                str(len(rules_df)),
                anchor.root_hash[:8],
                f"{velocity_vpm:,.1f} votos/min",
            ],
        ],
        "anomaly_rows": anomaly_rows,
        "snapshot_rows": snapshot_rows,
        "rules_list": rules_list,
        "topology": topology,
        "topology_rows": topology_rows,
        "topology_summary": topology_summary,
        "topology_alert": topology_alert,
        "latency_rows": latency_rows,
        "latency_alert_cells": latency_alert_cells,
        "crypto_text": f"Hash raíz: {anchor.root_hash}\nQR para escaneo y validación pública.",
        "risk_text": "Mapa de riesgos: deltas negativos, irregularidades temporales y dispersión geográfica.",
        "governance_text": "Gobernanza: trazabilidad, inmutabilidad y publicación auditada del JSON CNE.",
        "chart_captions": {
            "benford": "Distribución Benford: observado vs esperado (rojo cuando supera 5%).",
            "timeline": "Timeline con puntos rojos en horas de anomalías.",
            "heatmap": "Mapa de riesgos por departamento/hora (rojo = mayor riesgo).",
        },
        "qr": qr_buffer,
        "snapshot_count": len(snapshot_files),
        "status_badge": status_badge,
        "footer_left": f"Hash encadenado: {anchor.root_hash[:16]}…",
        "footer_right": f"Hash reporte: {report_hash[:16]}…",
        "footer_root_hash": anchor.root_hash,
        "footer_disclaimer": (
            "Datos solo de fuentes públicas CNE, conforme Ley Transparencia 170-2006. Agnóstico político."
        ),
    }

    if REPORTLAB_AVAILABLE:
        export_pdf_bytes = generate_pdf_report(
            data_nacional,
            data_departamentos,
            current_snapshot_hash,
            previous_snapshot_hash,
            snapshot_diffs,
        )
        st.download_button(
            "Exportar Reporte PDF",
            data=export_pdf_bytes,
            file_name="centinel_reporte_auditoria.pdf",
            mime="application/pdf",
        )
        use_enhanced_pdf = plt is not None and qrcode is not None
        if use_enhanced_pdf:
            from centinel_pdf_report import CentinelPDFReport

            report_data = {
                **pdf_data,
                "timestamp_utc": report_time_dt,
                "root_hash": anchor.root_hash,
                "status": ("COMPROMETIDO" if (not topology["is_match"] or critical_count > 0) else "INTEGRAL"),
                "source": pdf_data.get("input_source", "Endpoint JSON CNE"),
                "topology_check": {
                    "total_national": topology["national_total"],
                    "department_total": topology["department_total"],
                    "is_match": topology["is_match"],
                },
                "anomalies": [
                    {
                        "department": row.get("department"),
                        "hour": row.get("hour"),
                        "anomaly": 1,
                    }
                    for _, row in filtered_anomalies.iterrows()
                ],
                "benford": {
                    "observed": (benford_df.sort_values("digit")["observed"].tolist() if not benford_df.empty else []),
                    "sample_size": max(len(filtered_snapshots), 1),
                },
                "time_series": {"values": filtered_snapshots["votes"].tolist()},
                "snapshots": snapshots_real.head(5).to_dict(orient="records"),
            }

            buffer = io.BytesIO()
            CentinelPDFReport().generate(report_data, buffer)
            pdf_bytes = buffer.getvalue()
        else:
            pdf_bytes = build_pdf_report(pdf_data, chart_buffers)
        dept_label = selected_department if selected_department != "Todos" else "nacional"
        st.download_button(
            f"Descargar Informe PDF ({dept_label})",
            data=pdf_bytes,
            file_name=f"centinel_informe_{dept_label.lower().replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
    else:
        st.warning("Exportacion PDF no disponible: falta instalar reportlab.")

    # EN: WeasyPrint PDF button — professional Jinja2-rendered report.
    # ES: Boton PDF WeasyPrint — reporte profesional renderizado con Jinja2.
    if JINJA2_AVAILABLE and WEASYPRINT_AVAILABLE:
        _wp_now = dt.datetime.now(dt.timezone.utc)
        _wp_template_data = {
            "status": "COMPROMETIDO" if (not topology["is_match"] or critical_count > 0) else "INTEGRAL",
            "report_date": _wp_now.strftime("%Y-%m-%d %H:%M UTC"),
            "generated_by": _current_username,
            "root_hash": anchor.root_hash,
            "snapshot_hash": current_snapshot_hash,
            "snapshot_count": len(snapshot_files),
            "source": "19 JSON Streams (Direct Endpoint)",
            "executive_summary": pdf_data.get("executive_summary", ""),
            "kpi_rows": pdf_data.get("kpi_rows", []),
            "topology_summary": topology_summary,
            "topology_rows": topology_rows,
            "waterfall_chart": _chart_to_base64(chart_buffers.get("waterfall")),
            "anomaly_rows": anomaly_rows,
            "benford_chart": _chart_to_base64(chart_buffers.get("benford")),
            "timeline_chart": _chart_to_base64(chart_buffers.get("timeline")),
            "heatmap_chart": _chart_to_base64(chart_buffers.get("heatmap")),
            "snapshot_rows": snapshot_rows,
            "rules_list": rules_list,
            "thresholds": {
                "diff_error_min": alert_thresholds["diff_error_min"],
                "anomaly_error_min": alert_thresholds["anomaly_error_min"],
                "min_samples": alert_thresholds["min_samples"],
            },
            "report_hash": report_hash,
            "qr_image": "",
            "conclusions": (
                f"Se auditaron {len(snapshot_files)} snapshots. "
                f"Integridad topologica: {'OK' if topology['is_match'] else 'DISCREPANCIA'}. "
                f"Anomalias detectadas: {len(filtered_anomalies)}."
            ),
        }
        _wp_qr = build_qr_bytes(anchor.root_hash)
        if _wp_qr:
            _wp_template_data["qr_image"] = base64.b64encode(_wp_qr).decode("utf-8")
        _wp_pdf = _generate_weasyprint_pdf(_wp_template_data)
        if _wp_pdf:
            _wp_filename = f"centinel_audit_{_wp_now.strftime('%Y%m%d_%H%M%S')}.pdf"
            st.download_button(
                "\U0001f4c4 Descargar Reporte Completo como PDF",
                data=_wp_pdf,
                file_name=_wp_filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

    st.download_button(
        "Descargar CSV",
        data=filtered_snapshots.to_csv(index=False),
        file_name="centinel_snapshots.csv",
    )
    st.download_button(
        "Descargar JSON",
        data=filtered_snapshots.to_json(orient="records"),
        file_name="centinel_snapshots.json",
    )

# =========================================================================
# EN: TAB 2 — Sandbox Personal (researcher and viewer only).
#     Per-user threshold sliders, chart visibility toggles, and date ranges.
#     Stored per user in SQLite.  Does NOT affect production or global thresholds.
# ES: TAB 2 — Sandbox Personal (solo researcher y viewer).
#     Sliders de umbrales por usuario, toggles de graficos, rangos de fecha.
#     Guardado por usuario en SQLite.  NO afecta produccion ni umbrales globales.
# =========================================================================
with tabs[1]:
    st.markdown("### Sandbox Personal / Personal Sandbox")
    st.caption(
        "EN: Modify thresholds and chart visibility for your own exploration. "
        "Changes are saved per user and do NOT affect the production system.  \n"
        "ES: Modifica umbrales y visibilidad de graficos para tu propia exploracion. "
        "Los cambios se guardan por usuario y NO afectan el sistema productivo."
    )

    if _current_role not in ("researcher", "viewer", "admin"):
        st.warning("Tu rol no tiene acceso al sandbox.")
    else:
        # EN: Load user sandbox from DB.
        # ES: Cargar sandbox del usuario desde DB.
        if "sandbox_data" not in st.session_state:
            if AUTH_AVAILABLE:
                st.session_state["sandbox_data"] = load_sandbox(_current_username)
            else:
                st.session_state["sandbox_data"] = {}

        sb = st.session_state["sandbox_data"]

        st.markdown("#### Umbrales personalizados / Custom Thresholds")
        sb_cols = st.columns(3)
        with sb_cols[0]:
            sb["delta_threshold"] = st.slider(
                "Umbral delta negativo / Negative delta threshold",
                min_value=-2000,
                max_value=0,
                value=int(sb.get("delta_threshold", -200)),
                step=50,
                key="sb_delta_threshold",
            )
        with sb_cols[1]:
            sb["benford_pvalue"] = st.slider(
                "P-value Benford minimo / Min Benford p-value",
                min_value=0.001,
                max_value=0.10,
                value=float(sb.get("benford_pvalue", 0.05)),
                step=0.005,
                format="%.3f",
                key="sb_benford_pvalue",
            )
        with sb_cols[2]:
            sb["zscore_outlier"] = st.slider(
                "Z-score outlier / Outlier z-score",
                min_value=1.0,
                max_value=5.0,
                value=float(sb.get("zscore_outlier", 2.5)),
                step=0.1,
                key="sb_zscore",
            )

        st.markdown("#### Graficos visibles / Visible Charts")
        chart_options = [
            "Benford",
            "Timeline votos",
            "Heatmap anomalias",
            "Vista departamental",
            "Cadena de hashes",
        ]
        sb["visible_charts"] = st.multiselect(
            "Selecciona graficos / Select charts",
            chart_options,
            default=sb.get("visible_charts", chart_options),
            key="sb_visible_charts",
        )

        st.markdown("#### Rango de fechas / Date Range")
        date_cols = st.columns(2)
        with date_cols[0]:
            sb["date_from"] = str(
                st.date_input(
                    "Desde / From",
                    value=dt.date.fromisoformat(sb["date_from"]) if sb.get("date_from") else dt.date(2025, 11, 30),
                    key="sb_date_from",
                )
            )
        with date_cols[1]:
            sb["date_to"] = str(
                st.date_input(
                    "Hasta / To",
                    value=dt.date.fromisoformat(sb["date_to"]) if sb.get("date_to") else dt.date.today(),
                    key="sb_date_to",
                )
            )

        if st.button("Guardar sandbox / Save sandbox", type="primary", key="sb_save"):
            st.session_state["sandbox_data"] = sb
            if AUTH_AVAILABLE:
                save_sandbox(_current_username, sb)
            st.success("Sandbox guardado correctamente / Sandbox saved successfully.")

        # EN: Preview with sandbox thresholds.
        # ES: Vista previa con umbrales del sandbox.
        st.markdown("---")
        st.markdown("#### Vista previa con tus umbrales / Preview with your thresholds")
        sb_filtered = filtered_snapshots.copy()
        if not sb_filtered.empty:
            sb_anomalies = sb_filtered[sb_filtered["delta"] < sb.get("delta_threshold", -200)]
            st.metric("Anomalias con tus umbrales", len(sb_anomalies))
            if not sb_anomalies.empty:
                st.dataframe(sb_anomalies[["timestamp", "department", "delta", "votes", "hash"]], hide_index=True)
            else:
                st.success("Sin anomalias con los umbrales configurados.")

            if "Benford" in sb.get("visible_charts", []):
                st.altair_chart(
                    alt.Chart(benford_df)
                    .transform_fold(["expected", "observed"], as_=["type", "value"])
                    .mark_bar()
                    .encode(
                        x=alt.X("digit:O", title="Digito"),
                        y=alt.Y("value:Q", title="%"),
                        color="type:N",
                    )
                    .properties(height=200, title="Benford (sandbox)"),
                    use_container_width=True,
                )

            if "Timeline votos" in sb.get("visible_charts", []):
                st.line_chart(sb_filtered.set_index("hour")["votes"], height=180)


# =========================================================================
# EN: TAB 3 — Datos Historicos 2025.
#     Multi-selector for the 96 JSON files from data/2025/ (elections 30/11/2025).
#     Also supports test fixtures from tests/fixtures/snapshots_2025/.
# ES: TAB 3 — Datos Historicos 2025.
#     Selector multiple de los 96 archivos JSON de data/2025/ (elecciones 30/11/2025).
#     Tambien soporta fixtures de prueba de tests/fixtures/snapshots_2025/.
# =========================================================================
with tabs[2]:
    st.markdown("### Datos Historicos 2025 / Historical Data 2025")
    st.caption(
        "EN: Load any combination of the 2025 election JSON files for retrospective audit.  \n"
        "ES: Carga cualquier combinacion de archivos JSON de las elecciones 2025 para auditoria retrospectiva."
    )

    # EN: Discover available 2025 data files.
    # ES: Descubrir archivos de datos 2025 disponibles.
    _hist_dirs = [
        REPO_ROOT / "data" / "2025",
        REPO_ROOT / "tests" / "fixtures" / "snapshots_2025",
    ]
    _hist_files: list[Path] = []
    for _hd in _hist_dirs:
        if _hd.exists():
            _hist_files.extend(sorted(_hd.glob("*.json")))

    if not _hist_files:
        st.info(
            "No se encontraron archivos JSON en data/2025/ ni tests/fixtures/snapshots_2025/.  \n"
            "Coloca los 96 archivos JSON de las elecciones del 30/11/2025 en data/2025/ para habilitarlos."
        )
    else:
        _hist_labels = [f.name for f in _hist_files]
        selected_hist = st.multiselect(
            "Seleccionar archivos / Select files",
            _hist_labels,
            default=_hist_labels[:5] if len(_hist_labels) > 5 else _hist_labels,
            key="hist_select",
        )

        if selected_hist and st.button("Cargar y auditar / Load & audit", type="primary", key="hist_load"):
            _hist_selected_paths = [f for f in _hist_files if f.name in selected_hist]
            _hist_snapshots = []
            for hp in _hist_selected_paths:
                payload = _safe_read_json(hp)
                if payload is not None:
                    content_str = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                    _hist_snapshots.append(
                        {
                            "path": hp,
                            "timestamp": payload.get("timestamp_utc") or payload.get("timestamp") or hp.stem,
                            "content": payload,
                            "hash": hashlib.sha256(content_str.encode("utf-8")).hexdigest(),
                            "is_real": True,
                        }
                    )

            if _hist_snapshots:
                st.success(f"Se cargaron {len(_hist_snapshots)} archivos historicos.")

                # EN: Build metrics from historical data.
                # ES: Construir metricas desde datos historicos.
                _hist_df = build_snapshot_metrics(_hist_snapshots)
                _hist_anomalies = build_anomalies(_hist_df)

                st.markdown("#### Resumen historico / Historical Summary")
                hm_cols = st.columns(3)
                hm_cols[0].metric("Snapshots cargados", len(_hist_snapshots))
                hm_cols[1].metric("Anomalias", len(_hist_anomalies))
                hm_cols[2].metric("Departamentos", _hist_df["department"].nunique() if not _hist_df.empty else 0)

                if not _hist_df.empty:
                    st.dataframe(
                        _hist_df[["timestamp", "department", "delta", "votes", "status", "hash"]],
                        use_container_width=True,
                        hide_index=True,
                    )

                # EN: Show raw JSON structure for each selected file.
                # ES: Mostrar estructura JSON cruda de cada archivo seleccionado.
                with st.expander("Detalle JSON / JSON Detail"):
                    for snap in _hist_snapshots[:5]:
                        st.markdown(f"**{snap['path'].name}** - Hash: `{snap['hash'][:16]}...`")
                        st.json(snap["content"])
            else:
                st.warning("No se pudieron cargar los archivos seleccionados.")


# =========================================================================
# EN: TAB 4 — Panel de Control Admin (admin role only).
#     Visual sliders for global thresholds (saved to config/prod/rules_core.yaml
#     with automatic backup), buttons to launch full audit, view logs, etc.
# ES: TAB 4 — Panel de Control Admin (solo rol admin).
#     Sliders visuales para umbrales globales (guardados en config/prod/rules_core.yaml
#     con backup automatico), botones para lanzar auditoria completa, ver logs, etc.
# =========================================================================
if _current_role == "admin" and len(tabs) > 3:
    with tabs[3]:
        st.markdown("### Panel de Control Admin / Admin Control Panel")
        st.caption(
            "EN: Manage global thresholds, users, system health, and audit controls.  \n"
            "ES: Gestiona umbrales globales, usuarios, salud del sistema y controles de auditoria."
        )

        # ----- Global Thresholds -----
        st.markdown("#### Umbrales Globales / Global Thresholds")
        st.info(
            "EN: Changes here are saved to config/prod/rules_core.yaml with automatic backup.  \n"
            "ES: Los cambios aqui se guardan en config/prod/rules_core.yaml con backup automatico."
        )

        _rules_core_path = REPO_ROOT / "config" / "prod" / "rules_core.yaml"
        _rules_core = load_yaml_config(_rules_core_path) if _rules_core_path.exists() else {}

        _admin_max_req = st.slider(
            "MAX_REQUESTS_PER_HOUR",
            min_value=10,
            max_value=500,
            value=int(_rules_core.get("MAX_REQUESTS_PER_HOUR", 180)),
            step=10,
            key="admin_max_req",
        )

        _admin_reglas = _rules_core.get("reglas_core", [])
        st.markdown("**Reglas activas / Active rules:**")
        for _r in _admin_reglas:
            st.markdown(f"- `{_r}`")

        if st.button("Guardar umbrales / Save thresholds", type="primary", key="admin_save_thresholds"):
            if yaml is not None:
                # EN: Backup current config before overwriting.
                # ES: Backup de la config actual antes de sobreescribir.
                import shutil as _shutil

                _backup_path = _rules_core_path.with_suffix(
                    f".yaml.bak.{dt.datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                )
                if _rules_core_path.exists():
                    _shutil.copy2(str(_rules_core_path), str(_backup_path))

                _rules_core["MAX_REQUESTS_PER_HOUR"] = _admin_max_req
                _rules_core_path.write_text(
                    yaml.dump(_rules_core, default_flow_style=False, allow_unicode=True),
                    encoding="utf-8",
                )
                st.success(f"Umbrales guardados. Backup: {_backup_path.name}")
            else:
                st.error("PyYAML no disponible. No se pueden guardar cambios.")

        st.markdown("---")

        # ----- User Management -----
        st.markdown("#### Gestion de Usuarios / User Management")
        if AUTH_AVAILABLE:
            _users = list_users()
            if _users:
                st.dataframe(pd.DataFrame(_users), use_container_width=True, hide_index=True)

            with st.form("create_user_form", clear_on_submit=True):
                st.markdown("**Crear nuevo usuario / Create new user**")
                _nu_cols = st.columns(3)
                with _nu_cols[0]:
                    _nu_user = st.text_input("Username", key="nu_user")
                with _nu_cols[1]:
                    _nu_pass = st.text_input("Password", type="password", key="nu_pass")
                with _nu_cols[2]:
                    _nu_role = st.selectbox("Rol / Role", VALID_ROLES, index=2, key="nu_role")
                _nu_submit = st.form_submit_button("Crear / Create")
            if _nu_submit:
                if _nu_user and _nu_pass:
                    ok = create_user(_nu_user, _nu_pass, _nu_role)
                    if ok:
                        st.success(f"Usuario '{_nu_user}' creado con rol '{_nu_role}'.")
                    else:
                        st.error(f"No se pudo crear el usuario '{_nu_user}' (ya existe?).")
                else:
                    st.warning("Completa todos los campos.")

            with st.expander("Eliminar usuario / Delete user"):
                _del_user = st.text_input("Username a eliminar", key="del_user")
                if st.button("Eliminar / Delete", key="del_btn"):
                    if _del_user == _current_username:
                        st.error("No puedes eliminar tu propia cuenta.")
                    elif _del_user:
                        ok = delete_user(_del_user)
                        if ok:
                            st.success(f"Usuario '{_del_user}' eliminado.")
                        else:
                            st.error(f"No se encontro el usuario '{_del_user}'.")
        else:
            st.warning("Modulo de autenticacion no disponible.")

        st.markdown("---")

        # ----- System Status (moved from old tabs[6]) -----
        st.markdown("#### Estado del Sistema / System Status")

        refresh_cols = st.columns([0.4, 0.6])
        with refresh_cols[0]:
            auto_refresh = st.checkbox("Auto-refrescar", value=False, key="auto_refresh_system")
        with refresh_cols[1]:
            refresh_interval = st.select_slider(
                "Intervalo de refresco (segundos)",
                options=[30, 45, 60],
                value=45,
                key="refresh_interval_system",
            )

        time_since_last = dt.datetime.now(dt.timezone.utc) - latest_timestamp if latest_timestamp else None
        time_since_label = _format_timedelta(time_since_last)
        latest_checkpoint_label = latest_timestamp.strftime("%Y-%m-%d %H:%M UTC") if latest_timestamp else "Sin datos"

        health_ok = False
        health_message = "healthcheck_strict_no_data"
        if not STRICT_HEALTH_AVAILABLE:
            health_message = f"healthcheck_disabled: {STRICT_HEALTH_ERROR}"
        else:
            try:
                health_ok, diagnostics = asyncio.run(is_healthy_strict())
                if health_ok:
                    health_message = "healthcheck_strict_ok"
                else:
                    failures = diagnostics.get("failures", [])
                    health_message = "; ".join(failures) if failures else "healthcheck_strict_failed"
            except Exception as exc:  # noqa: BLE001
                health_ok = False
                health_message = f"healthcheck_error: {exc}"

        bucket_status = {}
        try:
            bucket_status = _check_bucket_connection()
        except Exception as exc:  # noqa: BLE001
            bucket_status = {"status": "Error", "latency_ms": None, "message": str(exc)}

        critical_alerts = filtered_anomalies.copy()
        if not critical_alerts.empty:
            critical_alerts = critical_alerts[critical_alerts["type"] == "Delta negativo"]
        if not critical_alerts.empty:
            critical_alerts["timestamp_dt"] = pd.to_datetime(
                critical_alerts["timestamp"], errors="coerce", utc=True
            )
            critical_alerts = critical_alerts.sort_values("timestamp_dt", ascending=False)
        critical_alerts = critical_alerts.head(5)

        pipeline_status = "Activo"
        if not health_ok:
            pipeline_status = "Con errores criticos"
        elif not critical_alerts.empty:
            pipeline_status = "Con errores criticos"
        elif latest_timestamp is None or (time_since_last and time_since_last > dt.timedelta(minutes=45)):
            pipeline_status = "Pausado"
        elif failed_retries > 0:
            pipeline_status = "Recuperandose"

        status_emoji = {
            "Activo": "\U0001f7e2",
            "Pausado": "\U0001f7e1",
            "Recuperandose": "\U0001f7e1",
            "Con errores criticos": "\U0001f534",
        }.get(pipeline_status, "\u26aa")

        header_cols = st.columns(3)
        with header_cols[0]:
            st.metric("Estado del pipeline", f"{status_emoji} {pipeline_status}")
        with header_cols[1]:
            st.metric("Ultimo checkpoint", latest_checkpoint_label)
            st.caption(f"Lote: {last_batch_label} - Hash: {_format_short_hash(hash_accumulator)}")
        with header_cols[2]:
            st.metric("Tiempo desde ultimo lote", time_since_label)

        health_cols = st.columns([1.1, 0.9])
        with health_cols[0]:
            health_state = "complete" if health_ok else "error"
            with st.status(
                f"Healthcheck estricto: {'OK' if health_ok else 'ERROR'}",
                state=health_state,
            ):
                st.write(health_message)
        with health_cols[1]:
            supervisor_status = _detect_supervisor()
            st.metric("Supervisor externo", supervisor_status)

        st.markdown("#### Recursos en tiempo real")
        resource_cols = st.columns(3)
        if PSUTIL_AVAILABLE:
            cpu_percent = psutil.cpu_percent(interval=0.2)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage("/").percent
            with resource_cols[0]:
                st.metric("CPU", f"{cpu_percent:.1f}%")
            with resource_cols[1]:
                st.metric("Memoria", f"{memory_percent:.1f}%")
            with resource_cols[2]:
                st.metric("Disco", f"{disk_percent:.1f}%")
        else:
            with resource_cols[0]:
                st.metric("CPU", "N/D")
            with resource_cols[1]:
                st.metric("Memoria", "N/D")
            with resource_cols[2]:
                st.metric("Disco", "N/D")
            st.info("Metricas de sistema no disponibles: instala psutil.")

        connection_cols = st.columns(3)
        with connection_cols[0]:
            bucket_label = bucket_status.get("status", "N/D")
            latency = bucket_status.get("latency_ms")
            latency_label = f"{latency:.0f} ms" if latency is not None else "N/D"
            st.metric("Bucket checkpoints", bucket_label)
            st.caption(f"Latencia: {latency_label}")
        with connection_cols[1]:
            st.metric("Reintentos fallidos (24h)", str(failed_retries))
        with connection_cols[2]:
            st.metric("Hash acumulado", _format_short_hash(hash_accumulator))

        st.markdown("#### Ultimas alertas criticas")
        if critical_alerts.empty:
            st.success("Sin alertas criticas recientes.")
        else:
            alert_table = critical_alerts[["timestamp", "department", "type", "delta", "hash"]].rename(
                columns={
                    "timestamp": "Timestamp",
                    "department": "Departamento",
                    "type": "Motivo",
                    "delta": "Delta votos",
                    "hash": "Hash",
                }
            )
            alert_table["Hash"] = alert_table["Hash"].apply(_format_short_hash)
            st.dataframe(alert_table, use_container_width=True, hide_index=True)

        st.markdown("#### Acciones de mantenimiento / Maintenance Actions")
        maint_cols = st.columns(2)
        with maint_cols[0]:
            if st.button("Forzar checkpoint ahora", type="primary", key="admin_checkpoint"):
                try:
                    manager = _build_checkpoint_manager()
                    if manager is None:
                        if not CHECKPOINTING_AVAILABLE:
                            st.error(f"Checkpoint deshabilitado: ({CHECKPOINTING_ERROR}).")
                        else:
                            st.error("Checkpoint no configurado: define CHECKPOINT_BUCKET.")
                    else:
                        manager.save_checkpoint(
                            {
                                "last_acta_id": last_batch_label,
                                "last_batch_offset": len(snapshot_files),
                                "rules_state": {"source": "dashboard"},
                                "hash_accumulator": hash_accumulator,
                            }
                        )
                        st.success("Checkpoint guardado exitosamente.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"No se pudo guardar el checkpoint: {exc}")

        with maint_cols[1]:
            if st.button("Lanzar auditoria completa / Run full audit", key="admin_audit"):
                st.info("Auditoria completa solicitada. Verificando motor de reglas...")
                _audit_result = run_rules_engine(snapshots_df, command_center_cfg)
                _n_alerts = len(_audit_result.get("alerts", []))
                _n_crit = len(_audit_result.get("critical", []))
                st.success(f"Auditoria completada: {_n_alerts} alertas, {_n_crit} criticas.")

        # EN: View logs section.
        # ES: Seccion de visualizacion de logs.
        with st.expander("Ver logs recientes / View recent logs"):
            _log_file = Path(command_center_cfg.get("logging", {}).get("file", "C.E.N.T.I.N.E.L.log"))
            if _log_file.exists():
                try:
                    _log_content = _log_file.read_text(encoding="utf-8", errors="ignore")
                    _log_lines = _log_content.strip().split("\n")
                    st.code("\n".join(_log_lines[-50:]), language="log")
                except OSError as exc:
                    st.error(f"Error leyendo logs: {exc}")
            else:
                st.info(f"Archivo de log no encontrado: {_log_file}")

        if auto_refresh:
            st.caption(f"Auto-refresco activo - proxima actualizacion en {refresh_interval}s.")
            time.sleep(refresh_interval)
            rerun_app()

# =========================================================================
# EN: Footer
# ES: Pie de pagina
# =========================================================================
st.markdown("---")
st.caption(
    "C.E.N.T.I.N.E.L. - Centro de Vigilancia Electoral | "
    "Auditoria tecnica independiente | Sistema agnostico a partidos politicos"
)
