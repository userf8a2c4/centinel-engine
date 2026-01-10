"""Publica mensajes en Telegram con hashes verificables.

English:
    Posts messages to Telegram with verifiable hashes.
"""

import datetime
import logging
import os
import sys

import requests
from dotenv import load_dotenv

from sentinel.utils.logging_config import setup_logging

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DEFAULT_TEMPLATE = os.getenv("TELEGRAM_TEMPLATE", "neutral").strip().lower()

setup_logging()
logger = logging.getLogger(__name__)


def get_stored_hash(hash_path):
    """Lee el hash generado para asegurar consistencia con Git y Telegram.

    Args:
        hash_path (str): Ruta al archivo .sha256.

    Returns:
        str: Hash leído o mensaje de error.

    English:
        Reads the stored hash to keep Git and Telegram consistent.

    Args:
        hash_path (str): Path to the .sha256 file.

    Returns:
        str: Read hash or an error message.
    """
    try:
        with open(hash_path, "r") as f:
            # Extrae solo el hash (asumiendo formato estándar: hash filename)
            content = f.read().strip().split()[0]
            return content
    except Exception as e:
        logger.error("hash_read_failed path=%s error=%s", hash_path, e)
        return f"HASH_READ_ERROR: {str(e)}"


def format_as_neutral(raw_data, stored_hash=None):
    """Formatea el reporte con estilo técnico neutro.

    Args:
        raw_data (str): Texto base del reporte.
        stored_hash (str | None): Hash opcional para verificación.

    Returns:
        str: Texto formateado en HTML.

    English:
        Formats the report using a neutral technical style.

    Args:
        raw_data (str): Base report text.
        stored_hash (str | None): Optional verification hash.

    Returns:
        str: HTML-formatted message.
    """
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    header = (
        "<b>Proyecto C.E.N.T.I.N.E.L. | TECHNICAL NOTICE</b>\n"
        f"<code>Timestamp (UTC): {timestamp}</code>\n"
        "--------------------------------------------------\n\n"
    )

    hash_section = ""
    if stored_hash:
        hash_section = (
            f"\n--------------------------------------------------\n"
            f"<code>Verification hash (SHA-256):</code>\n"
            f"<code>{stored_hash}</code>"
        )

    footer = (
        "\n--------------------------------------------------\n"
        "<b>Publication generated from public data. Reproducible by third parties.</b>"
    )

    return f"{header}{raw_data}{hash_section}{footer}"


def resolve_template(template_name):
    """Selecciona el formateador de mensaje según la plantilla.

    Args:
        template_name (str | None): Nombre de la plantilla solicitada.

    Returns:
        callable: Función que formatea el texto final.

    English:
        Selects the formatter function based on a template name.

    Args:
        template_name (str | None): Requested template name.

    Returns:
        callable: Function that formats the final message.
    """
    return format_as_neutral


def send_message(text, stored_hash=None, template_name=None):
    """Envía un mensaje a Telegram usando la API oficial.

    Args:
        text (str): Texto del mensaje.
        stored_hash (str | None): Hash opcional para verificación.
        template_name (str | None): Plantilla de formato.

    Raises:
        SystemExit: Si faltan credenciales o falla el envío.

    English:
        Sends a message to Telegram using the official API.

    Args:
        text (str): Message text.
        stored_hash (str | None): Optional verification hash.
        template_name (str | None): Formatting template.

    Raises:
        SystemExit: When credentials are missing or send fails.
    """
    if not TOKEN or not CHAT_ID:
        logger.error("telegram_credentials_missing")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    formatter = resolve_template(template_name or DEFAULT_TEMPLATE)
    payload = {
        "chat_id": CHAT_ID,
        "text": formatter(text, stored_hash),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        logger.info("telegram_message_sent status_code=%s", response.status_code)
        logger.info("telegram_send_success status_code=%s", response.status_code)
    except Exception as e:
        logger.error("telegram_message_failed error=%s", e)
        logger.error("telegram_send_failed error=%s", e)
        sys.exit(1)


if __name__ == "__main__":
    # Uso esperado desde GitHub Actions:
    # python scripts/post_to_telegram.py "Mensaje técnico" "hashes/snapshot_XXXX.json.sha256" neutral

    if len(sys.argv) > 2:
        msg = sys.argv[1]
        hash_file_path = sys.argv[2]
        file_hash = get_stored_hash(hash_file_path)
        template = sys.argv[3] if len(sys.argv) > 3 else None
        send_message(msg, file_hash, template_name=template)
    elif len(sys.argv) == 2:
        send_message(sys.argv[1])
    else:
        # Heartbeat bilingüe si se ejecuta sin argumentos
        heartbeat = (
            "<b>[EN] SYSTEM_STATUS:</b> Operational. Data flow synchronized.\n"
            "<b>[ES] ESTADO_DEL_SISTEMA:</b> Operativo. Flujo de datos sincronizado."
        )
        send_message(heartbeat)
