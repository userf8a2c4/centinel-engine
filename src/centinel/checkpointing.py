"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/checkpointing.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - CheckpointConfig
  - CheckpointError
  - CheckpointStorageError
  - CheckpointValidationError
  - CheckpointManager
  - generate_checkpoint_key
  - bloque_main

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/checkpointing.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - CheckpointConfig
  - CheckpointError
  - CheckpointStorageError
  - CheckpointValidationError
  - CheckpointManager
  - generate_checkpoint_key
  - bloque_main

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Checkpointing Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations


from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if find_spec("cryptography"):
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
else:
    Fernet = None

    class InvalidToken(Exception):
        """Fallback error when cryptography is unavailable."""

    hashes = None
    HKDF = None

from monitoring.alerts import dispatch_alert

CheckpointState = Dict[str, Any]


@dataclass(frozen=True)
class CheckpointConfig:
    """Configuración necesaria para operar el checkpointing."""

    pipeline_version: str
    run_id: str
    checkpoint_dir: str = "checkpoints/"
    encryption_key_env: str = "CHECKPOINT_KEY"
    checkpoint_interval: int = 50


class CheckpointError(Exception):
    """Base error for checkpoint operations."""


class CheckpointStorageError(CheckpointError):
    """Raised when storage operations fail after retries."""


class CheckpointValidationError(CheckpointError):
    """Raised when checkpoint content is invalid or corrupt."""


class CheckpointManager:
    """Administra checkpoints cifrados en el sistema de archivos local.

    This manager stores encrypted checkpoints with a per-checkpoint IV, handles
    retries with exponential backoff, validates state shape, and provides
    asynchronous APIs compatible with async pipeline workflows.
    """

    required_state_keys = {
        "accumulated_hash_chain",
        "rule_states",
        "last_timestamp",
        "pipeline_version",
        "run_id",
    }

    def __init__(
        self,
        config: CheckpointConfig | None = None,
        *,
        checkpoint_dir: str = "checkpoints/",
        version: str | None = None,
        run_id: str | None = None,
        encryption_key_env: str = "CHECKPOINT_KEY",
        logger: logging.Logger | None = None,
    ) -> None:
        """Español: Función __init__ del módulo src/centinel/checkpointing.py.

        English: Function __init__ defined in src/centinel/checkpointing.py.
        """
        if isinstance(config, CheckpointConfig):
            resolved = config
        else:
            if not version or not run_id:
                raise CheckpointValidationError("checkpoint_config_missing_fields")
            resolved = CheckpointConfig(
                pipeline_version=version,
                run_id=run_id,
                checkpoint_dir=checkpoint_dir,
                encryption_key_env=encryption_key_env,
            )

        self.config = resolved
        self.checkpoint_dir = Path(resolved.checkpoint_dir)
        self.version = resolved.pipeline_version
        self.run_id = resolved.run_id
        self.encryption_key_env = resolved.encryption_key_env
        self.checkpoint_interval = resolved.checkpoint_interval
        self.logger = logger or logging.getLogger(__name__)
        self._base_key = self._load_base_key()

    async def save_checkpoint(self, state_dict: CheckpointState) -> str:
        """Guarda un checkpoint cifrado y devuelve su hash.

        Args:
            state_dict: Estado mínimo del pipeline. Debe incluir las llaves
                requeridas en ``required_state_keys``.

        Returns:
            Hash SHA256 del checkpoint almacenado (sobre el blob cifrado).
        """
        timestamp = self._utc_now()
        state = dict(state_dict)
        state.setdefault("last_timestamp", timestamp)
        state.setdefault("pipeline_version", self.version)
        state.setdefault("run_id", self.run_id)
        self._ensure_required_state(state)

        payload = {
            "state": state,
            "metadata": {
                "pipeline_version": self.version,
                "run_id": self.run_id,
                "last_timestamp": state["last_timestamp"],
            },
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")

        iv = os.urandom(16)
        fernet = self._derive_fernet(iv)
        encrypted_payload = fernet.encrypt(serialized)
        encrypted_hash = self._sha256_hex(encrypted_payload)

        envelope = {
            "schema_version": 2,
            "pipeline_version": self.version,
            "run_id": self.run_id,
            "timestamp": timestamp,
            "iv": base64.urlsafe_b64encode(iv).decode("utf-8"),
            "ciphertext": encrypted_payload.decode("utf-8"),
            "ciphertext_hash": encrypted_hash,
        }
        blob = json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")

        checkpoint_dir = self.checkpoint_dir
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        safe_timestamp = timestamp.replace(":", "-")
        latest_path = checkpoint_dir / "latest.json"
        history_path = checkpoint_dir / f"{safe_timestamp}.json"

        latest_path.write_bytes(blob)
        history_path.write_bytes(blob)
        self.logger.info(
            "checkpoint_saved",
            extra={
                "checkpoint_path": str(latest_path),
                "checkpoint_hash": encrypted_hash,
                "timestamp": timestamp,
            },
        )
        return encrypted_hash

    async def load_latest_checkpoint(self) -> Optional[CheckpointState]:
        """Carga el último checkpoint válido desde el directorio local.

        Returns:
            Estado del pipeline si existe un checkpoint válido; ``None`` si no hay.
        """
        latest_path = self.checkpoint_dir / "latest.json"
        if not latest_path.exists():
            self.logger.warning(
                "checkpoint_not_found",
                extra={"checkpoint_path": str(latest_path)},
            )
            return None

        try:
            raw_blob = latest_path.read_bytes()
        except OSError as exc:
            self.logger.warning(
                "checkpoint_read_failed",
                extra={"checkpoint_path": str(latest_path), "error": str(exc)},
            )
            return None

        try:
            payload = await self._decrypt_envelope(raw_blob)
        except CheckpointValidationError as exc:
            self.logger.warning(
                "checkpoint_decrypt_failed",
                extra={"checkpoint_path": str(latest_path), "error": str(exc)},
            )
            return None
        is_valid, reason = await self.validate_checkpoint(payload)
        if not is_valid:
            self.logger.warning(
                "checkpoint_invalid",
                extra={"checkpoint_path": str(latest_path), "reason": reason},
            )
            return None
        return payload["state"]

    async def validate_checkpoint(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Valida el contenido lógico de un checkpoint desencriptado."""
        if not isinstance(data, dict):
            return False, "checkpoint_payload_not_dict"
        state = data.get("state")
        if not isinstance(state, dict):
            return False, "checkpoint_state_missing"
        missing = self.required_state_keys - set(state.keys())
        if missing:
            return False, f"checkpoint_missing_keys:{sorted(missing)}"
        if not (state.get("last_acta_id") or state.get("last_hash")):
            return False, "checkpoint_missing_last_acta_or_hash"
        if not (state.get("current_offset") or state.get("batch_id")):
            return False, "checkpoint_missing_offset_or_batch"
        if state.get("pipeline_version") != self.version:
            return False, "checkpoint_version_mismatch"
        if state.get("run_id") != self.run_id:
            return False, "checkpoint_run_id_mismatch"
        rule_states = state.get("rule_states")
        if not isinstance(rule_states, dict):
            return False, "checkpoint_rule_states_invalid"
        for rule_name, rule_state in rule_states.items():
            if not isinstance(rule_state, dict):
                return False, f"checkpoint_rule_state_invalid:{rule_name}"
            if "status" not in rule_state or "last_error" not in rule_state:
                return False, f"checkpoint_rule_state_missing:{rule_name}"
        return True, "checkpoint_valid"

    async def list_historical_checkpoints(self) -> List[Dict[str, Any]]:
        """Lista los últimos 10 checkpoints históricos."""
        if not self.checkpoint_dir.exists():
            return []
        history = []
        for entry in sorted(self.checkpoint_dir.glob("*.json"), key=lambda p: p.name, reverse=True):
            if entry.name == "latest.json":
                continue
            stat = entry.stat()
            history.append(
                {
                    "path": str(entry),
                    "timestamp": entry.stem,
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                }
            )
        return history[:10]

    async def _decrypt_envelope(self, blob: bytes) -> Dict[str, Any]:
        """Español: Función asíncrona _decrypt_envelope del módulo src/centinel/checkpointing.py.

        English: Async function _decrypt_envelope defined in src/centinel/checkpointing.py.
        """
        try:
            envelope = json.loads(blob.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise CheckpointValidationError("checkpoint_envelope_invalid_json") from exc

        iv_b64 = envelope.get("iv")
        ciphertext = envelope.get("ciphertext")
        ciphertext_hash = envelope.get("ciphertext_hash")
        if not iv_b64 or not ciphertext or not ciphertext_hash:
            raise CheckpointValidationError("checkpoint_envelope_missing_fields")

        encrypted_bytes = ciphertext.encode("utf-8")
        if self._sha256_hex(encrypted_bytes) != ciphertext_hash:
            raise CheckpointValidationError("checkpoint_ciphertext_hash_mismatch")

        try:
            iv = base64.urlsafe_b64decode(iv_b64.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise CheckpointValidationError("checkpoint_iv_invalid") from exc

        fernet = self._derive_fernet(iv)
        try:
            decrypted = fernet.decrypt(encrypted_bytes)
        except InvalidToken as exc:
            raise CheckpointValidationError("checkpoint_decryption_failed") from exc

        try:
            return json.loads(decrypted.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise CheckpointValidationError("checkpoint_payload_invalid_json") from exc

    def _alert_critical(self, code: str, payload: Dict[str, Any]) -> None:
        """Español: Función _alert_critical del módulo src/centinel/checkpointing.py.

        English: Function _alert_critical defined in src/centinel/checkpointing.py.
        """
        if self.alert_callback:
            self.alert_callback(code, payload)
        else:
            self.logger.critical("Alerta crítica de checkpoint.", extra={"code": code, **payload})
            dispatch_alert(
                "CRITICAL",
                f"Fallo crítico en checkpoint: {code}",
                {"code": code, "payload": payload, "source": "checkpointing"},
            )

    def _ensure_required_state(self, state_dict: CheckpointState) -> None:
        """Español: Función _ensure_required_state del módulo src/centinel/checkpointing.py.

        English: Function _ensure_required_state defined in src/centinel/checkpointing.py.
        """
        missing = self.required_state_keys - set(state_dict.keys())
        if missing:
            raise CheckpointValidationError(f"checkpoint_missing_keys:{sorted(missing)}")
        if not (state_dict.get("last_acta_id") or state_dict.get("last_hash")):
            raise CheckpointValidationError("checkpoint_missing_last_acta_or_hash")
        if not (state_dict.get("current_offset") or state_dict.get("batch_id")):
            raise CheckpointValidationError("checkpoint_missing_offset_or_batch")

    def _load_base_key(self) -> bytes:
        """Español: Función _load_base_key del módulo src/centinel/checkpointing.py.

        English: Function _load_base_key defined in src/centinel/checkpointing.py.
        """
        raw_key = os.environ.get(self.encryption_key_env, "")
        if not raw_key:
            raise CheckpointValidationError(
                f"Missing environment variable {self.encryption_key_env} for Fernet key."
            )
        try:
            decoded = base64.urlsafe_b64decode(raw_key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise CheckpointValidationError("checkpoint_key_invalid_base64") from exc
        if len(decoded) != 32:
            raise CheckpointValidationError("checkpoint_key_invalid_length")
        return decoded

    def _derive_fernet(self, iv: bytes) -> Fernet:
        """Español: Función _derive_fernet del módulo src/centinel/checkpointing.py.

        English: Function _derive_fernet defined in src/centinel/checkpointing.py.
        """
        if Fernet is None or HKDF is None or hashes is None:
            raise CheckpointStorageError("cryptography is required for checkpoint encryption")
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=iv,
            info=b"centinel-checkpoint",
        )
        derived_key = hkdf.derive(self._base_key)
        return Fernet(base64.urlsafe_b64encode(derived_key))

    @staticmethod
    def _utc_now() -> str:
        """Español: Función _utc_now del módulo src/centinel/checkpointing.py.

        English: Function _utc_now defined in src/centinel/checkpointing.py.
        """
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _sha256_hex(data: bytes) -> str:
        """Español: Función _sha256_hex del módulo src/centinel/checkpointing.py.

        English: Function _sha256_hex defined in src/centinel/checkpointing.py.
        """
        return hashlib.sha256(data).hexdigest()


def generate_checkpoint_key() -> str:
    """Genera una clave Fernet válida (32 bytes base64)."""
    if Fernet is None:
        raise CheckpointStorageError("cryptography is required to generate checkpoint keys")
    return Fernet.generate_key().decode("utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not os.environ.get("CHECKPOINT_KEY"):
        key = generate_checkpoint_key()
        logging.info(
            "Generated CHECKPOINT_KEY. Export it before running: export CHECKPOINT_KEY='...'"
        )
        logging.debug("CHECKPOINT_KEY_VALUE=%s", key)

    manager = CheckpointManager(
        checkpoint_dir=os.environ.get("CENTINEL_CHECKPOINT_DIR", "checkpoints/"),
        version="v1.0.0",
        run_id="run-2024-11-05-001",
    )

    async def demo_pipeline() -> None:
        """Español: Función asíncrona demo_pipeline del módulo src/centinel/checkpointing.py.

        English: Async function demo_pipeline defined in src/centinel/checkpointing.py.
        """
        checkpoint = await manager.load_latest_checkpoint()
        if checkpoint:
            logging.info("Reanudando desde checkpoint: %s", checkpoint)
        else:
            logging.info("Sin checkpoint válido. Inicio desde cero.")

        processed = 0
        batch_id = "batch-001"
        for acta_id in range(1, 151):
            processed += 1
            state = {
                "last_acta_id": f"acta-{acta_id}",
                "current_offset": processed,
                "accumulated_hash_chain": f"hash-{acta_id}",
                "rule_states": {
                    "benford": {"status": "ok", "last_error": ""},
                    "turnout": {"status": "paused", "last_error": "pause requested"},
                },
                "last_timestamp": manager._utc_now(),
                "pipeline_version": manager.version,
                "run_id": manager.run_id,
                "batch_id": batch_id,
            }

            if processed % 50 == 0:
                await manager.save_checkpoint(state)

            if processed == 120:
                await manager.save_checkpoint(state)
                logging.info("Pausing pipeline for manual review.")
                time.sleep(1)

        await manager.save_checkpoint(state)

    asyncio.run(demo_pipeline())
