"""Encrypted backup of critical Centinel assets to multiple secure locations.

Backs up ``data/health_state.json`` and the hash-chain files after every
successful scrape or on a 30-minute timer. Files are encrypted with AES-256
via Fernet (``cryptography`` library) before writing to:
  1. Local ``./backups/`` directory (always).
  2. Dropbox (if ``dropbox`` SDK is available and configured).
  3. AWS S3 private bucket (if ``boto3`` is available and configured).

All backup operations are fail-safe: errors are logged but never propagate
to the main scraper pipeline.

Bilingual: Respaldo cifrado de activos criticos de Centinel a multiples
ubicaciones seguras. Respalda ``data/health_state.json`` y los archivos de
cadena de hashes despues de cada scrape exitoso o en un temporizador de
30 minutos. Los archivos se cifran con AES-256 via Fernet (libreria
``cryptography``) antes de escribir a:
  1. Directorio local ``./backups/`` (siempre).
  2. Dropbox (si el SDK ``dropbox`` esta disponible y configurado).
  3. Bucket S3 privado de AWS (si ``boto3`` esta disponible y configurado).

Todas las operaciones de respaldo son fail-safe: los errores se registran
pero nunca se propagan al pipeline principal del scraper.
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

# ---------------------------------------------------------------------------
# Cryptography imports / Imports de criptografia
# ---------------------------------------------------------------------------
try:
    from cryptography.fernet import Fernet

    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False
    logger.warning(
        "cryptography not available, backups will be unencrypted | "
        "cryptography no disponible, respaldos seran sin cifrar"
    )

# ---------------------------------------------------------------------------
# Optional cloud SDK imports / Imports opcionales de SDKs cloud
# ---------------------------------------------------------------------------
try:
    import dropbox  # type: ignore[import-untyped]

    _HAS_DROPBOX = True
except ImportError:
    _HAS_DROPBOX = False

try:
    import boto3  # type: ignore[import-untyped]

    _HAS_BOTO3 = True
except ImportError:
    _HAS_BOTO3 = False

# ---------------------------------------------------------------------------
# Default paths / Rutas por defecto
# ---------------------------------------------------------------------------
DEFAULT_HEALTH_STATE_PATH = Path("data/health_state.json")
DEFAULT_HASH_CHAIN_DIR = Path("data/hashes")
DEFAULT_BACKUP_DIR = Path("backups")
DEFAULT_BACKUP_INTERVAL_SECONDS = 1800  # 30 minutes / 30 minutos

# Environment variable names / Nombres de variables de entorno
ENV_BACKUP_KEY = "CENTINEL_BACKUP_KEY"
ENV_DROPBOX_TOKEN = "CENTINEL_DROPBOX_TOKEN"
ENV_DROPBOX_FOLDER = "CENTINEL_DROPBOX_FOLDER"
ENV_S3_BUCKET = "CENTINEL_S3_BUCKET"
ENV_S3_PREFIX = "CENTINEL_S3_PREFIX"


def _generate_backup_key() -> bytes:
    """Generate a new Fernet key and log a warning to persist it.

    Bilingual: Genera una nueva clave Fernet y registra advertencia para persistirla.
    """
    key = Fernet.generate_key()
    logger.warning(
        "Generated ephemeral backup key (set %s to persist) | "
        "Clave de respaldo efimera generada (configure %s para persistir)",
        ENV_BACKUP_KEY,
        ENV_BACKUP_KEY,
    )
    return key


def _get_fernet() -> Optional[Any]:
    """Return a Fernet instance using the configured or ephemeral key.

    Bilingual: Retorna una instancia Fernet usando la clave configurada o efimera.
    """
    if not _HAS_CRYPTOGRAPHY:
        return None

    key_str = os.getenv(ENV_BACKUP_KEY)
    if key_str:
        try:
            return Fernet(key_str.encode("utf-8"))
        except Exception:
            logger.error(
                "Invalid backup key in %s, generating ephemeral | "
                "Clave de respaldo invalida en %s, generando efimera",
                ENV_BACKUP_KEY,
                ENV_BACKUP_KEY,
            )
    return Fernet(_generate_backup_key())


def _encrypt_data(data: bytes, fernet: Optional[Any] = None) -> bytes:
    """Encrypt raw bytes with Fernet AES-256. Falls back to plaintext if unavailable.

    Bilingual: Cifra bytes crudos con Fernet AES-256. Retorna texto plano si no disponible.
    """
    if fernet is not None:
        return fernet.encrypt(data)
    return data


def _compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes.

    Bilingual: Calcula digest SHA-256 hexadecimal de bytes crudos.
    """
    return hashlib.sha256(data).hexdigest()


def _collect_hash_chain_files(hash_dir: Path) -> List[Path]:
    """Collect all hash JSON files from the hash directory.

    Bilingual: Recolecta todos los archivos JSON de hash del directorio de hashes.
    """
    if not hash_dir.exists():
        return []
    files = sorted(hash_dir.glob("*.json"), key=lambda p: p.name)
    return files


def _build_backup_manifest(
    files_backed_up: List[str],
    hashes: Dict[str, str],
    encrypted: bool,
) -> Dict[str, Any]:
    """Build a JSON manifest documenting what was backed up and its integrity hashes.

    Bilingual: Construye un manifiesto JSON documentando que fue respaldado y
    sus hashes de integridad.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "encrypted": encrypted,
        "files": files_backed_up,
        "sha256_hashes": hashes,
        "version": "1.0",
    }


# ---------------------------------------------------------------------------
# Backup destinations / Destinos de respaldo
# ---------------------------------------------------------------------------


def _backup_to_local(
    backup_dir: Path,
    payload: bytes,
    filename: str,
    manifest: Dict[str, Any],
) -> bool:
    """Write encrypted backup and manifest to local directory.

    Bilingual: Escribe respaldo cifrado y manifiesto al directorio local.
    """
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / filename
        manifest_path = backup_dir / f"{filename}.manifest.json"

        # Atomic write / Escritura atomica
        fd, tmp_path = tempfile.mkstemp(dir=str(backup_dir), suffix=".tmp")
        try:
            with open(fd, "wb") as f:
                f.write(payload)
            Path(tmp_path).replace(backup_path)
        except BaseException:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
            raise

        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(
            "Local backup written | Respaldo local escrito: %s (%d bytes)",
            backup_path,
            len(payload),
        )
        return True
    except Exception as exc:
        logger.error("Local backup failed | Respaldo local fallo: %s", exc)
        return False


def _backup_to_dropbox(
    payload: bytes,
    remote_path: str,
) -> bool:
    """Upload encrypted backup to Dropbox.

    Bilingual: Sube respaldo cifrado a Dropbox.
    """
    if not _HAS_DROPBOX:
        logger.debug("Dropbox SDK not available, skipping | SDK Dropbox no disponible, omitiendo")
        return False

    token = os.getenv(ENV_DROPBOX_TOKEN)
    if not token:
        logger.debug("Dropbox token not configured, skipping | Token Dropbox no configurado, omitiendo")
        return False

    try:
        dbx = dropbox.Dropbox(token)
        folder = os.getenv(ENV_DROPBOX_FOLDER, "/centinel-backups")
        full_path = f"{folder}/{remote_path}"
        dbx.files_upload(
            payload,
            full_path,
            mode=dropbox.files.WriteMode.overwrite,
        )
        logger.info(
            "Dropbox backup uploaded | Respaldo Dropbox subido: %s (%d bytes)",
            full_path,
            len(payload),
        )
        return True
    except Exception as exc:
        logger.error("Dropbox backup failed | Respaldo Dropbox fallo: %s", exc)
        return False


def _backup_to_s3(
    payload: bytes,
    key: str,
) -> bool:
    """Upload encrypted backup to AWS S3 private bucket.

    Bilingual: Sube respaldo cifrado a bucket S3 privado de AWS.
    """
    if not _HAS_BOTO3:
        logger.debug("boto3 not available, skipping S3 | boto3 no disponible, omitiendo S3")
        return False

    bucket = os.getenv(ENV_S3_BUCKET)
    if not bucket:
        logger.debug("S3 bucket not configured, skipping | Bucket S3 no configurado, omitiendo")
        return False

    try:
        prefix = os.getenv(ENV_S3_PREFIX, "centinel-backups")
        full_key = f"{prefix}/{key}"
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=full_key,
            Body=payload,
            ServerSideEncryption="AES256",
        )
        logger.info(
            "S3 backup uploaded | Respaldo S3 subido: s3://%s/%s (%d bytes)",
            bucket,
            full_key,
            len(payload),
        )
        return True
    except Exception as exc:
        logger.error("S3 backup failed | Respaldo S3 fallo: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main backup function / Funcion principal de respaldo
# ---------------------------------------------------------------------------


def backup_critical_assets(
    *,
    health_state_path: Path = DEFAULT_HEALTH_STATE_PATH,
    hash_chain_dir: Path = DEFAULT_HASH_CHAIN_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR / "encrypted",
) -> Dict[str, Any]:
    """Back up critical Centinel assets (health state + hash chain) to all configured destinations.

    This function is designed to be called after every successful scrape and
    after ``save_health_state()``. It NEVER raises exceptions -- all errors
    are caught, logged, and reported in the return dictionary.

    Bilingual: Respalda activos criticos de Centinel (estado de salud + cadena de hashes)
    a todos los destinos configurados. Esta funcion esta disenada para llamarse despues
    de cada scrape exitoso y despues de ``save_health_state()``. NUNCA lanza excepciones --
    todos los errores se capturan, registran y reportan en el diccionario de retorno.

    Args:
        health_state_path: Path to health_state.json.
        hash_chain_dir: Directory containing hash chain JSON files.
        backup_dir: Local backup destination directory.

    Returns:
        Dictionary with backup results including success/failure per destination.
    """
    results: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "local": False,
        "dropbox": False,
        "s3": False,
        "files_backed_up": [],
        "errors": [],
    }

    try:
        # Collect files to back up / Recolectar archivos a respaldar
        files_to_backup: Dict[str, bytes] = {}
        file_hashes: Dict[str, str] = {}

        # Health state / Estado de salud
        if health_state_path.exists():
            data = health_state_path.read_bytes()
            files_to_backup["health_state.json"] = data
            file_hashes["health_state.json"] = _compute_sha256(data)
        else:
            logger.debug(
                "Health state not found, skipping | Estado de salud no encontrado, omitiendo: %s",
                health_state_path,
            )

        # Hash chain files / Archivos de cadena de hashes
        chain_files = _collect_hash_chain_files(hash_chain_dir)
        for chain_file in chain_files:
            try:
                data = chain_file.read_bytes()
                relative_name = f"hashes/{chain_file.name}"
                files_to_backup[relative_name] = data
                file_hashes[relative_name] = _compute_sha256(data)
            except OSError as exc:
                logger.warning(
                    "Could not read hash file | No se pudo leer archivo hash: %s - %s",
                    chain_file,
                    exc,
                )

        if not files_to_backup:
            logger.info("No critical assets to back up | No hay activos criticos para respaldar")
            return results

        # Build combined backup payload / Construir payload combinado de respaldo
        combined_payload: Dict[str, str] = {}
        for name, raw_data in files_to_backup.items():
            # Store as base64-safe string in JSON structure /
            # Almacenar como cadena base64-safe en estructura JSON
            import base64

            combined_payload[name] = base64.b64encode(raw_data).decode("ascii")

        raw_bundle = json.dumps(combined_payload, indent=2, ensure_ascii=False).encode("utf-8")

        # Encrypt the bundle / Cifrar el paquete
        fernet = _get_fernet()
        encrypted = fernet is not None
        encrypted_bundle = _encrypt_data(raw_bundle, fernet)

        # Build manifest / Construir manifiesto
        bundle_hash = _compute_sha256(encrypted_bundle)
        file_hashes["_bundle"] = bundle_hash
        manifest = _build_backup_manifest(
            list(files_to_backup.keys()),
            file_hashes,
            encrypted=encrypted,
        )

        # Generate timestamped filename / Generar nombre de archivo con timestamp
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ext = ".enc" if encrypted else ".json"
        filename = f"centinel_backup_{ts}{ext}"

        results["files_backed_up"] = list(files_to_backup.keys())

        # Write to all destinations / Escribir a todos los destinos
        results["local"] = _backup_to_local(backup_dir, encrypted_bundle, filename, manifest)
        results["dropbox"] = _backup_to_dropbox(encrypted_bundle, filename)
        results["s3"] = _backup_to_s3(encrypted_bundle, filename)

        destinations_ok = sum([results["local"], results["dropbox"], results["s3"]])
        logger.info(
            "Backup complete | Respaldo completo: %d/%d destinations, %d files, encrypted=%s",
            destinations_ok,
            3,
            len(files_to_backup),
            encrypted,
        )

    except Exception as exc:
        # Never propagate to main pipeline / Nunca propagar al pipeline principal
        error_msg = f"Backup failed unexpectedly | Respaldo fallo inesperadamente: {exc}"
        logger.error(error_msg)
        results["errors"].append(str(exc))

    return results


# ---------------------------------------------------------------------------
# Timed backup scheduler / Programador de respaldo temporizado
# ---------------------------------------------------------------------------


def backup_critical(
    *,
    health_state_path: Path = DEFAULT_HEALTH_STATE_PATH,
    hash_chain_dir: Path = DEFAULT_HASH_CHAIN_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR / "encrypted",
) -> Dict[str, Any]:
    """Run encrypted critical backup in fail-safe mode for scheduler/post-scrape hooks.

    Bilingual: Ejecuta respaldo cifrado crítico en modo fail-safe para hooks de scheduler o post-scrape.

    Args:
        health_state_path: Path to serialized health state JSON file.
        hash_chain_dir: Directory with hash-chain artifacts (prefers data/hashes).
        backup_dir: Output directory for encrypted local bundles.

    Returns:
        Dictionary with per-destination backup status and metadata.

    Raises:
        Never: Errors are captured and returned in the result payload.
    """
    effective_hash_dir = hash_chain_dir if hash_chain_dir.exists() else Path("hashes")
    # Never break scraper flow / Nunca romper el flujo del scraper
    try:
        return backup_critical_assets(
            health_state_path=health_state_path,
            hash_chain_dir=effective_hash_dir,
            backup_dir=backup_dir,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("backup_critical_unexpected_error | error inesperado en backup_critical: %s", exc)
        return {"local": False, "dropbox": False, "s3": False, "errors": [str(exc)], "files_backed_up": []}


class BackupScheduler:
    """Runs backup_critical_assets() on a configurable interval in a background thread.

    Bilingual: Ejecuta backup_critical_assets() en un intervalo configurable
    en un hilo de fondo.
    """

    def __init__(
        self,
        *,
        interval_seconds: int = DEFAULT_BACKUP_INTERVAL_SECONDS,
        health_state_path: Path = DEFAULT_HEALTH_STATE_PATH,
        hash_chain_dir: Path = DEFAULT_HASH_CHAIN_DIR,
        backup_dir: Path = DEFAULT_BACKUP_DIR / "encrypted",
    ) -> None:
        self._interval: int = max(interval_seconds, 60)
        self._health_state_path: Path = health_state_path
        self._hash_chain_dir: Path = hash_chain_dir
        self._backup_dir: Path = backup_dir
        self._stop_event: threading.Event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_backup_time: float = 0.0

    def start(self) -> None:
        """Start the background backup timer.

        Bilingual: Inicia el temporizador de respaldo en segundo plano.
        """
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="centinel-backup-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Backup scheduler started | Programador de respaldo iniciado: interval=%ds",
            self._interval,
        )

    def stop(self) -> None:
        """Stop the background backup timer.

        Bilingual: Detiene el temporizador de respaldo en segundo plano.
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        logger.info("Backup scheduler stopped | Programador de respaldo detenido")

    def _run_loop(self) -> None:
        """Background loop that runs backups at regular intervals.

        Bilingual: Bucle de fondo que ejecuta respaldos a intervalos regulares.
        """
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self._interval)
            if self._stop_event.is_set():
                break
            self.trigger_backup()

    def trigger_backup(self) -> Dict[str, Any]:
        """Manually trigger a backup (also called by the background loop).

        Bilingual: Activa un respaldo manualmente (tambien llamado por el bucle de fondo).
        """
        result = backup_critical_assets(
            health_state_path=self._health_state_path,
            hash_chain_dir=self._hash_chain_dir,
            backup_dir=self._backup_dir,
        )
        self._last_backup_time = time.monotonic()
        return result

    @property
    def last_backup_time(self) -> float:
        """Monotonic timestamp of the last backup attempt.

        Bilingual: Timestamp monotonico del ultimo intento de respaldo.
        """
        return self._last_backup_time
