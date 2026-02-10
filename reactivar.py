#!/usr/bin/env python3
"""Reactivar pipeline después de modo pánico."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import yaml

from scripts.logging_utils import configure_logging

DATA_DIR = Path("data")
PANIC_FLAG_PATH = DATA_DIR / "panic_mode.json"
CONFIG_PATHS = [
    Path("command_center") / "config.yaml",
    Path("config") / "config.yaml",
    Path("config.yaml"),
]

logger = configure_logging("centinel.reactivar", log_file="logs/centinel.log")


def utc_now() -> datetime:
    """Español: Función utc_now del módulo reactivar.py.

    English: Function utc_now defined in reactivar.py.
    """
    return datetime.now(timezone.utc)


def load_yaml(path: Path) -> dict[str, Any]:
    """Español: Función load_yaml del módulo reactivar.py.

    English: Function load_yaml defined in reactivar.py.
    """
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        logger.error("reactivar_config_invalid path=%s error=%s", path, exc)
        return {}


def update_master_switch(status: str) -> list[Path]:
    """Español: Función update_master_switch del módulo reactivar.py.

    English: Function update_master_switch defined in reactivar.py.
    """
    updated: list[Path] = []
    for path in CONFIG_PATHS:
        if not path.exists():
            continue
        config = load_yaml(path)
        if not isinstance(config, dict):
            logger.warning("reactivar_config_not_dict path=%s", path)
            continue
        config["master_switch"] = status
        path.write_text(
            yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        updated.append(path)
    return updated


def clear_panic_flag(user: str, timestamp: str) -> dict[str, Any]:
    """Español: Función clear_panic_flag del módulo reactivar.py.

    English: Function clear_panic_flag defined in reactivar.py.
    """
    payload = {
        "active": False,
        "user": user,
        "timestamp": timestamp,
        "reason": "panic_cleared",
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PANIC_FLAG_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def build_s3_client() -> tuple[Any | None, str | None]:
    """Español: Función build_s3_client del módulo reactivar.py.

    English: Function build_s3_client defined in reactivar.py.
    """
    bucket = os.getenv("CENTINEL_PANIC_BUCKET") or os.getenv("CENTINEL_CHECKPOINT_BUCKET")
    if not bucket:
        return None, None
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=os.getenv("CENTINEL_S3_ENDPOINT"),
        region_name=os.getenv("CENTINEL_S3_REGION"),
        aws_access_key_id=os.getenv("CENTINEL_S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("CENTINEL_S3_SECRET_KEY"),
    )
    return client, bucket


def upload_clear_flag(client: Any, bucket: str, payload: dict[str, Any]) -> None:
    """Español: Función upload_clear_flag del módulo reactivar.py.

    English: Function upload_clear_flag defined in reactivar.py.
    """
    key = "panic/active.json"
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def main() -> int:
    """Español: Función main del módulo reactivar.py.

    English: Function main defined in reactivar.py.
    """
    parser = argparse.ArgumentParser(description="Reactiva el pipeline tras modo pánico.")
    parser.add_argument("--user", help="Usuario que reactivó el sistema.")
    args = parser.parse_args()

    user = args.user or os.getenv("PANIC_USER") or getpass.getuser()
    timestamp = utc_now().isoformat()

    payload = clear_panic_flag(user, timestamp)
    updated = update_master_switch("ON")
    logger.info("reactivar_master_switch_on paths=%s", [p.as_posix() for p in updated])

    try:
        client, bucket = build_s3_client()
        if client and bucket:
            upload_clear_flag(client, bucket, payload)
            logger.info("reactivar_bucket_flag_set bucket=%s", bucket)
    except Exception as exc:  # noqa: BLE001
        logger.error("reactivar_bucket_failed error=%s", exc)

    logger.info("reactivar_complete user=%s timestamp=%s", user, timestamp)
    print("[+] Sistema reactivado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
