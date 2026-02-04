"""Sistema de checkpointing externo, persistente y cifrado para Centinel Engine.

External, persistent, and encrypted checkpointing system for Centinel Engine.
"""

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
from typing import Any, Dict, List, Optional, Tuple

if find_spec("boto3"):
    import boto3
else:
    boto3 = None

if find_spec("botocore"):
    from botocore.config import Config
    from botocore.exceptions import ClientError, EndpointConnectionError
else:
    Config = None

    class ClientError(Exception):
        """Fallback error when botocore is unavailable."""

    class EndpointConnectionError(Exception):
        """Fallback error when botocore is unavailable."""


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

    bucket: str
    pipeline_version: str
    run_id: str
    prefix: str = "centinel/checkpoints"
    encryption_key_env: str = "CHECKPOINT_KEY"
    checkpoint_interval: int = 50
    s3_endpoint_url: Optional[str] = None
    s3_region: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None


class CheckpointError(Exception):
    """Base error for checkpoint operations."""


class CheckpointStorageError(CheckpointError):
    """Raised when storage operations fail after retries."""


class CheckpointValidationError(CheckpointError):
    """Raised when checkpoint content is invalid or corrupt."""


class CheckpointManager:
    """Administra checkpoints cifrados en un bucket S3-compatible.

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
        config: CheckpointConfig | str | None = None,
        *,
        bucket_name: str | None = None,
        prefix: str = "centinel/checkpoints",
        version: str | None = None,
        run_id: str | None = None,
        encryption_key_env: str = "CHECKPOINT_KEY",
        s3_client: Any | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Español: Función __init__ del módulo src/centinel/checkpointing.py.

        English: Function __init__ defined in src/centinel/checkpointing.py.
        """
        if isinstance(config, CheckpointConfig):
            resolved = config
        else:
            if config is not None and bucket_name is None:
                bucket_name = config if isinstance(config, str) else None
            if not bucket_name or not version or not run_id:
                raise CheckpointValidationError("checkpoint_config_missing_fields")
            resolved = CheckpointConfig(
                bucket=bucket_name,
                pipeline_version=version,
                run_id=run_id,
                prefix=prefix,
                encryption_key_env=encryption_key_env,
            )

        self.config = resolved
        self.bucket_name = resolved.bucket
        self.prefix = resolved.prefix.rstrip("/")
        self.version = resolved.pipeline_version
        self.run_id = resolved.run_id
        self.encryption_key_env = resolved.encryption_key_env
        self.checkpoint_interval = resolved.checkpoint_interval
        self.logger = logger or logging.getLogger(__name__)
        self._timeout_seconds = 15
        self._base_key = self._load_base_key()
        self._s3_client = s3_client or self._build_s3_client()

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
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode(
            "utf-8"
        )

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

        latest_key = self._latest_key()
        history_key = self._history_key(timestamp)

        await self._put_object_with_retry(latest_key, blob)
        await self._put_object_with_retry(history_key, blob)
        self.logger.info(
            "checkpoint_saved",
            extra={
                "checkpoint_key": latest_key,
                "checkpoint_hash": encrypted_hash,
                "timestamp": timestamp,
            },
        )
        return encrypted_hash

    async def load_latest_checkpoint(self) -> Optional[CheckpointState]:
        """Carga el último checkpoint válido desde el bucket.

        Returns:
            Estado del pipeline si existe un checkpoint válido; ``None`` si no hay.
        """
        latest_key = self._latest_key()
        try:
            raw_blob = await self._get_object_with_retry(latest_key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                self.logger.warning(
                    "checkpoint_not_found",
                    extra={"checkpoint_key": latest_key},
                )
                return None
            raise
        except EndpointConnectionError as exc:
            self.logger.warning(
                "checkpoint_endpoint_unreachable",
                extra={"checkpoint_key": latest_key, "error": str(exc)},
            )
            return None

        try:
            payload = await self._decrypt_envelope(raw_blob)
        except CheckpointValidationError as exc:
            self.logger.warning(
                "checkpoint_decrypt_failed",
                extra={"checkpoint_key": latest_key, "error": str(exc)},
            )
            return None
        is_valid, reason = await self.validate_checkpoint(payload)
        if not is_valid:
            self.logger.warning(
                "checkpoint_invalid",
                extra={"checkpoint_key": latest_key, "reason": reason},
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
        prefix = self._base_prefix()
        response = await self._list_objects_with_retry(prefix)
        contents = response.get("Contents", [])
        history = []
        for entry in contents:
            key = entry.get("Key", "")
            if not key.endswith(".json.enc") or key.endswith("latest.json.enc"):
                continue
            timestamp = key.split("/")[-1].replace(".json.enc", "")
            history.append(
                {
                    "key": key,
                    "timestamp": timestamp,
                    "size": entry.get("Size"),
                    "last_modified": (
                        entry.get("LastModified").isoformat()
                        if entry.get("LastModified")
                        else None
                    ),
                }
            )
        history.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
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

    async def _put_object_with_retry(self, key: str, data: bytes) -> None:
        """Español: Función asíncrona _put_object_with_retry del módulo src/centinel/checkpointing.py.

        English: Async function _put_object_with_retry defined in src/centinel/checkpointing.py.
        """
        for attempt in range(1, 6):
            try:
                await self._run_with_timeout(
                    self._put_object,
                    key,
                    data,
                )
                return
            except (ClientError, EndpointConnectionError, asyncio.TimeoutError) as exc:
                self.logger.warning(
                    "checkpoint_write_retry",
                    extra={
                        "checkpoint_key": key,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
                if attempt == 5:
                    self.logger.critical(
                        "checkpoint_write_failed",
                        extra={"checkpoint_key": key, "error": str(exc)},
                    )
                    raise CheckpointStorageError("checkpoint_write_failed") from exc
                await asyncio.sleep(2 ** (attempt - 1))

    def _alert_critical(self, code: str, payload: Dict[str, Any]) -> None:
        """Español: Función _alert_critical del módulo src/centinel/checkpointing.py.

        English: Function _alert_critical defined in src/centinel/checkpointing.py.
        """
        if self.alert_callback:
            self.alert_callback(code, payload)
        else:
            self.logger.critical(
                "Alerta crítica de checkpoint.", extra={"code": code, **payload}
            )
            dispatch_alert(
                "CRITICAL",
                f"Fallo crítico en checkpoint: {code}",
                {"code": code, "payload": payload, "source": "checkpointing"},
            )

    def _list_objects_raw(self, prefix: str) -> Dict[str, Any]:
        """Español: Función _list_objects_raw del módulo src/centinel/checkpointing.py.

        English: Function _list_objects_raw defined in src/centinel/checkpointing.py.
        """
        return self._s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)

    def _ensure_required_state(self, state_dict: CheckpointState) -> None:
        """Español: Función _ensure_required_state del módulo src/centinel/checkpointing.py.

        English: Function _ensure_required_state defined in src/centinel/checkpointing.py.
        """
        missing = self.required_state_keys - set(state_dict.keys())
        if missing:
            raise CheckpointValidationError(
                f"checkpoint_missing_keys:{sorted(missing)}"
            )
        if not (state_dict.get("last_acta_id") or state_dict.get("last_hash")):
            raise CheckpointValidationError("checkpoint_missing_last_acta_or_hash")
        if not (state_dict.get("current_offset") or state_dict.get("batch_id")):
            raise CheckpointValidationError("checkpoint_missing_offset_or_batch")

    def _latest_key(self) -> str:
        """Español: Función _latest_key del módulo src/centinel/checkpointing.py.

        English: Function _latest_key defined in src/centinel/checkpointing.py.
        """
        return f"{self._base_prefix()}/latest.json.enc"

    def _history_key(self, timestamp: str) -> str:
        """Español: Función _history_key del módulo src/centinel/checkpointing.py.

        English: Function _history_key defined in src/centinel/checkpointing.py.
        """
        return f"{self._base_prefix()}/{timestamp}.json.enc"

    def _base_prefix(self) -> str:
        """Español: Función _base_prefix del módulo src/centinel/checkpointing.py.

        English: Function _base_prefix defined in src/centinel/checkpointing.py.
        """
        return f"{self.prefix}/{self.version}/{self.run_id}"

    def _build_s3_client(self) -> Any:
        """Español: Función _build_s3_client del módulo src/centinel/checkpointing.py.

        English: Function _build_s3_client defined in src/centinel/checkpointing.py.
        """
        if boto3 is None or Config is None:
            raise CheckpointStorageError(
                "boto3 and botocore are required for checkpoint storage"
            )
        endpoint = (
            self.config.s3_endpoint_url
            or os.environ.get("CENTINEL_S3_ENDPOINT")
            or os.environ.get("S3_ENDPOINT_URL")
        )
        region = (
            self.config.s3_region
            or os.environ.get("AWS_REGION")
            or os.environ.get("CENTINEL_S3_REGION")
        )
        config = Config(
            connect_timeout=self._timeout_seconds, read_timeout=self._timeout_seconds
        )
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=self.config.s3_access_key,
            aws_secret_access_key=self.config.s3_secret_key,
            config=config,
        )

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
            raise CheckpointStorageError(
                "cryptography is required for checkpoint encryption"
            )
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
        raise CheckpointStorageError(
            "cryptography is required to generate checkpoint keys"
        )
    return Fernet.generate_key().decode("utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not os.environ.get("CHECKPOINT_KEY"):
        key = generate_checkpoint_key()
        print("Generated CHECKPOINT_KEY:", key)
        print("Export it before running: export CHECKPOINT_KEY='...'\n")

    manager = CheckpointManager(
        bucket_name=os.environ.get(
            "CENTINEL_CHECKPOINT_BUCKET", "centinel-checkpoints"
        ),
        prefix="centinel/checkpoints",
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
