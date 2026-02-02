"""Sistema de checkpointing externo y persistente para Centinel Engine.

External and persistent checkpointing system for Centinel Engine.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from cryptography.fernet import Fernet, InvalidToken


AlertCallback = Callable[[str, Dict[str, Any]], None]


@dataclass(frozen=True)
class CheckpointConfig:
    """Configuración principal para el checkpointing.

    English: Main configuration for checkpointing.
    """

    bucket: str
    pipeline_version: str
    run_id: str
    checkpoint_interval: int = 50
    s3_endpoint_url: Optional[str] = None
    s3_region: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None


class CheckpointManager:
    """Administra checkpoints persistentes con cifrado y hashing.

    This manager stores encrypted checkpoints in a S3-compatible bucket,
    validates integrity, retries writes with backoff, and allows recovery
    after container or host restarts.
    """

    required_state_keys = {
        "last_acta_id",
        "last_batch_offset",
        "rules_state",
        "hash_accumulator",
    }

    def __init__(
        self,
        config: CheckpointConfig,
        *,
        s3_client: Optional[Any] = None,
        alert_callback: Optional[AlertCallback] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config
        self.alert_callback = alert_callback
        self.logger = logger or logging.getLogger(__name__)
        self._fernet = self._build_fernet()
        self._s3_client = s3_client or self._build_s3_client()

    def __enter__(self) -> "CheckpointManager":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def save_checkpoint(self, state_dict: Dict[str, Any]) -> None:
        """Guarda un checkpoint cifrado en el bucket S3.

        Args:
            state_dict: Estado del pipeline que debe incluir las llaves
                mínimas definidas en ``required_state_keys``.
        """
        timestamp = self._utc_now()
        state_dict = dict(state_dict)
        state_dict.setdefault("checkpoint_timestamp", timestamp)
        state_dict.setdefault("pipeline_version", self.config.pipeline_version)
        self._ensure_required_state(state_dict)

        payload = {
            "state": state_dict,
            "metadata": {
                "run_id": self.config.run_id,
                "pipeline_version": self.config.pipeline_version,
                "checkpoint_timestamp": timestamp,
            },
        }

        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        payload_hash = self._sha256_hex(serialized)
        encrypted_payload = self._fernet.encrypt(serialized)

        envelope = {
            "schema_version": 1,
            "pipeline_version": self.config.pipeline_version,
            "run_id": self.config.run_id,
            "checkpoint_timestamp": timestamp,
            "payload_hash": payload_hash,
            "encrypted_payload_hash": self._sha256_hex(encrypted_payload),
            "encrypted_payload": encrypted_payload.decode("utf-8"),
        }

        latest_key = self._latest_key()
        history_key = self._history_key(timestamp)
        data = json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")

        self._put_object_with_retry(latest_key, data)
        self._put_object_with_retry(history_key, data)

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Carga el último checkpoint válido desde S3.

        Returns:
            Un dict con el estado recuperado si es válido; ``None`` en caso contrario.
        """
        latest_key = self._latest_key()
        try:
            response = self._s3_client.get_object(
                Bucket=self.config.bucket,
                Key=latest_key,
            )
            raw_bytes = response["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                self.logger.warning(
                    "Checkpoint no encontrado. Se inicia desde cero.",
                    extra={"checkpoint_key": latest_key},
                )
                return None
            raise
        except EndpointConnectionError:
            self.logger.warning(
                "No se pudo conectar al endpoint S3 para cargar checkpoint.",
                extra={"checkpoint_key": latest_key},
            )
            return None

        payload = self.validate_checkpoint_integrity(raw_bytes)
        if payload is None:
            self.logger.warning(
                "Checkpoint corrupto o inválido. Se inicia desde cero.",
                extra={"checkpoint_key": latest_key},
            )
            return None

        state = payload.get("state", {})
        if state.get("pipeline_version") != self.config.pipeline_version:
            self.logger.warning(
                "Checkpoint incompatible con la versión del pipeline.",
                extra={
                    "expected": self.config.pipeline_version,
                    "found": state.get("pipeline_version"),
                },
            )
            return None

        return state

    def validate_checkpoint_integrity(
        self,
        checkpoint_blob: Optional[bytes] = None,
    ) -> Optional[Dict[str, Any]]:
        """Valida la integridad del checkpoint.

        Args:
            checkpoint_blob: Contenido opcional del checkpoint en bytes. Si no
                se provee, se carga desde ``latest.json``.

        Returns:
            El payload descifrado si pasa todas las validaciones; ``None`` si falla.
        """
        if checkpoint_blob is None:
            try:
                response = self._s3_client.get_object(
                    Bucket=self.config.bucket,
                    Key=self._latest_key(),
                )
                checkpoint_blob = response["Body"].read()
            except ClientError:
                return None

        try:
            envelope = json.loads(checkpoint_blob.decode("utf-8"))
        except json.JSONDecodeError:
            return None

        encrypted_payload = envelope.get("encrypted_payload")
        encrypted_hash = envelope.get("encrypted_payload_hash")
        payload_hash = envelope.get("payload_hash")

        if not encrypted_payload or not encrypted_hash or not payload_hash:
            return None

        encrypted_bytes = encrypted_payload.encode("utf-8")
        if self._sha256_hex(encrypted_bytes) != encrypted_hash:
            return None

        try:
            decrypted = self._fernet.decrypt(encrypted_bytes)
        except InvalidToken:
            return None

        if self._sha256_hex(decrypted) != payload_hash:
            return None

        try:
            payload = json.loads(decrypted.decode("utf-8"))
        except json.JSONDecodeError:
            return None

        if payload.get("metadata", {}).get("pipeline_version") != self.config.pipeline_version:
            return None

        return payload

    def _build_s3_client(self) -> Any:
        session = boto3.session.Session()
        return session.client(
            "s3",
            endpoint_url=self.config.s3_endpoint_url,
            region_name=self.config.s3_region,
            aws_access_key_id=self.config.s3_access_key,
            aws_secret_access_key=self.config.s3_secret_key,
        )

    def _put_object_with_retry(self, key: str, data: bytes) -> None:
        for attempt in range(1, 4):
            try:
                self._s3_client.put_object(
                    Bucket=self.config.bucket,
                    Key=key,
                    Body=data,
                    ContentType="application/json",
                )
                return
            except (ClientError, EndpointConnectionError) as exc:
                self.logger.error(
                    "Error guardando checkpoint en S3.",
                    extra={"checkpoint_key": key, "attempt": attempt, "error": str(exc)},
                )
                if attempt == 3:
                    self._alert_critical(
                        "checkpoint_write_failed",
                        {"checkpoint_key": key, "error": str(exc)},
                    )
                    raise RuntimeError("No se pudo guardar el checkpoint en S3.") from exc
                time.sleep(2 ** (attempt - 1))

    def _alert_critical(self, code: str, payload: Dict[str, Any]) -> None:
        if self.alert_callback:
            self.alert_callback(code, payload)
        else:
            self.logger.critical("Alerta crítica de checkpoint.", extra={"code": code, **payload})

    def _ensure_required_state(self, state_dict: Dict[str, Any]) -> None:
        missing = self.required_state_keys - set(state_dict.keys())
        if missing:
            raise ValueError(f"Checkpoint incompleto. Faltan llaves: {sorted(missing)}")

    def _latest_key(self) -> str:
        return (
            f"centinel/checkpoints/{self.config.pipeline_version}/"
            f"{self.config.run_id}/latest.json"
        )

    def _history_key(self, timestamp: str) -> str:
        return (
            f"centinel/checkpoints/{self.config.pipeline_version}/"
            f"{self.config.run_id}/{timestamp}.json"
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _sha256_hex(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _build_fernet() -> Fernet:
        secret = os.environ.get("CENTINEL_CHECKPOINT_SECRET", "")
        if not secret:
            raise ValueError("Falta la variable CENTINEL_CHECKPOINT_SECRET para cifrado.")
        salt = os.environ.get("CENTINEL_CHECKPOINT_SALT", "")
        digest = hashlib.sha256(f"{secret}{salt}".encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = CheckpointConfig(
        bucket=os.environ.get("CENTINEL_CHECKPOINT_BUCKET", "centinel-checkpoints"),
        pipeline_version="v1.0.0",
        run_id="run-2024-11-05-001",
        checkpoint_interval=50,
        s3_endpoint_url=os.environ.get("CENTINEL_S3_ENDPOINT"),
        s3_region=os.environ.get("CENTINEL_S3_REGION"),
        s3_access_key=os.environ.get("CENTINEL_S3_ACCESS_KEY"),
        s3_secret_key=os.environ.get("CENTINEL_S3_SECRET_KEY"),
    )

    def alerting(code: str, payload: Dict[str, Any]) -> None:
        logging.critical("ALERTA: %s -> %s", code, payload)

    manager = CheckpointManager(config, alert_callback=alerting)

    checkpoint = manager.load_checkpoint()
    if checkpoint:
        logging.info("Reanudando desde checkpoint: %s", checkpoint)
    else:
        logging.info("Sin checkpoint válido. Inicio desde cero.")

    processed = 0
    for acta_id in range(1, 151):
        processed += 1
        state = {
            "last_acta_id": f"acta-{acta_id}",
            "last_batch_offset": processed,
            "rules_state": {"benford": "ok", "turnout": "paused"},
            "hash_accumulator": f"hash-{acta_id}",
            "checkpoint_timestamp": manager._utc_now(),
            "pipeline_version": config.pipeline_version,
        }

        if processed % config.checkpoint_interval == 0:
            manager.save_checkpoint(state)

    manager.save_checkpoint(state)
