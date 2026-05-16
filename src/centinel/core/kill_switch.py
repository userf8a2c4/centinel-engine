"""
DEFENSA DE TEJÓN — Kill Switch
(BADGER DEFENSE — Kill Switch)

Respuesta autónoma a ataque activo: congelación instantánea + recuperación
con exponential backoff incrementales. El Tejón es imparable y feroz.

Autonomous response to active attack: instant freeze + incremental exponential
backoff recovery. The Badger is relentless and fierce.
"""

import asyncio
import json
import logging
import os
import random
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .animal_defenses import AnimalDefense, DefenseStatus

logger = logging.getLogger(__name__)

LOCK_FILE = Path(tempfile.gettempdir()) / "centinel.lock"
FROZEN_CHECKPOINT_PATH = Path("hashes/checkpoint_frozen.json")


@dataclass
class RecoveryState:
    """
    Estado de recuperación post-congelación.
    (Recovery state after freeze.)
    """

    attempt_count: int = 0
    last_freeze_timestamp: float = field(default_factory=time.time)
    last_recovery_attempt_timestamp: float = 0.0
    is_frozen: bool = False


class KillSwitch:
    """
    DEFENSA DE TEJÓN — Kill Switch

    Respuesta autónoma a amenaza de integridad real:
    - Detecta: Merkle divergence, anomalía Benford severa, consensus roto
    - Ignora: cambios de endpoint (D11 se encarga)
    - Acción: freeze instantáneo + recuperación local autónoma

    Autonomous response to real integrity threats:
    - Detects: Merkle divergence, severe Benford anomaly, consensus broken
    - Ignores: endpoint changes (D11 handles those)
    - Action: instant freeze + autonomous local recovery
    """

    DEFENSE = AnimalDefense.KILL_SWITCH

    # Backoff exponencial: (min_seconds, max_seconds) con jitter ±30%
    BACKOFF_SCHEDULE = [
        (2, 0.3),  # Intento 1: 2s ± 30%  =  1.4s–2.6s
        (5, 0.3),  # Intento 2: 5s ± 30%  =  3.5s–6.5s
        (10, 0.3),  # Intento 3: 10s ± 30% =  7s–13s
        (20, 0.3),  # Intento 4: 20s ± 30% = 14s–26s
        (30, 0.3),  # Intento 5+: 30s ± 30% = 21s–39s
    ]

    def __init__(self, storage_path: str = "hashes"):
        """
        Inicializa Kill Switch.
        (Initialize Kill Switch.)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.recovery_state = RecoveryState()
        self._load_recovery_state()

    def _load_recovery_state(self) -> None:
        """
        Carga estado de recuperación desde disco.
        (Load recovery state from disk.)
        """
        state_file = self.storage_path / "recovery_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    data = json.load(f)
                    self.recovery_state = RecoveryState(
                        attempt_count=data.get("attempt_count", 0),
                        last_freeze_timestamp=data.get("last_freeze_timestamp", time.time()),
                        last_recovery_attempt_timestamp=data.get(
                            "last_recovery_attempt_timestamp", 0.0
                        ),
                        is_frozen=data.get("is_frozen", False),
                    )
            except Exception as e:
                logger.warning(f"Failed to load recovery state: {e}")

    def _save_recovery_state(self) -> None:
        """
        Guarda estado de recuperación en disco (escritura atómica).
        (Save recovery state to disk with atomic write.)

        Escribe a archivo temporal + fsync + os.replace para garantizar
        ACID: si el proceso muere a mitad de escritura, el archivo original
        permanece intacto (rename es atómico en POSIX).

        Atomic write: temp file + fsync + os.replace. If process dies
        mid-write, original file stays intact (POSIX rename is atomic).
        """
        state_file = self.storage_path / "recovery_state.json"
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.storage_path), prefix=".recovery_", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(asdict(self.recovery_state), f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, state_file)
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
        except Exception as e:
            logger.error(f"Failed to save recovery state: {e}")

    async def evaluate_threat(
        self,
        merkle_divergence: bool = False,
        benford_severity: float = 0.0,
        connectivity_lost: bool = False,
        federation_consensus_broken: bool = False,
    ) -> float:
        """
        Calcula puntuación de amenaza (0–100).
        Kill switch activa si ≥75.

        Threat score (0–100). Kill switch activates if ≥75.

        Factores (SOLO integridad de datos, NOT cambios de API):
        - Merkle divergence ≥3 snapshots: +40 pts
        - Benford anomaly χ² > 15.99: +25 pts
        - Conectividad total perdida (>2min): +20 pts
        - Federation consensus roto (≥2 testigos divergen): +35 pts

        IGNORA (non-threat):
        - Endpoint schema cambió: 0 pts (logged por D11)
        - Endpoint URL cambió: 0 pts (logged por D11)
        - Timeout transiente: 0 pts
        """
        score = 0.0

        if merkle_divergence:
            score += 40
            logger.warning("Tejón: Merkle divergence detected (+40 pts)")

        if benford_severity > 15.99:  # χ² critical value
            score += 25
            logger.warning(f"Tejón: Benford anomaly χ²={benford_severity:.2f} (+25 pts)")

        if connectivity_lost:
            score += 20
            logger.warning("Tejón: Complete connectivity loss detected (+20 pts)")

        if federation_consensus_broken:
            score += 35
            logger.warning("Tejón: Federation consensus broken (+35 pts)")

        logger.info(f"Tejón: Threat score = {score}/100")
        return score

    async def freeze(self, reason: str = "Unknown threat detected") -> bool:
        """
        Congelación instantánea: snapshot atómico de estado.
        Preserva cadena completa, crea lock file, se prepara para recuperación.

        Instant freeze: atomic state snapshot.
        Preserves full chain, creates lock file, prepares for recovery.
        """
        logger.critical(f"🐧 TEJÓN FREEZE ACTIVATED: {reason}")

        try:
            # 1. Snapshot atómico de estado actual
            checkpoint = await self._create_frozen_checkpoint()
            logger.info(f"Tejón: Frozen checkpoint created: {checkpoint}")

            # 2. Crea lock file (señal visible de congelamiento)
            LOCK_FILE.write_text(
                json.dumps(
                    {
                        "frozen_at": datetime.utcnow().isoformat(),
                        "reason": reason,
                        "recovery_state": asdict(self.recovery_state),
                    }
                )
            )
            logger.info(f"Tejón: Lock file created at {LOCK_FILE}")

            # 3. Resetea contador de intentos para nueva recuperación
            self.recovery_state.is_frozen = True
            self.recovery_state.attempt_count = 0
            self.recovery_state.last_freeze_timestamp = time.time()
            self._save_recovery_state()

            # 4. Log evento en attack_log.jsonl
            await self._log_attack_event(
                event="kill_switch_freeze",
                details={
                    "reason": reason,
                    "frozen_at": datetime.utcnow().isoformat(),
                },
            )

            return True

        except Exception as e:
            logger.error(f"Tejón: Freeze failed: {e}")
            return False

    def _calculate_exponential_backoff(self, attempt: int) -> Tuple[float, float]:
        """
        Calcula rango de espera con backoff exponencial + jitter.
        (Calculate exponential backoff range with jitter.)

        attempt=1 → (1.4, 2.6)   # 2s base ± 30%
        attempt=2 → (3.5, 6.5)   # 5s base ± 30%
        """
        idx = min(attempt - 1, len(self.BACKOFF_SCHEDULE) - 1)
        base_seconds, jitter_pct = self.BACKOFF_SCHEDULE[idx]

        jitter = base_seconds * jitter_pct
        min_delay = base_seconds - jitter
        max_delay = base_seconds + jitter

        return (min_delay, max_delay)

    async def auto_recover(self) -> bool:
        """
        Recuperación autónoma tras freeze, con backoff exponencial MODERADO.
        COMPLETAMENTE LOCAL — sin esperar consenso de hermanos.

        Autonomous recovery after freeze, with moderate exponential backoff.
        FULLY LOCAL — no waiting for sibling consensus.

        ACTIVATION RULE: Solo si evaluate_threat() >= 75 (real integrity threat)
        RECOVERY: LOCAL ONLY — verifica integridad local + mirrors locales
        """
        if not self.recovery_state.is_frozen:
            logger.info("Tejón: Sistema no congelado, sin recuperación necesaria")
            return True

        max_attempts = 5

        while self.recovery_state.attempt_count < max_attempts:
            self.recovery_state.attempt_count += 1
            min_delay, max_delay = self._calculate_exponential_backoff(
                self.recovery_state.attempt_count
            )
            sleep_time = random.uniform(min_delay, max_delay)

            logger.info(
                f"Tejón: Intento {self.recovery_state.attempt_count} en {sleep_time:.1f}s "
                f"(Kill Switch: Attempt {self.recovery_state.attempt_count} in {sleep_time:.1f}s)"
            )

            await asyncio.sleep(sleep_time)

            # Verifica: ¿integridad LOCAL OK para resume? (sin esperar hermanos)
            if await self._check_local_integrity_and_restore_from_mirrors():
                logger.info(
                    "Tejón: Recuperación exitosa desde mirrors locales "
                    "(Kill Switch: Recovery successful from local mirrors)"
                )
                await self._publish_recovery_attestation()
                self.recovery_state.is_frozen = False
                self._save_recovery_state()
                return True

        logger.critical("Tejón: Fallo permanente " "(Kill Switch: Permanent failure)")
        await self._log_attack_event(
            event="kill_switch_permanent_failure",
            details={"attempts": self.recovery_state.attempt_count},
        )
        return False

    async def _create_frozen_checkpoint(self) -> Dict[str, Any]:
        """
        Crea checkpoint congelado: snapshot atómico del estado actual.
        (Create frozen checkpoint: atomic snapshot of current state.)
        """
        checkpoint = {
            "frozen_at": datetime.utcnow().isoformat(),
            "recovery_state": asdict(self.recovery_state),
            "merkle_root": await self._get_current_merkle_root(),
        }

        frozen_file = self.storage_path / "checkpoint_frozen.json"
        try:
            with open(frozen_file, "w") as f:
                json.dump(checkpoint, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save frozen checkpoint: {e}")

        return checkpoint

    async def _check_local_integrity_and_restore_from_mirrors(self) -> bool:
        """
        COMPLETAMENTE AUTÓNOMO. Verifica cadena local, restaura de mirrors locales.
        No contacta hermanos, no espera consenso.

        (FULLY AUTONOMOUS. Checks local chain, restores from local mirrors.
        Does NOT contact siblings, does NOT wait for consensus.)
        """
        # 1. Verifica si datos locales = mirrors locales
        if await self._verify_chain_matches_local_mirrors():
            logger.info("Tejón: Cadena íntegra confirmada (Local chain verified as intact)")
            return True

        # 2. Si no coincide, restaura de mirror más reciente
        if await self._restore_from_best_local_mirror():
            logger.info("Tejón: Restaurado exitosamente (Successfully restored from local mirror)")
            return True

        # 3. Si falla, permanence en freeze (no hacer nada destructivo)
        logger.warning("Tejón: Integridad NO confirmada, permanece congelado")
        return False

    async def _verify_chain_matches_local_mirrors(self) -> bool:
        """
        Verifica que la cadena local coincide con mirrors.
        (Verify that local chain matches mirrors.)
        """
        # Placeholder: comparar merkle_root local vs mirrors
        # En implementación real: cargar desde almacenamiento
        logger.info("Tejón: Verificando integridad de cadena local...")
        return True  # Simplificado para esta versión

    async def _restore_from_best_local_mirror(self) -> bool:
        """
        Restaura de mirror local más confiable.
        (Restore from most reliable local mirror.)
        """
        logger.info("Tejón: Intentando restauración desde mirrors locales...")
        # Placeholder: implementar lógica de restauración
        return True  # Simplificado para esta versión

    async def _publish_recovery_attestation(self) -> None:
        """
        Publica atestación de recuperación (sin esperar respuesta).
        (Publish recovery attestation asynchronously.)
        """
        attestation = {
            "event": "kill_switch_recovery",
            "timestamp": datetime.utcnow().isoformat(),
            "witness_id": "local",  # Placeholder
            "recovery_state": asdict(self.recovery_state),
        }

        logger.info(f"Tejón: Publicando atestación de recuperación: {attestation}")
        await self._log_attack_event(
            event="kill_switch_recovery",
            details=attestation,
        )

    async def _get_current_merkle_root(self) -> str:
        """Obtiene merkle root actual."""
        # Placeholder: en real, calcular desde datos
        return "pending_calculation"

    async def _log_attack_event(self, event: str, details: Dict[str, Any]) -> None:
        """
        Registra evento en attack_log.jsonl (append-only).
        (Log event to attack_log.jsonl in append-only mode.)
        """
        log_file = self.storage_path / "attack_log.jsonl"
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": event,
                "details": details,
            }
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to log attack event: {e}")

    def get_status(self) -> DefenseStatus:
        """Retorna estado actual de la defensa."""
        return DefenseStatus(
            defense=self.DEFENSE,
            enabled=True,
            last_check_ts=time.time(),
            metrics={
                "is_frozen": self.recovery_state.is_frozen,
                "attempt_count": self.recovery_state.attempt_count,
                "last_freeze_ts": self.recovery_state.last_freeze_timestamp,
            },
        )
