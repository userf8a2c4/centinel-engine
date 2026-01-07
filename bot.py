"""Bot Telegram para consultas rápidas de Sentinel (solo lectura)."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Iterable

import matplotlib
from dateutil import parser
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from sentinel.utils.logging_config import setup_logging

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

setup_logging()
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
HASH_DIR = Path("hashes")
ALERTS_LOG = Path("alerts.log")
ALERTS_JSON = DATA_DIR / "alerts.json"

MODE_CIUDADANO = "ciudadano"
MODE_AUDITOR = "auditor"

DISCLAIMER = (
    "Solo datos públicos del CNE – Código abierto MIT – "
    "Repo: https://github.com/userf8a2c4/sentinel"
)

RATE_LIMIT_SECONDS = 60
MODE_TTL_MINUTES = 120


@dataclass
class SnapshotRecord:
    path: Path
    payload: dict
    timestamp: datetime | None
    porcentaje_escrutado: float | None
    total_votos: int | None
    votos_lista: list[int]
    departamento: str | None


@dataclass
class RangeQuery:
    start: datetime | None
    end: datetime | None
    label: str


MODE_STORE: dict[int, dict[str, object]] = {}
RATE_LIMIT: dict[int, datetime] = {}


def cleanup_mode_store(now: datetime) -> None:
    expired = []
    for chat_id, item in MODE_STORE.items():
        last_seen = item.get("last_seen")
        if isinstance(last_seen, datetime) and (now - last_seen) > timedelta(
            minutes=MODE_TTL_MINUTES
        ):
            expired.append(chat_id)
    for chat_id in expired:
        MODE_STORE.pop(chat_id, None)


def set_mode(chat_id: int, mode: str) -> None:
    MODE_STORE[chat_id] = {"mode": mode, "last_seen": datetime.utcnow()}


def get_mode(chat_id: int) -> str:
    entry = MODE_STORE.get(chat_id)
    if not entry:
        return MODE_CIUDADANO
    mode = entry.get("mode")
    return mode if mode in (MODE_CIUDADANO, MODE_AUDITOR) else MODE_CIUDADANO


def update_last_seen(chat_id: int) -> None:
    entry = MODE_STORE.get(chat_id)
    if entry:
        entry["last_seen"] = datetime.utcnow()


def is_rate_limited(chat_id: int, now: datetime) -> bool:
    last_seen = RATE_LIMIT.get(chat_id)
    if last_seen and (now - last_seen).total_seconds() < RATE_LIMIT_SECONDS:
        return True
    RATE_LIMIT[chat_id] = now
    return False


def parse_timestamp_from_name(filename: str) -> datetime | None:
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    date_part = parts[-2]
    time_part = parts[-1]
    for fmt in ("%Y-%m-%d_%H-%M-%S", "%Y-%m-%d_%H-%M"):
        try:
            return datetime.strptime(f"{date_part}_{time_part}", fmt)
        except ValueError:
            continue
    return None


def extract_timestamp(snapshot_path: Path, payload: dict) -> datetime | None:
    metadata = payload.get("metadata") or payload.get("meta") or {}
    for key in ("timestamp_utc", "timestamp"):
        raw = metadata.get(key) or payload.get(key)
        if isinstance(raw, str):
            try:
                return parser.isoparse(raw)
            except ValueError:
                continue
        if isinstance(raw, datetime):
            return raw
    return parse_timestamp_from_name(snapshot_path.name)


def safe_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def safe_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def extract_porcentaje_escrutado(payload: dict) -> float | None:
    porcentaje = (
        payload.get("porcentaje_escrutado")
        or payload.get("porcentaje")
        or payload.get("porcentaje_escrutinio")
    )
    if porcentaje is None:
        meta = payload.get("meta") or payload.get("metadata") or {}
        porcentaje = meta.get("porcentaje_escrutado") or meta.get("porcentaje")
    return safe_float(porcentaje)


def extract_total_votos(payload: dict) -> int | None:
    votos_totales = payload.get("votos_totales") or {}
    total = (
        payload.get("total_votos")
        or votos_totales.get("total")
        or votos_totales.get("total_votes")
        or votos_totales.get("validos")
        or votos_totales.get("valid_votes")
    )
    total_value = safe_int(total)
    if total_value is not None:
        return total_value
    votos_lista = extract_votos_lista(payload)
    if votos_lista:
        return sum(votos_lista)
    return None


def extract_votos_lista(payload: dict) -> list[int]:
    votos = payload.get("votos") or payload.get("candidates") or payload.get("candidatos")
    if isinstance(votos, list):
        results = []
        for item in votos:
            if isinstance(item, dict):
                value = safe_int(item.get("votos") or item.get("votes") or item.get("total"))
                if value is not None:
                    results.append(value)
            elif isinstance(item, (int, float, str)):
                value = safe_int(item)
                if value is not None:
                    results.append(value)
        return results
    if isinstance(votos, dict):
        results = []
        for value in votos.values():
            value_int = safe_int(value)
            if value_int is not None:
                results.append(value_int)
        return results
    return []


def load_snapshot(path: Path) -> SnapshotRecord | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("snapshot_read_failed path=%s error=%s", path, exc)
        return None
    data_payload = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    timestamp = extract_timestamp(path, payload)
    porcentaje = extract_porcentaje_escrutado(data_payload)
    total_votos = extract_total_votos(data_payload)
    votos_lista = extract_votos_lista(data_payload)
    departamento = None
    metadata = payload.get("metadata") or payload.get("meta") or {}
    departamento = metadata.get("department") or metadata.get("departamento")
    if not departamento and isinstance(data_payload, dict):
        departamento = data_payload.get("departamento")
    return SnapshotRecord(
        path=path,
        payload=payload,
        timestamp=timestamp,
        porcentaje_escrutado=porcentaje,
        total_votos=total_votos,
        votos_lista=votos_lista,
        departamento=departamento,
    )


def load_snapshots() -> list[SnapshotRecord]:
    if not DATA_DIR.exists():
        return []
    snapshots = sorted(DATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    records: list[SnapshotRecord] = []
    for snapshot_path in snapshots:
        record = load_snapshot(snapshot_path)
        if record:
            records.append(record)
    return records


def parse_range(text: str, reference: datetime) -> RangeQuery | None:
    if not text:
        return RangeQuery(None, None, "todo")
    normalized = text.strip().lower()
    match = re.search(
        r"(últimos|últimas|ultimo|ultimos)\s*(\d+)\s*(min|minuto|minutos|h|hora|horas|d|dia|días|dias)",
        normalized,
    )
    if match:
        amount = int(match.group(2))
        unit = match.group(3)
        if unit.startswith("min"):
            delta = timedelta(minutes=amount)
        elif unit.startswith("h"):
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(days=amount)
        return RangeQuery(reference - delta, reference, f"últimos {amount} {unit}")
    if "hoy" in normalized:
        start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
        return RangeQuery(start, reference, "hoy")
    if "ayer" in normalized:
        end = reference.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
        return RangeQuery(start, end, "ayer")
    match = re.search(r"desde\s*(\d{1,2}:\d{2})\s*hasta\s*(\d{1,2}:\d{2})", normalized)
    if match:
        start_time = match.group(1)
        end_time = match.group(2)
        base_date = reference.date()
        start = datetime.combine(base_date, parser.parse(start_time).time())
        end = datetime.combine(base_date, parser.parse(end_time).time())
        if end < start:
            end += timedelta(days=1)
        return RangeQuery(start, end, f"desde {start_time} hasta {end_time}")
    return None


def filter_snapshots(records: Iterable[SnapshotRecord], query: RangeQuery | None) -> list[SnapshotRecord]:
    if not query or (query.start is None and query.end is None):
        return list(records)
    filtered = []
    for record in records:
        if not record.timestamp:
            continue
        if query.start and record.timestamp < query.start:
            continue
        if query.end and record.timestamp > query.end:
            continue
        filtered.append(record)
    return filtered


def format_number(value: int | float | None) -> str:
    if value is None:
        return "N/D"
    if isinstance(value, float):
        return f"{value:.2f}"
    return f"{value:,}".replace(",", ".")


def build_disclaimer(message: str) -> str:
    return f"{message}\n\n{DISCLAIMER}"


def get_latest_timestamp(records: list[SnapshotRecord]) -> str:
    for record in records:
        if record.timestamp:
            return record.timestamp.strftime("%Y-%m-%d %H:%M")
    return "sin fecha"


def get_alerts() -> list[dict]:
    if ALERTS_JSON.exists():
        try:
            data = json.loads(ALERTS_JSON.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("alerts_json_failed error=%s", exc)
    if ALERTS_LOG.exists():
        try:
            lines = ALERTS_LOG.read_text(encoding="utf-8").splitlines()
            return [{"timestamp": "", "descripcion": line} for line in lines if line.strip()]
        except OSError as exc:
            logger.error("alerts_log_failed error=%s", exc)
    return []


async def enforce_access(update: Update) -> bool:
    chat = update.effective_chat
    if not chat:
        return False
    allowed = os.getenv("TELEGRAM_CHAT_ID")
    if allowed:
        try:
            if int(allowed) != chat.id:
                await update.message.reply_text(
                    build_disclaimer("Este bot está en modo privado. No tienes acceso."),
                )
                return False
        except ValueError:
            return True
    return True


async def preflight(update: Update) -> bool:
    chat = update.effective_chat
    if not chat or not update.message:
        return False
    now = datetime.utcnow()
    cleanup_mode_store(now)
    if is_rate_limited(chat.id, now):
        await update.message.reply_text(
            build_disclaimer("Espera un minuto antes de enviar otro comando."),
        )
        return False
    update_last_seen(chat.id)
    return True


def build_commands_list(mode: str) -> str:
    base = [
        "/inicio",
        "/ultimo",
        "/cambios [rango]",
        "/alertas",
        "/grafico [rango]",
        "/tendencia [rango]",
        "/info [rango]",
    ]
    if mode == MODE_AUDITOR:
        base.extend(["/hash [acta o JRV]", "/json [rango o depto]"])
    return "\n".join(base)


async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    chat_id = update.effective_chat.id
    set_mode(chat_id, MODE_CIUDADANO)
    message = (
        "¡Bienvenido! Este bot solo muestra datos públicos ya guardados.\n"
        "¿Modo ciudadano o auditor? Escribe 'ciudadano' o 'auditor'.\n\n"
        "Comandos disponibles:\n"
        f"{build_commands_list(MODE_CIUDADANO)}"
    )
    logger.info("cmd_inicio chat_id=%s", chat_id)
    await update.message.reply_text(build_disclaimer(message))


async def seleccionar_modo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip().lower()
    if text in {"ciudadano", "modo ciudadano"}:
        set_mode(chat_id, MODE_CIUDADANO)
        message = (
            "Listo, estás en modo ciudadano.\n"
            "Comandos disponibles:\n"
            f"{build_commands_list(MODE_CIUDADANO)}"
        )
        logger.info("mode_set chat_id=%s mode=ciudadano", chat_id)
        await update.message.reply_text(build_disclaimer(message))
        return
    if text in {"auditor", "modo auditor", "prensa"}:
        set_mode(chat_id, MODE_AUDITOR)
        message = (
            "Listo, estás en modo auditor/prensa.\n"
            "Comandos disponibles:\n"
            f"{build_commands_list(MODE_AUDITOR)}"
        )
        logger.info("mode_set chat_id=%s mode=auditor", chat_id)
        await update.message.reply_text(build_disclaimer(message))
        return


async def ultimo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(
            build_disclaimer("No hay datos disponibles todavía."),
        )
        return
    latest = records[0]
    timestamp = latest.timestamp.strftime("%Y-%m-%d %H:%M") if latest.timestamp else "N/D"
    porcentaje = format_number(latest.porcentaje_escrutado)
    votos = format_number(latest.total_votos)
    message = (
        f"¡Última actualización a las {timestamp}! "
        f"{porcentaje}% escrutado, {votos} votos totales."
    )
    logger.info("cmd_ultimo chat_id=%s", update.effective_chat.id)
    await update.message.reply_text(build_disclaimer(message))


def resolve_range_argument(records: list[SnapshotRecord], args: list[str]) -> tuple[RangeQuery | None, str | None]:
    text = " ".join(args).strip()
    reference = None
    for record in records:
        if record.timestamp:
            reference = record.timestamp
            break
    if not reference:
        reference = datetime.utcnow()
    query = parse_range(text, reference)
    if text and query is None:
        return None, (
            "No entendí el rango. Ejemplos válidos: 'últimos 30min', 'hoy', "
            "'ayer', 'desde 14:00 hasta 16:00'."
        )
    return query, None


async def cambios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(build_disclaimer("No hay datos disponibles todavía."))
        return
    query, error = resolve_range_argument(records, context.args)
    if error:
        await update.message.reply_text(build_disclaimer(error))
        return
    filtered = list(reversed(filter_snapshots(records, query)))
    if len(filtered) < 2:
        latest_time = get_latest_timestamp(records)
        await update.message.reply_text(
            build_disclaimer(f"No hay información en ese rango. Último disponible: {latest_time}."),
        )
        return
    first, last = filtered[0], filtered[-1]
    delta_porcentaje = None
    if first.porcentaje_escrutado is not None and last.porcentaje_escrutado is not None:
        delta_porcentaje = last.porcentaje_escrutado - first.porcentaje_escrutado
    delta_votos = None
    if first.total_votos is not None and last.total_votos is not None:
        delta_votos = last.total_votos - first.total_votos
    parts = ["Cambios recientes:"]
    if delta_porcentaje is not None:
        parts.append(f"% escrutado: {delta_porcentaje:+.2f} puntos")
    if delta_votos is not None:
        parts.append(f"Votos: {delta_votos:+,}".replace(",", "."))
    if delta_porcentaje is None and delta_votos is None:
        parts.append("No hay métricas comparables en ese rango.")
    message = "\n".join(parts)
    logger.info("cmd_cambios chat_id=%s range=%s", update.effective_chat.id, query.label if query else "todo")
    await update.message.reply_text(build_disclaimer(message))


async def alertas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    alerts = get_alerts()
    if not alerts:
        await update.message.reply_text(build_disclaimer("No hay alertas registradas por ahora."))
        return
    lines = []
    for item in alerts[:5]:
        descripcion = item.get("descripcion") or item.get("detail") or "Alerta"
        timestamp = item.get("timestamp") or ""
        if timestamp:
            lines.append(f"{descripcion} ({timestamp})")
        else:
            lines.append(descripcion)
    message = "Alertas recientes:\n" + "\n".join(f"- {line}" for line in lines)
    logger.info("cmd_alertas chat_id=%s", update.effective_chat.id)
    await update.message.reply_text(build_disclaimer(message))


def build_benford_chart(votes: list[int], title: str) -> BytesIO:
    digits = [int(str(v)[0]) for v in votes if v > 0]
    counts = [digits.count(d) for d in range(1, 10)]
    total = sum(counts)
    observed = [count / total if total else 0 for count in counts]
    expected = [
        0.301,
        0.176,
        0.125,
        0.097,
        0.079,
        0.067,
        0.058,
        0.051,
        0.046,
    ]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(range(1, 10), observed, label="Observado")
    ax.plot(range(1, 10), expected, color="red", marker="o", label="Benford")
    ax.set_title(title)
    ax.set_xlabel("Primer dígito")
    ax.set_ylabel("Proporción")
    ax.set_xticks(range(1, 10))
    ax.legend()
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close(fig)
    return buffer


async def grafico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(build_disclaimer("No hay datos disponibles todavía."))
        return
    query, error = resolve_range_argument(records, context.args)
    if error:
        await update.message.reply_text(build_disclaimer(error))
        return
    filtered = filter_snapshots(records, query)
    votes = []
    for record in filtered:
        votes.extend(record.votos_lista)
    if len(votes) < 10:
        latest_time = get_latest_timestamp(records)
        await update.message.reply_text(
            build_disclaimer(f"No hay información suficiente en ese rango. Último disponible: {latest_time}."),
        )
        return
    title = f"Benford ({query.label if query else 'todo'})"
    chart = build_benford_chart(votes, title)
    caption = build_disclaimer("Gráfico Benford generado.")
    logger.info("cmd_grafico chat_id=%s range=%s", update.effective_chat.id, query.label if query else "todo")
    await update.message.reply_photo(photo=chart, caption=caption)


def build_trend_chart(points: list[tuple[datetime, float]], label: str) -> BytesIO:
    fig, ax = plt.subplots(figsize=(6, 4))
    times = [point[0] for point in points]
    values = [point[1] for point in points]
    ax.plot(times, values, marker="o")
    ax.set_title(label)
    ax.set_xlabel("Hora")
    ax.set_ylabel("Valor")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close(fig)
    return buffer


async def tendencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(build_disclaimer("No hay datos disponibles todavía."))
        return
    query, error = resolve_range_argument(records, context.args)
    if error:
        await update.message.reply_text(build_disclaimer(error))
        return
    filtered = list(reversed(filter_snapshots(records, query)))
    points: list[tuple[datetime, float]] = []
    for record in filtered:
        if not record.timestamp:
            continue
        value = record.porcentaje_escrutado
        label = "% escrutado"
        if value is None:
            value = float(record.total_votos) if record.total_votos is not None else None
            label = "Votos totales"
        if value is not None:
            points.append((record.timestamp, value))
    if len(points) < 2:
        latest_time = get_latest_timestamp(records)
        await update.message.reply_text(
            build_disclaimer(f"No hay información en ese rango. Último disponible: {latest_time}."),
        )
        return
    chart = build_trend_chart(points, f"Tendencia ({query.label if query else 'todo'})")
    caption = build_disclaimer("Tendencia generada.")
    logger.info("cmd_tendencia chat_id=%s", update.effective_chat.id)
    await update.message.reply_photo(photo=chart, caption=caption)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(build_disclaimer("No hay datos disponibles todavía."))
        return
    query, error = resolve_range_argument(records, context.args)
    if error:
        await update.message.reply_text(build_disclaimer(error))
        return
    filtered = filter_snapshots(records, query)
    if not filtered:
        latest_time = get_latest_timestamp(records)
        await update.message.reply_text(
            build_disclaimer(f"No hay información en ese rango. Último disponible: {latest_time}."),
        )
        return
    latest = filtered[0]
    message = (
        f"Resumen ({query.label if query else 'todo'}):\n"
        f"Snapshots: {len(filtered)}\n"
        f"Último % escrutado: {format_number(latest.porcentaje_escrutado)}\n"
        f"Últimos votos totales: {format_number(latest.total_votos)}"
    )
    logger.info("cmd_info chat_id=%s", update.effective_chat.id)
    await update.message.reply_text(build_disclaimer(message))


def find_snapshot_by_query(query: str, records: list[SnapshotRecord]) -> SnapshotRecord | None:
    if not query:
        return records[0] if records else None
    lower = query.lower()
    for record in records:
        if lower in record.path.name.lower():
            return record
    return None


def find_hash_for_snapshot(snapshot_path: Path) -> str | None:
    hash_path = HASH_DIR / f"{snapshot_path.name}.sha256"
    if hash_path.exists():
        try:
            return hash_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.error("hash_read_failed path=%s error=%s", hash_path, exc)
            return None
    return None


async def hash_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    if get_mode(update.effective_chat.id) != MODE_AUDITOR:
        await update.message.reply_text(
            build_disclaimer("Este comando es solo para modo auditor. Escribe 'auditor' para activarlo."),
        )
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(build_disclaimer("No hay datos disponibles todavía."))
        return
    query = " ".join(context.args).strip()
    record = find_snapshot_by_query(query, records)
    if not record:
        await update.message.reply_text(
            build_disclaimer("No encontré esa acta o JRV en los archivos disponibles."),
        )
        return
    hash_value = find_hash_for_snapshot(record.path)
    if not hash_value:
        await update.message.reply_text(
            build_disclaimer("No se encontró hash para ese archivo."),
        )
        return
    message = (
        f"Hash SHA-256 de {record.path.name}: {hash_value}."
    )
    logger.info("cmd_hash chat_id=%s query=%s", update.effective_chat.id, query)
    await update.message.reply_text(build_disclaimer(message))


def select_json_record(records: list[SnapshotRecord], query_text: str) -> SnapshotRecord | None:
    if not query_text:
        return records[0] if records else None
    lower = query_text.lower()
    for record in records:
        if record.departamento and lower in str(record.departamento).lower():
            return record
    return find_snapshot_by_query(query_text, records)


async def json_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not await enforce_access(update) or not await preflight(update):
        return
    if get_mode(update.effective_chat.id) != MODE_AUDITOR:
        await update.message.reply_text(
            build_disclaimer("Este comando es solo para modo auditor. Escribe 'auditor' para activarlo."),
        )
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(build_disclaimer("No hay datos disponibles todavía."))
        return
    query_text = " ".join(context.args).strip()
    record = select_json_record(records, query_text)
    if not record:
        await update.message.reply_text(
            build_disclaimer("No encontré un JSON crudo con ese criterio."),
        )
        return
    content = json.dumps(record.payload, ensure_ascii=False, indent=2)
    if len(content) > 3000:
        content = content[:3000] + "\n... (contenido recortado)"
    message = f"JSON crudo ({record.path.name}):\n{content}"
    logger.info("cmd_json chat_id=%s query=%s", update.effective_chat.id, query_text)
    await update.message.reply_text(build_disclaimer(message))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("telegram_error update=%s error=%s", update, context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            build_disclaimer("Ocurrió un error inesperado. Intenta nuevamente."),
        )


def build_application(token: str):
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("inicio", inicio))
    application.add_handler(CommandHandler("ultimo", ultimo))
    application.add_handler(CommandHandler("cambios", cambios))
    application.add_handler(CommandHandler("alertas", alertas))
    application.add_handler(CommandHandler("grafico", grafico))
    application.add_handler(CommandHandler("tendencia", tendencia))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("hash", hash_command))
    application.add_handler(CommandHandler("json", json_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_modo)
    )
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_TOKEN en .env o variables de entorno.")
    application = build_application(token)
    logger.info("telegram_bot_start")
    application.run_polling()


if __name__ == "__main__":
    main()
