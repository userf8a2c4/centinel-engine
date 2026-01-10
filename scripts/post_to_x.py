import datetime
import os
import sys

import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1

load_dotenv()

API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")


def get_stored_hash(hash_path):
    try:
        with open(hash_path, "r") as f:
            content = f.read().strip().split()[0]
            return content
    except Exception as e:
        return f"HASH_READ_ERROR: {str(e)}"


def format_as_neutral(raw_data, stored_hash=None):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    hash_line = f"\nVerification hash (SHA-256): {stored_hash}" if stored_hash else ""
    return (
        "Proyecto C.E.N.T.I.N.E.L. | TECHNICAL NOTICE\n"
        f"Timestamp (UTC): {timestamp}\n"
        f"{raw_data}"
        f"{hash_line}\n"
        "Publication generated from public data. Reproducible by third parties."
    )


def send_message(text, stored_hash=None):
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        print("[!] ERROR: X_CREDENTIALS_MISSING")
        sys.exit(1)

    url = "https://api.x.com/2/tweets"
    auth = OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    payload = {"text": text}

    try:
        response = requests.post(url, auth=auth, json=payload, timeout=15)
        response.raise_for_status()
        print("[+] STATUS: X_TRANSMISSION_SUCCESSFUL")
    except Exception as e:
        print(f"[!] STATUS: X_TRANSMISSION_FAILED // ERR: {str(e)}")
        sys.exit(1)


def truncate_for_x(text, limit=280):
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


if __name__ == "__main__":
    # Uso esperado desde GitHub Actions:
    # python scripts/post_to_x.py "Mensaje técnico" "hashes/snapshot_XXXX.json.sha256"

    if len(sys.argv) > 2:
        msg = sys.argv[1]
        hash_file_path = sys.argv[2]
        file_hash = get_stored_hash(hash_file_path)
        formatted = format_as_neutral(msg, file_hash)
        send_message(truncate_for_x(formatted))
    elif len(sys.argv) == 2:
        formatted = format_as_neutral(sys.argv[1])
        send_message(truncate_for_x(formatted))
    else:
        heartbeat = (
            "SYSTEM_STATUS: Operational. Data flow synchronized. " "Technical notice."
        )
        send_message(truncate_for_x(format_as_neutral(heartbeat)))
