"""Internal library — not a CLI entry point. Imported by pipeline modules.

======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `scripts/circuit_breaker.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - CircuitBreaker

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `scripts/circuit_breaker.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - CircuitBreaker

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Circuit Breaker Module
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

import hashlib
import hmac
import json
import logging
import os
import shutil
import tempfile
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Optional


_LOGGER = logging.getLogger("centinel.circuit_breaker")

_STATE_SECRET_FILENAME = ".circuit_breaker_secret"


def _resolve_state_hmac_key(state_path: Path) -> bytes:
    """Resolve the HMAC key protecting persisted breaker state.

    Priority: CENTINEL_STATE_HMAC_KEY env var (>=16 chars) else a
    local random secret file (0600) created next to the state file.
    The secret protects against an attacker who edits or truncates the
    state JSON to silently reset the breaker to CLOSED and re-open the
    DoS window. Tampering invalidates the MAC, so a forged state is
    rejected instead of trusted.
    """
    env_key = os.getenv("CENTINEL_STATE_HMAC_KEY", "").strip()
    if len(env_key) >= 16:
        return env_key.encode("utf-8")
    secret_path = state_path.parent / _STATE_SECRET_FILENAME
    try:
        existing = secret_path.read_text(encoding="utf-8").strip()
        if existing:
            return existing.encode("utf-8")
    except OSError:
        pass
    generated = hashlib.sha256(os.urandom(32)).hexdigest()
    try:
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        secret_path.write_text(generated, encoding="utf-8")
        os.chmod(secret_path, 0o600)
    except OSError:
        pass
    return generated.encode("utf-8")


def _compute_state_mac(payload: bytes, key: bytes) -> str:
    """Return the hex HMAC-SHA256 of a serialized state payload."""
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an optional ISO-8601 timestamp into an aware UTC datetime."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


@dataclass
class CircuitBreaker:
    """/** Circuit breaker con estados CLOSED/OPEN/HALF-OPEN. / Circuit breaker with CLOSED/OPEN/HALF-OPEN states. **/"""

    failure_threshold: int = 5
    failure_window_seconds: int = 600
    open_timeout_seconds: int = 1800
    half_open_after_seconds: int = 600
    success_threshold: int = 2
    open_log_interval_seconds: int = 300
    state: str = "CLOSED"
    _failures: Deque[datetime] = field(default_factory=deque)
    _opened_at: datetime | None = None
    _next_log_at: datetime | None = None
    _half_open_successes: int = 0
    _alert_sent: bool = False

    def _now(self) -> datetime:
        """Español: Función _now del módulo scripts/circuit_breaker.py.

        English: Function _now defined in scripts/circuit_breaker.py.
        """
        return datetime.now(timezone.utc)

    def _trim_failures(self, now: datetime) -> None:
        """Español: Función _trim_failures del módulo scripts/circuit_breaker.py.

        English: Function _trim_failures defined in scripts/circuit_breaker.py.
        """
        window = timedelta(seconds=self.failure_window_seconds)
        while self._failures and now - self._failures[0] > window:
            self._failures.popleft()

    def _open(self, now: datetime) -> bool:
        """Español: Función _open del módulo scripts/circuit_breaker.py.

        English: Function _open defined in scripts/circuit_breaker.py.
        """
        if self.state == "OPEN":
            return False
        self.state = "OPEN"
        self._opened_at = now
        self._next_log_at = now
        self._half_open_successes = 0
        self._alert_sent = False
        return True

    def _half_open(self, now: datetime) -> None:
        """Español: Función _half_open del módulo scripts/circuit_breaker.py.

        English: Function _half_open defined in scripts/circuit_breaker.py.
        """
        self.state = "HALF_OPEN"
        self._half_open_successes = 0
        self._opened_at = now
        self._next_log_at = None

    def _close(self) -> None:
        """Español: Función _close del módulo scripts/circuit_breaker.py.

        English: Function _close defined in scripts/circuit_breaker.py.
        """
        self.state = "CLOSED"
        self._failures.clear()
        self._opened_at = None
        self._next_log_at = None
        self._half_open_successes = 0
        self._alert_sent = False

    def _next_half_open_at(self) -> datetime | None:
        """Español: Función _next_half_open_at del módulo scripts/circuit_breaker.py.

        English: Function _next_half_open_at defined in scripts/circuit_breaker.py.
        """
        if not self._opened_at:
            return None
        wait_seconds = min(self.half_open_after_seconds, self.open_timeout_seconds)
        return self._opened_at + timedelta(seconds=wait_seconds)

    def seconds_until_half_open(self, now: datetime | None = None) -> float:
        """Español: Función seconds_until_half_open del módulo scripts/circuit_breaker.py.

        English: Function seconds_until_half_open defined in scripts/circuit_breaker.py.
        """
        now = now or self._now()
        target = self._next_half_open_at()
        if not target:
            return 0.0
        return max(0.0, (target - now).total_seconds())

    def allow_request(self, now: datetime | None = None) -> bool:
        """Español: Función allow_request del módulo scripts/circuit_breaker.py.

        English: Function allow_request defined in scripts/circuit_breaker.py.
        """
        now = now or self._now()
        if self.state != "OPEN":
            return True
        next_half_open = self._next_half_open_at()
        if next_half_open and now >= next_half_open:
            self._half_open(now)
            return True
        return False

    def record_failure(self, now: datetime | None = None) -> bool:
        """Español: Función record_failure del módulo scripts/circuit_breaker.py.

        English: Function record_failure defined in scripts/circuit_breaker.py.
        """
        now = now or self._now()
        if self.state == "HALF_OPEN":
            return self._open(now)
        self._failures.append(now)
        self._trim_failures(now)
        if self.state == "CLOSED" and len(self._failures) >= self.failure_threshold:
            return self._open(now)
        return False

    def record_success(self, now: datetime | None = None) -> bool:
        """Español: Función record_success del módulo scripts/circuit_breaker.py.

        English: Function record_success defined in scripts/circuit_breaker.py.
        """
        if self.state != "HALF_OPEN":
            return False
        self._half_open_successes += 1
        if self._half_open_successes >= self.success_threshold:
            self._close()
            return True
        return False

    def should_log_open_wait(self, now: datetime | None = None) -> bool:
        """Español: Función should_log_open_wait del módulo scripts/circuit_breaker.py.

        English: Function should_log_open_wait defined in scripts/circuit_breaker.py.
        """
        if self.state != "OPEN":
            return False
        now = now or self._now()
        if not self._next_log_at or now >= self._next_log_at:
            self._next_log_at = now + timedelta(seconds=self.open_log_interval_seconds)
            return True
        return False

    def consume_open_alert(self) -> bool:
        """Español: Función consume_open_alert del módulo scripts/circuit_breaker.py.

        English: Function consume_open_alert defined in scripts/circuit_breaker.py.
        """
        if self.state != "OPEN" or self._alert_sent:
            return False
        self._alert_sent = True
        return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize breaker state for durable persistence.

        Captures both static config and dynamic runtime state so the breaker
        can be reconstructed exactly after a process restart, preventing the
        'attacker forces restart -> circuit re-opens -> DoS loop' scenario.
        """
        return {
            "version": 1,
            "config": {
                "failure_threshold": self.failure_threshold,
                "failure_window_seconds": self.failure_window_seconds,
                "open_timeout_seconds": self.open_timeout_seconds,
                "half_open_after_seconds": self.half_open_after_seconds,
                "success_threshold": self.success_threshold,
                "open_log_interval_seconds": self.open_log_interval_seconds,
            },
            "state": self.state,
            "failures": [ts.isoformat() for ts in self._failures],
            "opened_at": self._opened_at.isoformat() if self._opened_at else None,
            "next_log_at": self._next_log_at.isoformat() if self._next_log_at else None,
            "half_open_successes": self._half_open_successes,
            "alert_sent": self._alert_sent,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CircuitBreaker":
        """Reconstruct breaker from a previously saved state dict."""
        config = payload.get("config", {}) or {}
        breaker = cls(
            failure_threshold=int(config.get("failure_threshold", 5)),
            failure_window_seconds=int(config.get("failure_window_seconds", 600)),
            open_timeout_seconds=int(config.get("open_timeout_seconds", 1800)),
            half_open_after_seconds=int(config.get("half_open_after_seconds", 600)),
            success_threshold=int(config.get("success_threshold", 2)),
            open_log_interval_seconds=int(config.get("open_log_interval_seconds", 300)),
        )
        breaker.state = payload.get("state", "CLOSED")
        breaker._failures = deque(ts for ts in (_parse_iso(v) for v in payload.get("failures", [])) if ts is not None)
        breaker._opened_at = _parse_iso(payload.get("opened_at"))
        breaker._next_log_at = _parse_iso(payload.get("next_log_at"))
        breaker._half_open_successes = int(payload.get("half_open_successes", 0))
        breaker._alert_sent = bool(payload.get("alert_sent", False))
        return breaker

    def save_state(self, path: Path) -> None:
        """Atomically persist MAC-protected breaker state to disk.

        The state dict is wrapped in an envelope carrying an HMAC-SHA256
        over its canonical serialization. Atomic via tempfile + fsync +
        rename so no partial write is visible or persisted on crash.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        state_dict = self.to_dict()
        canonical = json.dumps(state_dict, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        key = _resolve_state_hmac_key(path)
        envelope = {
            "mac_algorithm": "HMAC-SHA256",
            "mac": _compute_state_mac(canonical, key),
            "state": state_dict,
        }
        payload = json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as tmp_file:
                tmp_file.write(payload)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            shutil.move(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    @classmethod
    def load_state(cls, path: Path) -> Optional["CircuitBreaker"]:
        """Load MAC-verified breaker state.

        Security behavior:
          - Missing file -> None (caller builds a fresh breaker).
          - Unreadable / not JSON -> None (tolerant: corrupt file must
            not brick pipeline startup).
          - Valid MAC -> trusted state restored.
          - INVALID MAC (active tampering: someone edited the file to
            reset the breaker to CLOSED and re-open the DoS window) ->
            CRITICAL alert + breaker forced OPEN so the tamper attempt
            fails closed instead of granting the attacker their goal.
          - Legacy un-enveloped state -> accepted once with a warning
            (one-time migration; next save_state writes a MAC).
        """
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _LOGGER.warning("circuit_breaker_state_unreadable path=%s error=%s", path, exc)
            return None
        if not isinstance(raw, dict):
            _LOGGER.warning("circuit_breaker_state_invalid path=%s reason=not_dict", path)
            return None

        # Legacy format (no envelope): accept once, will be re-MAC'd on save.
        if "mac" not in raw or "state" not in raw:
            _LOGGER.warning(
                "circuit_breaker_state_legacy_unauthenticated path=%s "
                "(accepting once; will be MAC-protected on next save)",
                path,
            )
            return cls.from_dict(raw)

        state_dict = raw.get("state")
        if not isinstance(state_dict, dict):
            _LOGGER.warning("circuit_breaker_state_invalid path=%s reason=envelope_state", path)
            return None
        canonical = json.dumps(state_dict, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        key = _resolve_state_hmac_key(path)
        expected = _compute_state_mac(canonical, key)
        if not hmac.compare_digest(expected, str(raw.get("mac", ""))):
            _LOGGER.critical(
                "circuit_breaker_state_TAMPERED path=%s — MAC mismatch. "
                "Forcing breaker OPEN (fail-closed) to deny the tamper attempt.",
                path,
            )
            breaker = cls.from_dict(state_dict)
            breaker._open(breaker._now())
            return breaker
        return cls.from_dict(state_dict)
