"""SHA-256 chained log hashing with optional encrypted persistence.
(Hashing encadenado SHA-256 de logs con persistencia encriptada opcional.)

Provides tamper-evident logging: each log entry includes the SHA-256 hash
of the previous entry, forming a hash chain.  Any modification to a past
entry breaks the chain and is detectable.

(Provee logging a prueba de manipulaciones: cada entrada incluye el hash
SHA-256 de la entrada anterior, formando una cadena de hashes.  Cualquier
modificación a una entrada pasada rompe la cadena y es detectable.)

Opt-in via config.yaml:
    security:
      log_hashing: true           # Enable hash chain (Habilitar cadena de hashes)
      log_encryption: true        # Enable AES encryption (Habilitar encriptación AES)
      log_encryption_key_env: "CENTINEL_LOG_KEY"  # Env var with Fernet key
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("centinel.logs")

# ---------------------------------------------------------------------------
# Config loading (Carga de configuración)
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parents[3] / "command_center" / "config.yaml"


def _load_log_security_config() -> dict[str, Any]:
    """Load security config section relevant to log integrity.
    (Carga la sección de configuración de seguridad relevante para integridad de logs.)
    """
    if not _CONFIG_PATH.exists():
        return {}
    try:
        raw = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    sec = raw.get("security", {})
    return sec if isinstance(sec, dict) else {}


# ---------------------------------------------------------------------------
# Hash chain (Cadena de hashes)
# ---------------------------------------------------------------------------

# Sentinel value for the very first entry in the chain
# (Valor centinela para la primera entrada en la cadena)
_GENESIS_HASH = "0" * 64


class HashChainLogger:
    """Append-only logger that chains SHA-256 hashes across entries.
    (Logger append-only que encadena hashes SHA-256 entre entradas.)

    Each entry is:
        { "seq": N, "ts": "<ISO>", "event": "...", "data": {...},
          "prev_hash": "<hex>", "hash": "<hex>" }

    The "hash" field is SHA-256(prev_hash + canonical_json(entry_without_hash)).
    Verification: iterate entries, recompute each hash, compare.

    (Cada entrada contiene seq, ts, event, data, prev_hash y hash.
    El campo "hash" es SHA-256(prev_hash + json_canónico(entrada_sin_hash)).
    Verificación: iterar entradas, recalcular cada hash, comparar.)
    """

    def __init__(
        self,
        log_path: str | Path = "logs/integrity.jsonl",
        enabled: bool = False,
    ) -> None:
        self._path = Path(log_path)
        self._enabled = enabled
        self._seq: int = 0
        self._prev_hash: str = _GENESIS_HASH

        if self._enabled:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # Resume chain from last entry if the file exists
            # (Retomar cadena desde la última entrada si el archivo existe)
            self._resume_chain()

    # ------------------------------------------------------------------
    # Public API (API pública)
    # ------------------------------------------------------------------

    def append(self, event: str, data: dict[str, Any] | None = None) -> str | None:
        """Append a hash-chained entry to the integrity log.
        (Agrega una entrada encadenada al log de integridad.)

        Returns the entry hash, or None when hashing is disabled.
        (Retorna el hash de la entrada, o None si el hashing está deshabilitado.)
        """
        if not self._enabled:
            return None

        self._seq += 1
        entry: dict[str, Any] = {
            "seq": self._seq,
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": data or {},
            "prev_hash": self._prev_hash,
        }
        entry_hash = self._compute_hash(entry)
        entry["hash"] = entry_hash
        self._prev_hash = entry_hash

        # Append as a single JSONL line (Escribir como línea JSONL)
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

        return entry_hash

    def verify(self) -> tuple[bool, int, str]:
        """Verify the full hash chain from genesis to the latest entry.
        (Verifica la cadena completa de hashes desde el genesis hasta la última entrada.)

        Returns (valid, entries_checked, message).
        (Retorna (válido, entradas_verificadas, mensaje).)
        """
        if not self._path.exists():
            return True, 0, "no_log_file"

        prev = _GENESIS_HASH
        count = 0
        for lineno, raw_line in enumerate(self._path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw_line.strip():
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                return False, count, f"json_parse_error line={lineno}"

            stored_hash = entry.pop("hash", "")
            expected_prev = entry.get("prev_hash", "")

            # Verify prev_hash links correctly (Verificar que prev_hash enlaza correctamente)
            if expected_prev != prev:
                return False, count, f"chain_break line={lineno} expected_prev={prev[:16]}..."

            # Recompute and compare (Recalcular y comparar)
            computed = self._compute_hash(entry)
            if computed != stored_hash:
                return False, count, f"hash_mismatch line={lineno}"

            prev = stored_hash
            count += 1

        return True, count, "chain_valid"

    # ------------------------------------------------------------------
    # Internals (Internos)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_hash(entry: dict[str, Any]) -> str:
        """Compute SHA-256(prev_hash + canonical_json(entry)).
        (Calcula SHA-256(prev_hash + json_canónico(entrada)).)
        """
        prev = entry.get("prev_hash", _GENESIS_HASH)
        # Canonical JSON: sorted keys, no spaces, UTF-8
        # (JSON canónico: claves ordenadas, sin espacios, UTF-8)
        canonical = json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        payload = (prev + canonical).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _resume_chain(self) -> None:
        """Resume seq and prev_hash from the last line of the existing log.
        (Retoma seq y prev_hash de la última línea del log existente.)
        """
        if not self._path.exists():
            return
        try:
            lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        except OSError:
            return
        if not lines:
            return
        try:
            last = json.loads(lines[-1])
            self._seq = int(last.get("seq", 0))
            self._prev_hash = last.get("hash", _GENESIS_HASH)
        except (json.JSONDecodeError, ValueError):
            logger.warning("hashchain_resume_failed — starting fresh chain (iniciando cadena nueva)")


# ---------------------------------------------------------------------------
# Encrypted persistence (Persistencia encriptada)
# ---------------------------------------------------------------------------

def _get_fernet_key(env_var: str = "CENTINEL_LOG_KEY") -> bytes | None:
    """Load a Fernet key from the environment.
    (Carga una clave Fernet del entorno.)

    ─────────────────────────────────────────────────────────
    HOW TO GENERATE A KEY (CÓMO GENERAR UNA CLAVE):
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    Then set the env var:
        export CENTINEL_LOG_KEY="<the-key>"
    ─────────────────────────────────────────────────────────
    """
    raw = os.getenv(env_var, "").strip()
    return raw.encode("utf-8") if raw else None


def encrypt_log_file(
    source: str | Path,
    dest: str | Path | None = None,
    env_var: str = "CENTINEL_LOG_KEY",
) -> Path | None:
    """Encrypt a plaintext log file using Fernet (AES-128-CBC + HMAC).
    (Encripta un archivo de log en texto plano usando Fernet — AES-128-CBC + HMAC.)

    If dest is None, writes to <source>.enc.
    Returns the output path, or None if encryption is not configured.
    (Si dest es None, escribe en <source>.enc.
    Retorna la ruta de salida, o None si la encriptación no está configurada.)
    """
    key = _get_fernet_key(env_var)
    if not key:
        logger.info("log_encryption_skipped reason=no_key env_var=%s", env_var)
        return None

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        logger.warning("log_encryption_skipped reason=cryptography_not_installed")
        return None

    src = Path(source)
    if not src.exists():
        return None

    out = Path(dest) if dest else src.with_suffix(src.suffix + ".enc")
    fernet = Fernet(key)
    plaintext = src.read_bytes()
    ciphertext = fernet.encrypt(plaintext)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(ciphertext)
    logger.info("log_encrypted src=%s dest=%s bytes=%d", src, out, len(ciphertext))
    return out


def decrypt_log_file(
    source: str | Path,
    dest: str | Path | None = None,
    env_var: str = "CENTINEL_LOG_KEY",
) -> Path | None:
    """Decrypt a Fernet-encrypted log file back to plaintext.
    (Desencripta un archivo de log encriptado con Fernet a texto plano.)

    If dest is None, writes to <source> minus the .enc suffix.
    Returns the output path, or None if decryption fails.
    (Si dest es None, escribe en <source> sin el sufijo .enc.
    Retorna la ruta de salida, o None si la desencriptación falla.)
    """
    key = _get_fernet_key(env_var)
    if not key:
        logger.warning("log_decryption_failed reason=no_key")
        return None

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        logger.warning("log_decryption_failed reason=cryptography_not_installed")
        return None

    src = Path(source)
    if not src.exists():
        return None

    out = Path(dest) if dest else src.with_suffix("")  # remove .enc
    fernet = Fernet(key)
    try:
        plaintext = fernet.decrypt(src.read_bytes())
    except Exception as exc:
        logger.error("log_decryption_failed error=%s", exc)
        return None

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(plaintext)
    logger.info("log_decrypted src=%s dest=%s", src, out)
    return out


# ---------------------------------------------------------------------------
# Factory — convenience constructor from config.yaml
# (Fábrica — constructor conveniente desde config.yaml)
# ---------------------------------------------------------------------------

def create_integrity_logger(
    log_path: str | Path = "logs/integrity.jsonl",
) -> HashChainLogger:
    """Create a HashChainLogger using settings from config.yaml.
    (Crea un HashChainLogger usando settings de config.yaml.)

    Reads security.log_hashing from config.yaml.
    When false or missing, the logger is a no-op (returns None on append).
    (Lee security.log_hashing de config.yaml.
    Cuando es false o falta, el logger es no-op — retorna None en append.)
    """
    cfg = _load_log_security_config()
    enabled = bool(cfg.get("log_hashing", False))
    return HashChainLogger(log_path=log_path, enabled=enabled)
