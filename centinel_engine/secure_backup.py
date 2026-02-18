"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `centinel_engine/secure_backup.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - _generate_backup_key
  - _get_fernet
  - _encrypt_data
  - _compute_sha256
  - _collect_hash_chain_files
  - _build_backup_manifest
  - _backup_to_local
  - _backup_to_dropbox
  - _backup_to_s3
  - backup_critical_assets
  - backup_critical
  - BackupScheduler

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `centinel_engine/secure_backup.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - _generate_backup_key
  - _get_fernet
  - _encrypt_data
  - _compute_sha256
  - _collect_hash_chain_files
  - _build_backup_manifest
  - _backup_to_local
  - _backup_to_dropbox
  - _backup_to_s3
  - backup_critical_assets
  - backup_critical
  - BackupScheduler

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet

    _HAS_CRYPTOGRAPHY = True
except Exception:  # noqa: BLE001
    Fernet = None  # type: ignore[assignment]
    _HAS_CRYPTOGRAPHY = False

try:
    import dropbox  # type: ignore[import-untyped]

    _HAS_DROPBOX = True
except Exception:  # noqa: BLE001
    _HAS_DROPBOX = False

try:
    import boto3  # type: ignore[import-untyped]

    _HAS_BOTO3 = True
except Exception:  # noqa: BLE001
    _HAS_BOTO3 = False

DEFAULT_HEALTH_STATE_PATH = Path("data/health_state.json")
DEFAULT_HASH_CHAIN_DIR = Path("data/hashes")
DEFAULT_BACKUP_DIR = Path("backups")
DEFAULT_BACKUP_INTERVAL_SECONDS = 1800

ENV_BACKUP_KEY = "CENTINEL_BACKUP_KEY"
ENV_DROPBOX_TOKEN = "CENTINEL_DROPBOX_TOKEN"
ENV_DROPBOX_FOLDER = "CENTINEL_DROPBOX_FOLDER"
ENV_S3_BUCKET = "CENTINEL_S3_BUCKET"
ENV_S3_PREFIX = "CENTINEL_S3_PREFIX"


def _generate_backup_key() -> bytes:
    """Generate an ephemeral Fernet key when no configured key exists.

    Bilingual: Genera una clave Fernet efímera cuando no hay clave configurada.

    Args:
        None.

    Returns:
        bytes: Base64-encoded Fernet key.

    Raises:
        RuntimeError: If cryptography support is unavailable.
    """
    if not _HAS_CRYPTOGRAPHY:
        raise RuntimeError("cryptography is required for key generation")
    key = Fernet.generate_key()
    logger.warning("backup_key_ephemeral | using temporary key")
    return key


def _get_fernet() -> Optional[Any]:
    """Build Fernet encryptor from environment key or ephemeral fallback.

    Bilingual: Crea cifrador Fernet desde entorno o fallback efímero.

    Args:
        None.

    Returns:
        Optional[Any]: Fernet instance or None if crypto is unavailable.

    Raises:
        None.
    """
    if not _HAS_CRYPTOGRAPHY:
        return None
    key = os.getenv(ENV_BACKUP_KEY)
    if key:
        try:
            return Fernet(key.encode("utf-8"))
        except Exception:  # noqa: BLE001
            logger.error("backup_key_invalid | ignoring configured key")
    return Fernet(_generate_backup_key())


def _encrypt_data(data: bytes, fernet: Optional[Any] = None) -> bytes:
    """Encrypt payload bytes, or return plaintext when encryption is unavailable.

    Bilingual: Cifra bytes del payload o retorna texto plano si no hay cifrado.

    Args:
        data: Raw bytes payload.
        fernet: Optional Fernet instance.

    Returns:
        bytes: Encrypted or plaintext payload.

    Raises:
        None.
    """
    return fernet.encrypt(data) if fernet is not None else data


def _compute_sha256(data: bytes) -> str:
    """Compute SHA-256 digest for integrity manifest.

    Bilingual: Calcula digest SHA-256 para manifiesto de integridad.

    Args:
        data: Raw bytes payload.

    Returns:
        str: Hex-encoded SHA-256 digest.

    Raises:
        None.
    """
    return hashlib.sha256(data).hexdigest()


def _collect_hash_chain_files(hash_dir: Path) -> List[Path]:
    """Collect hash-chain JSON files sorted by filename.

    Bilingual: Recolecta archivos JSON de cadena hash ordenados por nombre.

    Args:
        hash_dir: Hash directory path.

    Returns:
        List[Path]: Ordered list of JSON files.

    Raises:
        None.
    """
    if not hash_dir.exists():
        return []
    return sorted(hash_dir.glob("*.json"), key=lambda item: item.name)


def _build_backup_manifest(files_backed_up: List[str], hashes: Dict[str, str], encrypted: bool) -> Dict[str, Any]:
    """Build backup manifest metadata.

    Bilingual: Construye metadatos del manifiesto de respaldo.

    Args:
        files_backed_up: Relative filenames included in backup payload.
        hashes: SHA-256 mapping by filename.
        encrypted: Whether payload was encrypted.

    Returns:
        Dict[str, Any]: JSON-serializable manifest.

    Raises:
        None.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "encrypted": encrypted,
        "files": files_backed_up,
        "sha256_hashes": hashes,
        "version": "1.0",
    }


def _backup_to_local(backup_dir: Path, payload: bytes, filename: str, manifest: Dict[str, Any]) -> bool:
    """Persist backup payload and manifest to local filesystem.

    Bilingual: Persiste payload y manifiesto de respaldo en filesystem local.

    Args:
        backup_dir: Destination backup folder.
        payload: Backup payload bytes.
        filename: Backup payload filename.
        manifest: Backup manifest dictionary.

    Returns:
        bool: True when both files are written correctly.

    Raises:
        None.
    """
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / filename
        manifest_path = backup_dir / f"{filename}.manifest.json"

        fd, temp_path = tempfile.mkstemp(dir=str(backup_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
            Path(temp_path).replace(backup_path)
        finally:
            if Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)

        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("backup_local_failed | %s", exc)
        return False


def _backup_to_dropbox(payload: bytes, remote_path: str) -> bool:
    """Upload payload to Dropbox when SDK and credentials are available.

    Bilingual: Sube payload a Dropbox cuando SDK y credenciales están disponibles.

    Args:
        payload: Backup payload bytes.
        remote_path: Remote object path.

    Returns:
        bool: True on successful upload.

    Raises:
        None.
    """
    if not _HAS_DROPBOX:
        return False
    token = os.getenv(ENV_DROPBOX_TOKEN)
    if not token:
        return False
    try:
        folder = os.getenv(ENV_DROPBOX_FOLDER, "/centinel-backups")
        client = dropbox.Dropbox(token)
        client.files_upload(payload, f"{folder}/{remote_path}", mode=dropbox.files.WriteMode.overwrite)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("backup_dropbox_failed | %s", exc)
        return False


def _backup_to_s3(payload: bytes, remote_path: str) -> bool:
    """Upload payload to S3 when SDK and bucket credentials are available.

    Bilingual: Sube payload a S3 cuando SDK y credenciales están disponibles.

    Args:
        payload: Backup payload bytes.
        remote_path: Remote object key suffix.

    Returns:
        bool: True on successful upload.

    Raises:
        None.
    """
    if not _HAS_BOTO3:
        return False
    bucket = os.getenv(ENV_S3_BUCKET)
    if not bucket:
        return False
    try:
        prefix = os.getenv(ENV_S3_PREFIX, "centinel-backups")
        key = f"{prefix}/{remote_path}"
        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=payload)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("backup_s3_failed | %s", exc)
        return False


def backup_critical_assets(
    health_state_path: Path = DEFAULT_HEALTH_STATE_PATH,
    hash_chain_dir: Path = DEFAULT_HASH_CHAIN_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
) -> Dict[str, Any]:
    """Create encrypted backup of health state and hash-chain files.

    Bilingual: Crea respaldo cifrado del estado de salud y archivos de cadena hash.

    Args:
        health_state_path: Path to health_state JSON file.
        hash_chain_dir: Directory containing hash-chain JSON files.
        backup_dir: Destination backup directory.

    Returns:
        Dict[str, Any]: Backup execution report.

    Raises:
        None.
    """
    report: Dict[str, Any] = {
        "local": False,
        "dropbox": False,
        "s3": False,
        "files_backed_up": [],
        "errors": [],
    }
    try:
        files: List[Path] = []
        if health_state_path.exists():
            files.append(health_state_path)
        files.extend(_collect_hash_chain_files(hash_chain_dir))
        report["files_backed_up"] = [file.name for file in files]

        if not files:
            return report

        blob: Dict[str, Any] = {}
        hashes: Dict[str, str] = {}
        for file in files:
            content = file.read_bytes()
            blob[file.name] = content.decode("utf-8", errors="replace")
            hashes[file.name] = _compute_sha256(content)

        payload = json.dumps(blob, ensure_ascii=False, indent=2).encode("utf-8")
        fernet = _get_fernet()
        encrypted_payload = _encrypt_data(payload, fernet=fernet)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"centinel_backup_{timestamp}.enc"
        manifest = _build_backup_manifest(report["files_backed_up"], hashes, encrypted=fernet is not None)

        report["local"] = _backup_to_local(backup_dir, encrypted_payload, filename, manifest)
        report["dropbox"] = _backup_to_dropbox(encrypted_payload, filename)
        report["s3"] = _backup_to_s3(encrypted_payload, filename)
        return report
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(str(exc))
        logger.error("backup_critical_assets_failed | %s", exc)
        return report


def backup_critical(
    health_state_path: Path = DEFAULT_HEALTH_STATE_PATH,
    hash_chain_dir: Path = DEFAULT_HASH_CHAIN_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
) -> Dict[str, Any]:
    """Compatibility wrapper over `backup_critical_assets`.

    Bilingual: Wrapper de compatibilidad sobre `backup_critical_assets`.

    Args:
        health_state_path: Path to health_state JSON file.
        hash_chain_dir: Directory containing hash-chain files.
        backup_dir: Destination backup folder.

    Returns:
        Dict[str, Any]: Backup execution report.

    Raises:
        None.
    """
    return backup_critical_assets(health_state_path, hash_chain_dir, backup_dir)


class BackupScheduler:
    """Periodic backup scheduler with explicit trigger and stop controls.

    Bilingual: Programador periódico de respaldos con trigger explícito y stop.

    Args:
        interval_seconds: Seconds between periodic backup cycles.
        health_state_path: Path to health_state JSON file.
        hash_chain_dir: Directory containing hash-chain files.
        backup_dir: Destination backup folder.

    Returns:
        None: Class constructor.

    Raises:
        ValueError: If interval_seconds is non-positive.
    """

    def __init__(
        self,
        interval_seconds: int = DEFAULT_BACKUP_INTERVAL_SECONDS,
        health_state_path: Path = DEFAULT_HEALTH_STATE_PATH,
        hash_chain_dir: Path = DEFAULT_HASH_CHAIN_DIR,
        backup_dir: Path = DEFAULT_BACKUP_DIR,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        self.interval_seconds = interval_seconds
        self.health_state_path = health_state_path
        self.hash_chain_dir = hash_chain_dir
        self.backup_dir = backup_dir
        self.last_backup_time = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def trigger_backup(self) -> Dict[str, Any]:
        """Run a backup immediately and update scheduler timestamp.

        Bilingual: Ejecuta respaldo inmediato y actualiza timestamp del scheduler.

        Args:
            None.

        Returns:
            Dict[str, Any]: Backup execution report.

        Raises:
            None.
        """
        result = backup_critical_assets(
            health_state_path=self.health_state_path,
            hash_chain_dir=self.hash_chain_dir,
            backup_dir=self.backup_dir,
        )
        self.last_backup_time = time.monotonic()
        return result

    def _run(self) -> None:
        """Internal scheduler loop.

        Bilingual: Loop interno del programador.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        while not self._stop_event.is_set():
            self.trigger_backup()
            self._stop_event.wait(self.interval_seconds)

    def start(self) -> None:
        """Start background periodic backup worker.

        Bilingual: Inicia worker en background para respaldo periódico.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background backup worker if running.

        Bilingual: Detiene worker de respaldo en background si está activo.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
