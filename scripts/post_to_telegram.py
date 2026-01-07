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
    """
    Lee el hash previamente generado por download_and_hash.py
    para asegurar consistencia total entre Git y Telegram.
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
    """
    Formatea el reporte con estilo técnico neutro.
    """
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    header = (
        "<b>HND-SENTINEL-2029 | TECHNICAL NOTICE</b>\n"
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
    return format_as_neutral


def send_message(text, stored_hash=None, template_name=None):
    if not TOKEN or not CHAT_ID:
        logger.error("telegram_credentials_missing")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    formatter = resolve_template(template_name or DEFAULT_TEMPLATE)
    payload = {
        "chat_id": CHAT_ID,
        "text": formatter(text, stored_hash),
        "parse_mode": "HTML",
        "disable_web_page_preview": True
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
