"""Encrypted multi-destination backup for critical Centinel state.
Bilingual: Backup cifrado multi-destino para estado critico de Centinel.

After each successful scrape or health-state save, this module creates an
AES-256 encrypted (Fernet) backup of critical files and distributes copies
to local storage, Dropbox, and (stub) S3.

Despues de cada scrape exitoso o guardado de estado de salud, este modulo crea
un backup cifrado AES-256 (Fernet) de archivos criticos y distribuye copias
a almacenamiento local, Dropbox, y (stub) S3.

Error handling is intentionally silent to never interrupt the main scraper.
El manejo de errores es intencionalmente silencioso para nunca interrumpir el scraper principal.
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Encryption helpers / Helpers de cifrado
# ---------------------------------------------------------------------------

try:
    from cryptography.fernet import Fernet
    _HAS_FERNET = True
except ImportError:
    _HAS_FERNET = False
    logger.warning(
        "cryptography.fernet not available, backups will be unencrypted / "
        "cryptography.fernet no disponible, backups seran sin cifrar"
    )

# Dropbox SDK availability / Disponibilidad del SDK de Dropbox
try:
    import dropbox  # type: ignore[import-untyped]
    _HAS_DROPBOX = True
except ImportError:
    _HAS_DROPBOX = False

# Boto3 SDK availability / Disponibilidad del SDK de Boto3
try:
    import boto3  # type: ignore[import-untyped]
    _HAS_BOTO3 = True
except ImportError:
    _HAS_BOTO3 = False


def _get_fernet_key() -> Optional[bytes]:
    """Retrieve the Fernet encryption key from environment or secrets file.
    Bilingual: Obtiene la clave de cifrado Fernet del entorno o archivo de secretos.

    Looks for CENTINEL_BACKUP_KEY in environment variables first, then
    falls back to ``config/secrets/backup_key.txt``.

    Returns:
        Fernet key bytes, or None if unavailable.
    """
    # Environment variable first / Variable de entorno primero
    env_key: Optional[str] = os.getenv("CENTINEL_BACKUP_KEY")
    if env_key:
        return env_key.encode("utf-8")

    # Fallback to secrets file / Fallback a archivo de secretos
    secrets_path: Path = Path("config/secrets/backup_key.txt")
    if secrets_path.exists():
        key_text: str = secrets_path.read_text(encoding="utf-8").strip()
        if key_text:
            return key_text.encode("utf-8")

    return None


def _encrypt_data(data: bytes) -> bytes:
    """Encrypt raw bytes with Fernet AES-256.
    Bilingual: Cifra bytes crudos con Fernet AES-256.

    Args:
        data: Raw bytes to encrypt.

    Returns:
        Encrypted bytes. Returns original data if encryption is unavailable.
    """
    if not _HAS_FERNET:
        logger.warning(
            "Fernet unavailable, returning raw data / "
            "Fernet no disponible, retornando datos crudos"
        )
        return data

    key: Optional[bytes] = _get_fernet_key()
    if not key:
        logger.warning(
            "No backup encryption key found, returning raw data / "
            "No se encontro clave de cifrado para backup, retornando datos crudos"
        )
        return data

    try:
        fernet: Fernet = Fernet(key)
        return fernet.encrypt(data)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Encryption failed, returning raw data / "
            "Cifrado fallo, retornando datos crudos: %s",
            exc,
        )
        return data


def _timestamp_str() -> str:
    """Generate a UTC timestamp string for backup filenames.
    Bilingual: Genera una cadena de timestamp UTC para nombres de archivo de backup.

    Returns:
        ISO-style timestamp safe for filenames.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Backup destinations / Destinos de backup
# ---------------------------------------------------------------------------

def _backup_local(encrypted_data: bytes, filename: str) -> bool:
    """Save encrypted backup to local ./backups/encrypted/ directory.
    Bilingual: Guarda backup cifrado en directorio local ./backups/encrypted/.

    Args:
        encrypted_data: Encrypted bytes to save.
        filename: Target filename (with timestamp).

    Returns:
        True if backup succeeded, False otherwise.
    """
    try:
        backup_dir: Path = Path("backups/encrypted")
        backup_dir.mkdir(parents=True, exist_ok=True)
        target: Path = backup_dir / filename
        target.write_bytes(encrypted_data)
        logger.info(
            "Local backup saved / Backup local guardado: %s (%d bytes)",
            target,
            len(encrypted_data),
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Local backup failed / Backup local fallo: %s",
            exc,
        )
        return False


def _backup_dropbox(encrypted_data: bytes, filename: str) -> bool:
    """Upload encrypted backup to Dropbox.
    Bilingual: Sube backup cifrado a Dropbox.

    Requires DROPBOX_ACCESS_TOKEN environment variable and dropbox SDK.

    Args:
        encrypted_data: Encrypted bytes to upload.
        filename: Target filename in Dropbox.

    Returns:
        True if upload succeeded, False otherwise.
    """
    if not _HAS_DROPBOX:
        logger.debug(
            "Dropbox SDK not available, skipping / SDK de Dropbox no disponible, omitiendo"
        )
        return False

    token: Optional[str] = os.getenv("DROPBOX_ACCESS_TOKEN")
    if not token:
        logger.debug(
            "DROPBOX_ACCESS_TOKEN not set, skipping / DROPBOX_ACCESS_TOKEN no definido, omitiendo"
        )
        return False

    try:
        dbx = dropbox.Dropbox(token)
        remote_path: str = f"/centinel_backups/{filename}"
        dbx.files_upload(
            encrypted_data,
            remote_path,
            mode=dropbox.files.WriteMode.overwrite,
        )
        logger.info(
            "Dropbox backup uploaded / Backup de Dropbox subido: %s",
            remote_path,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Dropbox backup failed / Backup de Dropbox fallo: %s",
            exc,
        )
        return False


def _backup_s3(encrypted_data: bytes, filename: str) -> bool:
    """Upload encrypted backup to S3 (stub, requires boto3 and config).
    Bilingual: Sube backup cifrado a S3 (stub, requiere boto3 y configuracion).

    Requires AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and
    CENTINEL_S3_BUCKET environment variables.

    Args:
        encrypted_data: Encrypted bytes to upload.
        filename: Target object key in S3.

    Returns:
        True if upload succeeded, False otherwise.
    """
    if not _HAS_BOTO3:
        logger.debug(
            "boto3 not available, skipping S3 backup / boto3 no disponible, omitiendo backup S3"
        )
        return False

    bucket: Optional[str] = os.getenv("CENTINEL_S3_BUCKET")
    if not bucket:
        logger.debug(
            "CENTINEL_S3_BUCKET not set, skipping S3 backup / "
            "CENTINEL_S3_BUCKET no definido, omitiendo backup S3"
        )
        return False

    try:
        s3_client = boto3.client("s3")
        s3_key: str = f"centinel_backups/{filename}"
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=encrypted_data,
            ServerSideEncryption="AES256",
        )
        logger.info(
            "S3 backup uploaded / Backup S3 subido: s3://%s/%s",
            bucket,
            s3_key,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "S3 backup failed / Backup S3 fallo: %s",
            exc,
        )
        return False


# ---------------------------------------------------------------------------
# Main backup orchestrator / Orquestador principal de backup
# ---------------------------------------------------------------------------

# Minimum seconds between backup runs to avoid excessive I/O /
# Segundos minimos entre ejecuciones de backup para evitar I/O excesivo
_MIN_BACKUP_INTERVAL_SECONDS: float = 1800.0  # 30 minutes / 30 minutos
_last_backup_time: float = 0.0


def backup_critical(
    *,
    force: bool = False,
    health_state_path: str = "data/health_state.json",
    chain_path: str = "data/hashes/chain.json",
) -> Dict[str, Any]:
    """Create encrypted backups of critical state files to all configured destinations.
    Bilingual: Crea backups cifrados de archivos de estado criticos a todos los destinos configurados.

    This function is designed to NEVER raise exceptions to protect the main
    scraping pipeline. All errors are logged and silently handled.

    Esta funcion esta disenada para NUNCA lanzar excepciones para proteger el
    pipeline principal de scraping. Todos los errores se registran y manejan silenciosamente.

    Args:
        force: If True, bypass the minimum interval check.
               Si True, omitir la verificacion de intervalo minimo.
        health_state_path: Path to health_state.json.
        chain_path: Path to chain.json (hash chain).

    Returns:
        Dictionary with backup status per destination:
        ``{"local": bool, "dropbox": bool, "s3": bool, "skipped": bool}``.
    """
    global _last_backup_time

    result: Dict[str, Any] = {
        "local": False,
        "dropbox": False,
        "s3": False,
        "skipped": False,
        "timestamp": _timestamp_str(),
    }

    try:
        # Throttle: enforce minimum interval / Regulacion: forzar intervalo minimo
        now: float = time.monotonic()
        if not force and (_last_backup_time > 0 and now - _last_backup_time < _MIN_BACKUP_INTERVAL_SECONDS):
            logger.debug(
                "Backup skipped: within minimum interval / "
                "Backup omitido: dentro del intervalo minimo"
            )
            result["skipped"] = True
            return result

        # Collect files to backup / Recolectar archivos para backup
        files_to_backup: Dict[str, Path] = {}
        for label, path_str in [("health_state", health_state_path), ("chain", chain_path)]:
            p: Path = Path(path_str)
            if p.exists():
                files_to_backup[label] = p
            else:
                logger.debug(
                    "Backup source not found, skipping / "
                    "Fuente de backup no encontrada, omitiendo: %s",
                    p,
                )

        if not files_to_backup:
            logger.info(
                "No critical files to backup / No hay archivos criticos para backup"
            )
            result["skipped"] = True
            return result

        # Bundle files into a single JSON payload / Empaquetar archivos en un solo payload JSON
        bundle: Dict[str, Any] = {
            "backup_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "files": {},
        }
        for label, file_path in files_to_backup.items():
            try:
                content: str = file_path.read_text(encoding="utf-8")
                # Try to parse as JSON for clean bundling / Intentar parsear como JSON
                bundle["files"][label] = {
                    "path": str(file_path),
                    "content": json.loads(content) if content.strip() else {},
                }
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "Could not read backup file / No se pudo leer archivo de backup: %s (%s)",
                    file_path,
                    exc,
                )

        if not bundle["files"]:
            result["skipped"] = True
            return result

        # Serialize and encrypt / Serializar y cifrar
        raw_bytes: bytes = json.dumps(bundle, indent=2, ensure_ascii=False).encode("utf-8")
        encrypted: bytes = _encrypt_data(raw_bytes)

        # Distribute to all destinations / Distribuir a todos los destinos
        ts: str = _timestamp_str()
        filename: str = f"centinel_backup_{ts}.enc"

        result["local"] = _backup_local(encrypted, filename)
        result["dropbox"] = _backup_dropbox(encrypted, filename)
        result["s3"] = _backup_s3(encrypted, filename)

        _last_backup_time = now

        successful_destinations: List[str] = [k for k in ("local", "dropbox", "s3") if result[k]]
        logger.info(
            "Backup completed to %d destination(s): %s / "
            "Backup completado a %d destino(s): %s",
            len(successful_destinations),
            ", ".join(successful_destinations) or "none",
            len(successful_destinations),
            ", ".join(successful_destinations) or "ninguno",
        )

    except Exception as exc:  # noqa: BLE001
        # NEVER let backup errors propagate to main pipeline /
        # NUNCA dejar que errores de backup se propaguen al pipeline principal
        logger.error(
            "Backup orchestration failed silently / "
            "Orquestacion de backup fallo silenciosamente: %s",
            exc,
        )

    return result


def generate_backup_key() -> str:
    """Generate a new Fernet encryption key (utility for initial setup).
    Bilingual: Genera una nueva clave de cifrado Fernet (utilidad para setup inicial).

    Returns:
        Base64-encoded Fernet key string.

    Raises:
        RuntimeError: If cryptography library is not available.
    """
    if not _HAS_FERNET:
        raise RuntimeError(
            "cryptography library required / Libreria cryptography requerida"
        )
    return Fernet.generate_key().decode("utf-8")
