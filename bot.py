"""Bot Telegram para consultas rápidas de Sentinel (solo lectura).

English:
    Telegram bot for quick Sentinel queries (read-only).
"""

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
    """Representa un snapshot cargado desde disco.

    Attributes:
        path (Path): Ruta del archivo de snapshot.
        payload (dict): JSON completo del snapshot.
        timestamp (datetime | None): Fecha/hora del snapshot.
        porcentaje_escrutado (float | None): % escrutado si aplica.
        total_votos (int | None): Total de votos si aplica.
        votos_lista (list[int]): Lista de votos de candidatos.
        departamento (str | None): Departamento asociado.

    English:
        Represents a snapshot loaded from disk.

    Attributes:
        path (Path): Snapshot file path.
        payload (dict): Full snapshot JSON.
        timestamp (datetime | None): Snapshot datetime.
        porcentaje_escrutado (float | None): Scrutiny percentage when available.
        total_votos (int | None): Total votes when available.
        votos_lista (list[int]): Candidate vote list.
        departamento (str | None): Related department.
    """

    path: Path
    payload: dict
    timestamp: datetime | None
    porcentaje_escrutado: float | None
    total_votos: int | None
    votos_lista: list[int]
    departamento: str | None


@dataclass
class RangeQuery:
    """Rango de fechas para filtrar snapshots.

    Attributes:
        start (datetime | None): Inicio del rango.
        end (datetime | None): Fin del rango.
        label (str): Etiqueta legible del rango.

    English:
        Date range for filtering snapshots.

    Attributes:
        start (datetime | None): Range start.
        end (datetime | None): Range end.
        label (str): Human-readable label.
    """

    start: datetime | None
    end: datetime | None
    label: str


MODE_STORE: dict[int, dict[str, object]] = {}
RATE_LIMIT: dict[int, datetime] = {}


def cleanup_mode_store(now: datetime) -> None:
    """Limpia modos expirados según el TTL configurado.

    Args:
        now (datetime): Tiempo actual en UTC.

    English:
        Clears expired mode entries based on the configured TTL.

    Args:
        now (datetime): Current UTC time.
    """
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
    """Guarda el modo seleccionado para un chat.

    Args:
        chat_id (int): ID del chat de Telegram.
        mode (str): Modo seleccionado.

    English:
        Stores the selected mode for a chat.

    Args:
        chat_id (int): Telegram chat ID.
        mode (str): Selected mode.
    """
    MODE_STORE[chat_id] = {"mode": mode, "last_seen": datetime.utcnow()}


def get_mode(chat_id: int) -> str:
    """Obtiene el modo actual de un chat.

    Args:
        chat_id (int): ID del chat.

    Returns:
        str: Modo activo (ciudadano o auditor).

    English:
        Gets the current mode for a chat.

    Args:
        chat_id (int): Chat ID.

    Returns:
        str: Active mode (citizen or auditor).
    """
    entry = MODE_STORE.get(chat_id)
    if not entry:
        return MODE_CIUDADANO
    mode = entry.get("mode")
    return mode if mode in (MODE_CIUDADANO, MODE_AUDITOR) else MODE_CIUDADANO


def update_last_seen(chat_id: int) -> None:
    """Actualiza el timestamp de última actividad del chat.

    Args:
        chat_id (int): ID del chat.

    English:
        Updates the last-seen timestamp for the chat.

    Args:
        chat_id (int): Chat ID.
    """
    entry = MODE_STORE.get(chat_id)
    if entry:
        entry["last_seen"] = datetime.utcnow()


def is_rate_limited(chat_id: int, now: datetime) -> bool:
    """Valida si un chat está en límite de frecuencia.

    Args:
        chat_id (int): ID del chat.
        now (datetime): Hora actual.

    Returns:
        bool: True si debe limitarse, False si puede continuar.

    English:
        Checks if a chat is rate-limited.

    Args:
        chat_id (int): Chat ID.
        now (datetime): Current time.

    Returns:
        bool: True if rate-limited, False otherwise.
    """
    last_seen = RATE_LIMIT.get(chat_id)
    if last_seen and (now - last_seen).total_seconds() < RATE_LIMIT_SECONDS:
        return True
    RATE_LIMIT[chat_id] = now
    return False


def parse_timestamp_from_name(filename: str) -> datetime | None:
    """Extrae un timestamp desde el nombre del archivo.

    Args:
        filename (str): Nombre del archivo.

    Returns:
        datetime | None: Timestamp parseado o None.

    English:
        Extracts a timestamp from a file name.

    Args:
        filename (str): File name.

    Returns:
        datetime | None: Parsed timestamp or None.
    """
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
    """Obtiene el timestamp desde metadata o nombre del archivo.

    Args:
        snapshot_path (Path): Ruta del snapshot.
        payload (dict): Payload del snapshot.

    Returns:
        datetime | None: Timestamp encontrado o None.

    English:
        Gets the timestamp from metadata or file name.

    Args:
        snapshot_path (Path): Snapshot path.
        payload (dict): Snapshot payload.

    Returns:
        datetime | None: Timestamp if found, otherwise None.
    """
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
    """Convierte valores a float de forma segura.

    Args:
        value (object): Valor a convertir.

    Returns:
        float | None: Float convertido o None si falla.

    English:
        Safely converts values to float.

    Args:
        value (object): Value to convert.

    Returns:
        float | None: Converted float or None on failure.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def safe_int(value: object) -> int | None:
    """Convierte valores a int de forma segura.

    Args:
        value (object): Valor a convertir.

    Returns:
        int | None: Entero convertido o None si falla.

    English:
        Safely converts values to int.

    Args:
        value (object): Value to convert.

    Returns:
        int | None: Converted int or None on failure.
    """
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
    """Extrae el porcentaje escrutado desde distintas claves.

    Args:
        payload (dict): Payload del snapshot.

    Returns:
        float | None: Porcentaje escrutado si existe.

    English:
        Extracts the scrutiny percentage from possible fields.

    Args:
        payload (dict): Snapshot payload.

    Returns:
        float | None: Scrutiny percentage if present.
    """
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
    """Obtiene el total de votos desde campos conocidos o lista de votos.

    Args:
        payload (dict): Payload del snapshot.

    Returns:
        int | None: Total de votos si se encuentra.

    English:
        Gets total votes from known fields or the vote list.

    Args:
        payload (dict): Snapshot payload.

    Returns:
        int | None: Total votes if found.
    """
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
    """Extrae una lista de votos desde el payload.

    Args:
        payload (dict): Payload del snapshot.

    Returns:
        list[int]: Lista de votos normalizados.

    English:
        Extracts a list of votes from the payload.

    Args:
        payload (dict): Snapshot payload.

    Returns:
        list[int]: Normalized vote list.
    """
    votos = (
        payload.get("votos") or payload.get("candidates") or payload.get("candidatos")
    )
    if isinstance(votos, list):
        results = []
        for item in votos:
            if isinstance(item, dict):
                value = safe_int(
                    item.get("votos") or item.get("votes") or item.get("total")
                )
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
    """Carga un snapshot desde disco y lo normaliza.

    Args:
        path (Path): Ruta del archivo de snapshot.

    Returns:
        SnapshotRecord | None: Registro cargado o None si falla.

    English:
        Loads a snapshot from disk and normalizes it.

    Args:
        path (Path): Snapshot file path.

    Returns:
        SnapshotRecord | None: Loaded record or None on failure.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("snapshot_read_failed path=%s error=%s", path, exc)
        return None
    data_payload = (
        payload.get("data") if isinstance(payload.get("data"), dict) else payload
    )
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
    """Carga todos los snapshots disponibles desde el directorio de datos.

    Returns:
        list[SnapshotRecord]: Lista de snapshots cargados.

    English:
        Loads all available snapshots from the data directory.

    Returns:
        list[SnapshotRecord]: Loaded snapshot records.
    """
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
    """Interpreta rangos de tiempo en lenguaje simple.

    Args:
        text (str): Texto ingresado por el usuario.
        reference (datetime): Fecha/hora de referencia.

    Returns:
        RangeQuery | None: Rango interpretado o None si no se entiende.

    English:
        Parses human-friendly time ranges.

    Args:
        text (str): User-entered text.
        reference (datetime): Reference datetime.

    Returns:
        RangeQuery | None: Parsed range or None if not understood.
    """
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


def filter_snapshots(
    records: Iterable[SnapshotRecord], query: RangeQuery | None
) -> list[SnapshotRecord]:
    """Filtra snapshots según un rango temporal.

    Args:
        records (Iterable[SnapshotRecord]): Lista de registros.
        query (RangeQuery | None): Rango solicitado.

    Returns:
        list[SnapshotRecord]: Lista filtrada.

    English:
        Filters snapshots by a time range.

    Args:
        records (Iterable[SnapshotRecord]): Record list.
        query (RangeQuery | None): Requested range.

    Returns:
        list[SnapshotRecord]: Filtered list.
    """
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
    """Formatea números para mostrar en mensajes.

    Args:
        value (int | float | None): Valor a formatear.

    Returns:
        str: Texto formateado.

    English:
        Formats numbers for display in messages.

    Args:
        value (int | float | None): Value to format.

    Returns:
        str: Formatted text.
    """
    if value is None:
        return "N/D"
    if isinstance(value, float):
        return f"{value:.2f}"
    return f"{value:,}".replace(",", ".")


def build_disclaimer(message: str) -> str:
    """Agrega el descargo institucional al mensaje.

    Args:
        message (str): Mensaje base.

    Returns:
        str: Mensaje con descargo agregado.

    English:
        Appends the institutional disclaimer to a message.

    Args:
        message (str): Base message.

    Returns:
        str: Message with disclaimer appended.
    """
    return f"{message}\n\n{DISCLAIMER}"


def get_latest_timestamp(records: list[SnapshotRecord]) -> str:
    """Obtiene el timestamp más reciente en formato corto.

    Args:
        records (list[SnapshotRecord]): Lista de snapshots.

    Returns:
        str: Timestamp formateado o texto alternativo.

    English:
        Gets the latest timestamp in short format.

    Args:
        records (list[SnapshotRecord]): Snapshot list.

    Returns:
        str: Formatted timestamp or fallback text.
    """
    for record in records:
        if record.timestamp:
            return record.timestamp.strftime("%Y-%m-%d %H:%M")
    return "sin fecha"


def get_alerts() -> list[dict]:
    """Carga alertas desde JSON o logs de texto.

    Returns:
        list[dict]: Lista de alertas disponibles.

    English:
        Loads alerts from JSON or text logs.

    Returns:
        list[dict]: Available alerts.
    """
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
            return [
                {"timestamp": "", "descripcion": line} for line in lines if line.strip()
            ]
        except OSError as exc:
            logger.error("alerts_log_failed error=%s", exc)
    return []


async def enforce_access(update: Update) -> bool:
    """Valida si el chat tiene permisos para usar el bot.

    Args:
        update (Update): Evento recibido de Telegram.

    Returns:
        bool: True si tiene acceso, False si se bloquea.

    English:
        Validates whether the chat has access to the bot.

    Args:
        update (Update): Telegram update event.

    Returns:
        bool: True if access is allowed, False otherwise.
    """
    chat = update.effective_chat
    if not chat:
        return False
    allowed = os.getenv("TELEGRAM_CHAT_ID")
    if allowed:
        try:
            if int(allowed) != chat.id:
                await update.message.reply_text(
                    build_disclaimer(
                        "Este bot está en modo privado. No tienes acceso."
                    ),
                )
                return False
        except ValueError:
            return True
    return True


async def preflight(update: Update) -> bool:
    """Ejecuta validaciones de acceso y rate limit antes de responder.

    Args:
        update (Update): Evento recibido de Telegram.

    Returns:
        bool: True si el comando puede continuar.

    English:
        Runs access and rate-limit checks before responding.

    Args:
        update (Update): Telegram update event.

    Returns:
        bool: True if the command can proceed.
    """
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
    """Genera la lista de comandos disponibles por modo.

    Args:
        mode (str): Modo actual (ciudadano o auditor).

    Returns:
        str: Lista de comandos en formato texto.

    English:
        Builds the list of available commands for a mode.

    Args:
        mode (str): Current mode (citizen or auditor).

    Returns:
        str: Text list of commands.
    """
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
    """Comando de bienvenida e inicio del bot.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Welcome command for the bot.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
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
    """Permite al usuario seleccionar modo ciudadano o auditor.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Lets the user pick citizen or auditor mode.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
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
    """Muestra el último snapshot disponible.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Shows the latest available snapshot.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(
            build_disclaimer("No hay datos disponibles todavía."),
        )
        return
    latest = records[0]
    timestamp = (
        latest.timestamp.strftime("%Y-%m-%d %H:%M") if latest.timestamp else "N/D"
    )
    porcentaje = format_number(latest.porcentaje_escrutado)
    votos = format_number(latest.total_votos)
    message = (
        f"¡Última actualización a las {timestamp}! "
        f"{porcentaje}% escrutado, {votos} votos totales."
    )
    logger.info("cmd_ultimo chat_id=%s", update.effective_chat.id)
    await update.message.reply_text(build_disclaimer(message))


def resolve_range_argument(
    records: list[SnapshotRecord], args: list[str]
) -> tuple[RangeQuery | None, str | None]:
    """Resuelve el argumento de rango y valida errores de formato.

    Args:
        records (list[SnapshotRecord]): Lista de snapshots.
        args (list[str]): Argumentos del comando.

    Returns:
        tuple[RangeQuery | None, str | None]: Rango interpretado y error si aplica.

    English:
        Resolves the range argument and validates format errors.

    Args:
        records (list[SnapshotRecord]): Snapshot list.
        args (list[str]): Command arguments.

    Returns:
        tuple[RangeQuery | None, str | None]: Parsed range and error message if any.
    """
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
    """Muestra cambios entre snapshots en un rango.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Shows snapshot changes within a range.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(
            build_disclaimer("No hay datos disponibles todavía.")
        )
        return
    query, error = resolve_range_argument(records, context.args)
    if error:
        await update.message.reply_text(build_disclaimer(error))
        return
    filtered = list(reversed(filter_snapshots(records, query)))
    if len(filtered) < 2:
        latest_time = get_latest_timestamp(records)
        await update.message.reply_text(
            build_disclaimer(
                f"No hay información en ese rango. Último disponible: {latest_time}."
            ),
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
    logger.info(
        "cmd_cambios chat_id=%s range=%s",
        update.effective_chat.id,
        query.label if query else "todo",
    )
    await update.message.reply_text(build_disclaimer(message))


async def alertas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra alertas recientes registradas.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Shows recent recorded alerts.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
        return
    alerts = get_alerts()
    if not alerts:
        await update.message.reply_text(
            build_disclaimer("No hay alertas registradas por ahora.")
        )
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
    """Genera un gráfico de la Ley de Benford.

    Args:
        votes (list[int]): Lista de votos para analizar.
        title (str): Título del gráfico.

    Returns:
        BytesIO: Imagen PNG en memoria.

    English:
        Generates a Benford's Law chart.

    Args:
        votes (list[int]): Vote list to analyze.
        title (str): Chart title.

    Returns:
        BytesIO: In-memory PNG image.
    """
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
    """Envía un gráfico Benford según el rango solicitado.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Sends a Benford chart for the requested range.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(
            build_disclaimer("No hay datos disponibles todavía.")
        )
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
            build_disclaimer(
                f"No hay información suficiente en ese rango. Último disponible: {latest_time}."
            ),
        )
        return
    title = f"Benford ({query.label if query else 'todo'})"
    chart = build_benford_chart(votes, title)
    caption = build_disclaimer("Gráfico Benford generado.")
    logger.info(
        "cmd_grafico chat_id=%s range=%s",
        update.effective_chat.id,
        query.label if query else "todo",
    )
    await update.message.reply_photo(photo=chart, caption=caption)


def build_trend_chart(points: list[tuple[datetime, float]], label: str) -> BytesIO:
    """Genera un gráfico de tendencia simple.

    Args:
        points (list[tuple[datetime, float]]): Puntos de la serie.
        label (str): Etiqueta del gráfico.

    Returns:
        BytesIO: Imagen PNG en memoria.

    English:
        Builds a simple trend chart.

    Args:
        points (list[tuple[datetime, float]]): Series points.
        label (str): Chart label.

    Returns:
        BytesIO: In-memory PNG image.
    """
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
    """Envía una gráfica de tendencia de votos o escrutinio.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Sends a trend chart for votes or scrutiny percentage.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(
            build_disclaimer("No hay datos disponibles todavía.")
        )
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
        if value is None:
            value = (
                float(record.total_votos) if record.total_votos is not None else None
            )
        if value is not None:
            points.append((record.timestamp, value))
    if len(points) < 2:
        latest_time = get_latest_timestamp(records)
        await update.message.reply_text(
            build_disclaimer(
                f"No hay información en ese rango. Último disponible: {latest_time}."
            ),
        )
        return
    chart = build_trend_chart(points, f"Tendencia ({query.label if query else 'todo'})")
    caption = build_disclaimer("Tendencia generada.")
    logger.info("cmd_tendencia chat_id=%s", update.effective_chat.id)
    await update.message.reply_photo(photo=chart, caption=caption)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un resumen rápido del rango solicitado.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Sends a quick summary for the requested range.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(
            build_disclaimer("No hay datos disponibles todavía.")
        )
        return
    query, error = resolve_range_argument(records, context.args)
    if error:
        await update.message.reply_text(build_disclaimer(error))
        return
    filtered = filter_snapshots(records, query)
    if not filtered:
        latest_time = get_latest_timestamp(records)
        await update.message.reply_text(
            build_disclaimer(
                f"No hay información en ese rango. Último disponible: {latest_time}."
            ),
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


def find_snapshot_by_query(
    query: str, records: list[SnapshotRecord]
) -> SnapshotRecord | None:
    """Busca un snapshot por coincidencia en el nombre.

    Args:
        query (str): Texto de búsqueda.
        records (list[SnapshotRecord]): Lista de snapshots.

    Returns:
        SnapshotRecord | None: Registro encontrado o None.

    English:
        Finds a snapshot by matching its file name.

    Args:
        query (str): Search text.
        records (list[SnapshotRecord]): Snapshot list.

    Returns:
        SnapshotRecord | None: Found record or None.
    """
    if not query:
        return records[0] if records else None
    lower = query.lower()
    for record in records:
        if lower in record.path.name.lower():
            return record
    return None


def find_hash_for_snapshot(snapshot_path: Path) -> str | None:
    """Busca el hash asociado a un snapshot.

    Args:
        snapshot_path (Path): Ruta del snapshot.

    Returns:
        str | None: Hash encontrado o None.

    English:
        Finds the hash associated with a snapshot.

    Args:
        snapshot_path (Path): Snapshot path.

    Returns:
        str | None: Hash value or None.
    """
    hash_path = HASH_DIR / f"{snapshot_path.name}.sha256"
    if hash_path.exists():
        try:
            return hash_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.error("hash_read_failed path=%s error=%s", hash_path, exc)
            return None
    return None


async def hash_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde con el hash SHA-256 de un snapshot.

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Replies with the SHA-256 hash of a snapshot.

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
        return
    if get_mode(update.effective_chat.id) != MODE_AUDITOR:
        await update.message.reply_text(
            build_disclaimer(
                "Este comando es solo para modo auditor. Escribe 'auditor' para activarlo."
            ),
        )
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(
            build_disclaimer("No hay datos disponibles todavía.")
        )
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
    message = f"Hash SHA-256 de {record.path.name}: {hash_value}."
    logger.info("cmd_hash chat_id=%s query=%s", update.effective_chat.id, query)
    await update.message.reply_text(build_disclaimer(message))


def select_json_record(
    records: list[SnapshotRecord], query_text: str
) -> SnapshotRecord | None:
    """Selecciona un snapshot por departamento o nombre.

    Args:
        records (list[SnapshotRecord]): Lista de snapshots.
        query_text (str): Texto de búsqueda.

    Returns:
        SnapshotRecord | None: Registro encontrado o None.

    English:
        Selects a snapshot by department or file name.

    Args:
        records (list[SnapshotRecord]): Snapshot list.
        query_text (str): Search text.

    Returns:
        SnapshotRecord | None: Found record or None.
    """
    if not query_text:
        return records[0] if records else None
    lower = query_text.lower()
    for record in records:
        if record.departamento and lower in str(record.departamento).lower():
            return record
    return find_snapshot_by_query(query_text, records)


async def json_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entrega el JSON crudo de un snapshot (modo auditor).

    Args:
        update (Update): Evento recibido.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Sends raw snapshot JSON (auditor mode).

    Args:
        update (Update): Incoming update.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    if (
        not update.message
        or not await enforce_access(update)
        or not await preflight(update)
    ):
        return
    if get_mode(update.effective_chat.id) != MODE_AUDITOR:
        await update.message.reply_text(
            build_disclaimer(
                "Este comando es solo para modo auditor. Escribe 'auditor' para activarlo."
            ),
        )
        return
    records = load_snapshots()
    if not records:
        await update.message.reply_text(
            build_disclaimer("No hay datos disponibles todavía.")
        )
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
    """Maneja errores inesperados del bot.

    Args:
        update (object): Evento que causó el error.
        context (ContextTypes.DEFAULT_TYPE): Contexto del bot.

    English:
        Handles unexpected bot errors.

    Args:
        update (object): Update that caused the error.
        context (ContextTypes.DEFAULT_TYPE): Bot context.
    """
    logger.error("telegram_error update=%s error=%s", update, context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            build_disclaimer("Ocurrió un error inesperado. Intenta nuevamente."),
        )


def build_application(token: str):
    """Construye la aplicación del bot con handlers registrados.

    Args:
        token (str): Token de Telegram.

    Returns:
        Application: Aplicación lista para iniciar.

    English:
        Builds the bot application with registered handlers.

    Args:
        token (str): Telegram token.

    Returns:
        Application: Ready-to-run application.
    """
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
    """Punto de entrada principal del bot.

    Raises:
        SystemExit: Si no se encuentra el token de Telegram.

    English:
        Main entry point for the bot.

    Raises:
        SystemExit: When the Telegram token is missing.
    """
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_TOKEN en .env o variables de entorno.")
    application = build_application(token)
    logger.info("telegram_bot_start")
    application.run_polling()


if __name__ == "__main__":
    main()
