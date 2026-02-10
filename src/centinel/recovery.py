"""Gestión de recuperación tras reinicios o caídas del pipeline.

English:
    Recovery management after restarts or crashes in the pipeline.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Mapping, Optional


class RecoveryError(Exception):
    """Error general durante la recuperación.

    English: Generic recovery error.
    """


class CheckpointLoadError(RecoveryError):
    """Error al cargar un checkpoint.

    English: Error while loading a checkpoint.
    """


class CheckpointCorruptError(RecoveryError):
    """Checkpoint corrupto o inválido.

    English: Corrupt or invalid checkpoint.
    """

    def __init__(self, message: str, *, partial: bool = False) -> None:
        """Español: Función __init__ del módulo src/centinel/recovery.py.

        English: Function __init__ defined in src/centinel/recovery.py.
        """
        super().__init__(message)
        self.partial = partial


class RecoveryDecisionType(str, Enum):
    """Tipos de decisión de recuperación.

    English: Recovery decision types.
    """

    START_FROM_BEGINNING = "start_from_beginning"
    CONTINUE_FROM_LAST_ACTA = "continue_from_last_acta"
    REPROCESS_LAST_BATCH = "reprocess_last_batch"
    SKIP_TO_NEXT_VALID = "skip_to_next_valid"
    PAUSE_AND_ALERT = "pause_and_alert"


@dataclass(frozen=True)
class RecoveryDecision:
    """Resultado de la recuperación.

    English: Recovery result.
    """

    decision: RecoveryDecisionType
    reason: str
    acta_id: Optional[str] = None
    offset: Optional[int] = None
    batch_id: Optional[str] = None
    checkpoint_path: Optional[Path] = None
    checkpoint_age_minutes: Optional[float] = None
    alerts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckpointData:
    """Contenido validado de un checkpoint.

    English: Validated checkpoint payload.
    """

    acta_id: str
    offset: int
    batch_id: str
    created_at: datetime
    source_format: Optional[str] = None
    checksum: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CheckpointData":
        """Construye un checkpoint validado desde un mapping.

        English: Build a validated checkpoint from a mapping.
        """
        try:
            acta_id = str(data["acta_id"])
            offset = int(data["offset"])
            batch_id = str(data["batch_id"])
            created_at = _parse_timestamp(data["created_at"])
        except KeyError as exc:
            raise CheckpointCorruptError(f"Missing required checkpoint field: {exc}", partial=False) from exc
        except (TypeError, ValueError) as exc:
            raise CheckpointCorruptError(f"Invalid checkpoint field type: {exc}", partial=False) from exc

        if offset < 0:
            raise CheckpointCorruptError("Checkpoint offset must be >= 0.", partial=False)

        return cls(
            acta_id=acta_id,
            offset=offset,
            batch_id=batch_id,
            created_at=created_at,
            source_format=data.get("source_format"),
            checksum=data.get("checksum"),
            metadata={
                key: value
                for key, value in data.items()
                if key
                not in {
                    "acta_id",
                    "offset",
                    "batch_id",
                    "created_at",
                    "source_format",
                    "checksum",
                }
            },
        )


@dataclass(frozen=True)
class RecoveryState:
    """Estado real del pipeline para comparar con checkpoint.

    English: Real pipeline state for checkpoint comparison.
    """

    last_acta_id: Optional[str] = None
    last_offset: Optional[int] = None
    last_batch_id: Optional[str] = None
    source_format: Optional[str] = None
    is_consistent: bool = True
    notes: Optional[str] = None


StateProbe = Callable[[], Awaitable[RecoveryState]]


class RecoveryManager:
    """Gestiona la lógica de recuperación del pipeline.

    The manager loads checkpoints, validates integrity, and decides how to
    resume the pipeline based on recency, corruption, and source changes.

    Example:
        >>> settings = load_config()
        >>> logger = setup_logging(settings.LOG_LEVEL, settings.STORAGE_PATH)
        >>> recovery_manager = RecoveryManager(
        ...     storage_path=settings.STORAGE_PATH,
        ...     logger=logger,
        ...     expected_source_format="cne_actas_v1",
        ...     stale_checkpoint_policy="continue",
        ... )
        >>> decision = await recovery_manager.recover()
        >>> if decision.decision is RecoveryDecisionType.CONTINUE_FROM_LAST_ACTA:
        ...     cursor.acta_id = decision.acta_id
        ...     cursor.offset = decision.offset
        ...     cursor.batch_id = decision.batch_id
        ... elif decision.decision is RecoveryDecisionType.REPROCESS_LAST_BATCH:
        ...     cursor.reprocess_last_batch()
        ... elif decision.decision is RecoveryDecisionType.START_FROM_BEGINNING:
        ...     cursor.reset()
        ... elif decision.decision is RecoveryDecisionType.PAUSE_AND_ALERT:
        ...     alerting.notify(decision.reason)
        ...     return
    """

    def __init__(
        self,
        *,
        storage_path: Path,
        logger: Optional[logging.Logger] = None,
        expected_source_format: Optional[str] = None,
        stale_checkpoint_policy: str = "pause",
        recent_threshold_minutes: int = 15,
        stale_threshold_minutes: int = 60,
        state_probe: Optional[StateProbe] = None,
    ) -> None:
        """Español: Función __init__ del módulo src/centinel/recovery.py.

        English: Function __init__ defined in src/centinel/recovery.py.
        """
        self.storage_path = storage_path
        self.checkpoint_dir = storage_path / "checkpoints"
        self.logger = logger or logging.getLogger(__name__)
        self.expected_source_format = expected_source_format
        self.stale_checkpoint_policy = stale_checkpoint_policy
        self.recent_threshold_minutes = recent_threshold_minutes
        self.stale_threshold_minutes = stale_threshold_minutes
        self.state_probe = state_probe

    async def recover(self) -> RecoveryDecision:
        """Ejecuta la lógica completa de recuperación.

        English:
            Executes the full recovery logic.
        """
        self.logger.info("recovery_start", checkpoint_dir=str(self.checkpoint_dir))
        candidate_paths = list(_checkpoint_candidates(self.checkpoint_dir))
        if not candidate_paths:
            message = "No checkpoint files found. Starting from beginning."
            self.logger.error("recovery_no_checkpoint", reason=message)
            return RecoveryDecision(
                decision=RecoveryDecisionType.START_FROM_BEGINNING,
                reason=message,
                alerts=["Critical: no checkpoint available."],
            )

        checkpoint, checkpoint_path, warnings, last_error = _load_first_valid(candidate_paths)
        for warning in warnings:
            self.logger.warning("recovery_checkpoint_warning", warning=warning)

        if checkpoint is None:
            if isinstance(last_error, CheckpointCorruptError) and last_error.partial:
                message = "Checkpoint partially corrupt; reprocessing last batch."
                self.logger.error("recovery_partial_corruption", reason=message, error=str(last_error))
                return RecoveryDecision(
                    decision=RecoveryDecisionType.REPROCESS_LAST_BATCH,
                    reason=message,
                    alerts=["Checkpoint partially corrupt."],
                )
            message = "No valid checkpoint available. Starting from beginning."
            self.logger.error(
                "recovery_no_valid_checkpoint",
                reason=message,
                error=str(last_error) if last_error else None,
            )
            return RecoveryDecision(
                decision=RecoveryDecisionType.START_FROM_BEGINNING,
                reason=message,
                alerts=["Critical: no valid checkpoint."],
            )

        self.logger.info(
            "recovery_checkpoint_loaded",
            checkpoint_path=str(checkpoint_path),
            acta_id=checkpoint.acta_id,
            offset=checkpoint.offset,
            batch_id=checkpoint.batch_id,
            created_at=checkpoint.created_at.isoformat(),
        )

        if (
            self.expected_source_format
            and checkpoint.source_format
            and checkpoint.source_format != self.expected_source_format
        ):
            message = "Source format changed; pausing to avoid unsafe recovery."
            self.logger.error(
                "recovery_source_format_mismatch",
                expected=self.expected_source_format,
                found=checkpoint.source_format,
            )
            return RecoveryDecision(
                decision=RecoveryDecisionType.PAUSE_AND_ALERT,
                reason=message,
                checkpoint_path=checkpoint_path,
                alerts=[message],
            )

        state = None
        if self.state_probe:
            state = await self.state_probe()
            self._log_state_differences(checkpoint, state)
            if state.source_format and (
                self.expected_source_format and state.source_format != self.expected_source_format
            ):
                message = "Source format changed in live state; pausing recovery."
                self.logger.error(
                    "recovery_live_source_format_mismatch",
                    expected=self.expected_source_format,
                    found=state.source_format,
                )
                return RecoveryDecision(
                    decision=RecoveryDecisionType.PAUSE_AND_ALERT,
                    reason=message,
                    checkpoint_path=checkpoint_path,
                    alerts=[message],
                )
            if not state.is_consistent:
                message = "Detected irrecoverable gaps; skipping to next valid point."
                self.logger.error(
                    "recovery_state_inconsistent",
                    reason=message,
                    notes=state.notes,
                )
                return RecoveryDecision(
                    decision=RecoveryDecisionType.SKIP_TO_NEXT_VALID,
                    reason=message,
                    checkpoint_path=checkpoint_path,
                    alerts=[message],
                    metadata={"state_notes": state.notes},
                )

        age_minutes = _age_minutes(checkpoint.created_at)
        decision = self._decide_from_age(checkpoint, checkpoint_path, age_minutes)
        self.logger.info(
            "recovery_decision",
            decision=decision.decision.value,
            reason=decision.reason,
            checkpoint_age_minutes=age_minutes,
        )
        return decision

    def _decide_from_age(self, checkpoint: CheckpointData, path: Path, age_minutes: float) -> RecoveryDecision:
        """Español: Función _decide_from_age del módulo src/centinel/recovery.py.

        English: Function _decide_from_age defined in src/centinel/recovery.py.
        """
        if age_minutes <= self.recent_threshold_minutes:
            reason = "Checkpoint is recent; continuing from last acta."
            return RecoveryDecision(
                decision=RecoveryDecisionType.CONTINUE_FROM_LAST_ACTA,
                reason=reason,
                acta_id=checkpoint.acta_id,
                offset=checkpoint.offset,
                batch_id=checkpoint.batch_id,
                checkpoint_path=path,
                checkpoint_age_minutes=age_minutes,
            )

        if age_minutes >= self.stale_threshold_minutes:
            policy = self.stale_checkpoint_policy
            if policy == "continue":
                reason = "Checkpoint is stale; configured to continue."
                return RecoveryDecision(
                    decision=RecoveryDecisionType.CONTINUE_FROM_LAST_ACTA,
                    reason=reason,
                    acta_id=checkpoint.acta_id,
                    offset=checkpoint.offset,
                    batch_id=checkpoint.batch_id,
                    checkpoint_path=path,
                    checkpoint_age_minutes=age_minutes,
                )
            if policy == "reprocess":
                reason = "Checkpoint is stale; configured to reprocess last batch."
                return RecoveryDecision(
                    decision=RecoveryDecisionType.REPROCESS_LAST_BATCH,
                    reason=reason,
                    acta_id=checkpoint.acta_id,
                    offset=checkpoint.offset,
                    batch_id=checkpoint.batch_id,
                    checkpoint_path=path,
                    checkpoint_age_minutes=age_minutes,
                )
            reason = "Checkpoint is stale; pausing for operator decision."
            return RecoveryDecision(
                decision=RecoveryDecisionType.PAUSE_AND_ALERT,
                reason=reason,
                checkpoint_path=path,
                alerts=[reason],
                checkpoint_age_minutes=age_minutes,
            )

        reason = "Checkpoint is moderately old; continuing from last acta."
        return RecoveryDecision(
            decision=RecoveryDecisionType.CONTINUE_FROM_LAST_ACTA,
            reason=reason,
            acta_id=checkpoint.acta_id,
            offset=checkpoint.offset,
            batch_id=checkpoint.batch_id,
            checkpoint_path=path,
            checkpoint_age_minutes=age_minutes,
        )

    def _log_state_differences(self, checkpoint: CheckpointData, state: RecoveryState) -> None:
        """Español: Función _log_state_differences del módulo src/centinel/recovery.py.

        English: Function _log_state_differences defined in src/centinel/recovery.py.
        """
        differences: dict[str, Any] = {}
        if state.last_acta_id and state.last_acta_id != checkpoint.acta_id:
            differences["acta_id"] = {
                "checkpoint": checkpoint.acta_id,
                "state": state.last_acta_id,
            }
        if state.last_offset is not None and state.last_offset != checkpoint.offset:
            differences["offset"] = {
                "checkpoint": checkpoint.offset,
                "state": state.last_offset,
            }
        if state.last_batch_id and state.last_batch_id != checkpoint.batch_id:
            differences["batch_id"] = {
                "checkpoint": checkpoint.batch_id,
                "state": state.last_batch_id,
            }
        if differences:
            self.logger.warning(
                "recovery_state_mismatch",
                differences=differences,
            )


def _checkpoint_candidates(checkpoint_dir: Path) -> Iterable[Path]:
    """Español: Función _checkpoint_candidates del módulo src/centinel/recovery.py.

    English: Function _checkpoint_candidates defined in src/centinel/recovery.py.
    """
    if not checkpoint_dir.exists():
        return []
    candidates = set()
    primary = checkpoint_dir / "checkpoint.json"
    if primary.exists():
        candidates.add(primary)
    for pattern in ("checkpoint*.json", "checkpoint*.bak"):
        for path in checkpoint_dir.glob(pattern):
            if path.is_file():
                candidates.add(path)
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)


def _load_first_valid(
    candidates: Iterable[Path],
) -> tuple[Optional[CheckpointData], Optional[Path], list[str], Optional[Exception]]:
    """Español: Función _load_first_valid del módulo src/centinel/recovery.py.

    English: Function _load_first_valid defined in src/centinel/recovery.py.
    """
    warnings: list[str] = []
    last_error: Optional[Exception] = None
    for path in candidates:
        try:
            checkpoint, checkpoint_warnings = _load_checkpoint(path)
            warnings.extend(checkpoint_warnings)
            return checkpoint, path, warnings, None
        except (CheckpointLoadError, CheckpointCorruptError) as exc:
            last_error = exc
            warnings.append(f"Checkpoint {path} rejected: {exc}")
    return None, None, warnings, last_error


def _load_checkpoint(path: Path) -> tuple[CheckpointData, list[str]]:
    """Español: Función _load_checkpoint del módulo src/centinel/recovery.py.

    English: Function _load_checkpoint defined in src/centinel/recovery.py.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckpointLoadError(f"Failed to read checkpoint: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CheckpointCorruptError(f"Checkpoint JSON is invalid: {exc}", partial=False) from exc

    if not isinstance(data, dict):
        raise CheckpointCorruptError("Checkpoint must be a JSON object.", partial=False)

    checkpoint = CheckpointData.from_mapping(data)
    warnings: list[str] = []

    if checkpoint.checksum:
        payload = {key: value for key, value in data.items() if key != "checksum"}
        expected = _checksum_payload(payload)
        if expected != checkpoint.checksum:
            raise CheckpointCorruptError("Checkpoint checksum mismatch.", partial=True)
    else:
        warnings.append("Checkpoint without checksum; integrity not fully verified.")

    return checkpoint, warnings


def _parse_timestamp(value: Any) -> datetime:
    """Español: Función _parse_timestamp del módulo src/centinel/recovery.py.

    English: Function _parse_timestamp defined in src/centinel/recovery.py.
    """
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if not isinstance(value, str):
        raise ValueError("Timestamp must be ISO-8601 string.")
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _age_minutes(timestamp: datetime) -> float:
    """Español: Función _age_minutes del módulo src/centinel/recovery.py.

    English: Function _age_minutes defined in src/centinel/recovery.py.
    """
    now = datetime.now(timezone.utc)
    return (now - timestamp).total_seconds() / 60.0


def _checksum_payload(payload: Mapping[str, Any]) -> str:
    """Español: Función _checksum_payload del módulo src/centinel/recovery.py.

    English: Function _checksum_payload defined in src/centinel/recovery.py.
    """
    payload_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload_bytes).hexdigest()
