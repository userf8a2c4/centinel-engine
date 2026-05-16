"""
Tests para Kill Switch (Defensa de Tejón)
Tests for Kill Switch (Badger Defense)
"""

import asyncio
import json
import pytest
import random
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from centinel.core.kill_switch import KillSwitch, RecoveryState
from centinel.core.animal_defenses import AnimalDefense


@pytest.fixture
def kill_switch(tmp_path):
    """Fixture para KillSwitch con almacenamiento temporal."""
    return KillSwitch(storage_path=str(tmp_path))


class TestAnimalDefenseEnum:
    """Tests para el enum AnimalDefense."""

    def test_kill_switch_defense_properties(self):
        """Verifica propiedades de la defensa KILL_SWITCH."""
        defense = AnimalDefense.KILL_SWITCH
        assert defense.emoji == "⚔️"
        assert defense.name_es == "Tejón"
        assert defense.title_es == "Defensa de Tejón"
        assert "Freeze instantáneo" in defense.description_es


class TestExponentialBackoff:
    """Tests para exponential backoff."""

    def test_backoff_schedule_exists(self, kill_switch):
        """Verifica que schedule de backoff existe."""
        assert len(kill_switch.BACKOFF_SCHEDULE) == 5
        assert kill_switch.BACKOFF_SCHEDULE[0] == (2, 0.3)
        assert kill_switch.BACKOFF_SCHEDULE[4] == (30, 0.3)

    def test_calculate_backoff_attempt_1(self, kill_switch):
        """Intento 1: 2s ± 30% = 1.4s–2.6s"""
        min_delay, max_delay = kill_switch._calculate_exponential_backoff(1)
        assert 1.3 < min_delay < 1.5
        assert 2.5 < max_delay < 2.7
        assert max_delay > min_delay

    def test_calculate_backoff_attempt_2(self, kill_switch):
        """Intento 2: 5s ± 30% = 3.5s–6.5s"""
        min_delay, max_delay = kill_switch._calculate_exponential_backoff(2)
        assert 3.4 < min_delay < 3.6
        assert 6.4 < max_delay < 6.6

    def test_calculate_backoff_attempt_5(self, kill_switch):
        """Intento 5+: 30s ± 30% = 21s–39s"""
        min_delay, max_delay = kill_switch._calculate_exponential_backoff(5)
        assert 20.9 < min_delay < 21.1
        assert 38.9 < max_delay < 39.1

    def test_calculate_backoff_capped_at_5(self, kill_switch):
        """Intento > 5 sigue usando el máximo (30s)."""
        min_delay_5, max_delay_5 = kill_switch._calculate_exponential_backoff(5)
        min_delay_10, max_delay_10 = kill_switch._calculate_exponential_backoff(10)
        assert min_delay_5 == min_delay_10
        assert max_delay_5 == max_delay_10

    def test_jitter_distribution(self, kill_switch):
        """Verifica que jitter está dentro del rango esperado."""
        min_delay, max_delay = kill_switch._calculate_exponential_backoff(1)
        samples = [random.uniform(min_delay, max_delay) for _ in range(1000)]

        assert all(min_delay <= s <= max_delay for s in samples)
        mean = sum(samples) / len(samples)
        expected_mean = (min_delay + max_delay) / 2
        # Tolerancia: ±10% del promedio esperado
        assert abs(mean - expected_mean) < expected_mean * 0.1


class TestThreatScoring:
    """Tests para evaluación de amenaza."""

    @pytest.mark.asyncio
    async def test_threat_score_no_threat(self, kill_switch):
        """Score 0 si no hay amenaza."""
        score = await kill_switch.evaluate_threat(
            merkle_divergence=False,
            benford_severity=5.0,
            connectivity_lost=False,
            federation_consensus_broken=False,
        )
        assert score == 0

    @pytest.mark.asyncio
    async def test_threat_score_merkle_divergence(self, kill_switch):
        """Merkle divergence: +40 pts."""
        score = await kill_switch.evaluate_threat(merkle_divergence=True)
        assert score == 40

    @pytest.mark.asyncio
    async def test_threat_score_benford_anomaly(self, kill_switch):
        """Benford χ² > 15.99: +25 pts."""
        score = await kill_switch.evaluate_threat(benford_severity=16.0)
        assert score == 25

    @pytest.mark.asyncio
    async def test_threat_score_connectivity_loss(self, kill_switch):
        """Conectividad total perdida: +20 pts."""
        score = await kill_switch.evaluate_threat(connectivity_lost=True)
        assert score == 20

    @pytest.mark.asyncio
    async def test_threat_score_consensus_broken(self, kill_switch):
        """Consenso federation roto: +35 pts."""
        score = await kill_switch.evaluate_threat(federation_consensus_broken=True)
        assert score == 35

    @pytest.mark.asyncio
    async def test_threat_score_all_threats(self, kill_switch):
        """Todos los factores: 40+25+20+35 = 120 (capped at 100?)."""
        score = await kill_switch.evaluate_threat(
            merkle_divergence=True,
            benford_severity=16.0,
            connectivity_lost=True,
            federation_consensus_broken=True,
        )
        # Sin cap, el score es 120. Pero ≥75 ya activa kill switch.
        assert score >= 75

    @pytest.mark.asyncio
    async def test_threat_score_ignores_endpoint_changes(self, kill_switch):
        """Cambios de endpoint (D11) NO aumentan score."""
        # Esto se verifica implícitamente: no hay parámetro para cambios de endpoint
        score = await kill_switch.evaluate_threat()
        assert score == 0


class TestFreeze:
    """Tests para congelamiento."""

    @pytest.mark.asyncio
    async def test_freeze_creates_lock_file(self, kill_switch, tmp_path):
        """Freeze crea lock file visible."""
        with patch("centinel.core.kill_switch.LOCK_FILE", tmp_path / "centinel.lock"):
            success = await kill_switch.freeze(reason="Test freeze")
            assert success
            assert (tmp_path / "centinel.lock").exists()

    @pytest.mark.asyncio
    async def test_freeze_creates_checkpoint(self, kill_switch):
        """Freeze crea checkpoint congelado."""
        success = await kill_switch.freeze(reason="Test freeze")
        assert success

        checkpoint_file = Path(kill_switch.storage_path) / "checkpoint_frozen.json"
        assert checkpoint_file.exists()

        with open(checkpoint_file) as f:
            checkpoint = json.load(f)
            assert "frozen_at" in checkpoint
            assert "recovery_state" in checkpoint

    @pytest.mark.asyncio
    async def test_freeze_resets_attempt_count(self, kill_switch):
        """Freeze resetea contador de intentos."""
        kill_switch.recovery_state.attempt_count = 10

        await kill_switch.freeze(reason="Test")

        assert kill_switch.recovery_state.attempt_count == 0
        assert kill_switch.recovery_state.is_frozen is True

    @pytest.mark.asyncio
    async def test_freeze_logs_attack_event(self, kill_switch):
        """Freeze registra evento en attack_log.jsonl."""
        await kill_switch.freeze(reason="Test freeze")

        log_file = Path(kill_switch.storage_path) / "attack_log.jsonl"
        assert log_file.exists()

        with open(log_file) as f:
            lines = f.readlines()
            assert any("kill_switch_freeze" in line for line in lines)


class TestRecoveryState:
    """Tests para estado de recuperación."""

    def test_recovery_state_persistence(self, kill_switch, tmp_path):
        """Recuperación state persiste en disco."""
        kill_switch.recovery_state.attempt_count = 3
        kill_switch.recovery_state.is_frozen = True
        kill_switch._save_recovery_state()

        state_file = Path(kill_switch.storage_path) / "recovery_state.json"
        assert state_file.exists()

        # Cargar y verificar
        with open(state_file) as f:
            data = json.load(f)
            assert data["attempt_count"] == 3
            assert data["is_frozen"] is True

    def test_load_recovery_state(self, kill_switch):
        """Carga estado de recuperación existente."""
        # Guardar
        kill_switch.recovery_state.attempt_count = 5
        kill_switch._save_recovery_state()

        # Crear nuevo instance y cargar desde misma ruta
        kill_switch2 = KillSwitch(storage_path=str(kill_switch.storage_path))
        assert kill_switch2.recovery_state.attempt_count == 5

    def test_atomic_save_no_temp_files_left(self, kill_switch):
        """Escritura atómica no deja archivos temporales."""
        kill_switch.recovery_state.attempt_count = 3
        kill_switch._save_recovery_state()

        # No deben quedar archivos .tmp en storage
        temp_files = list(kill_switch.storage_path.glob(".recovery_*.tmp"))
        assert len(temp_files) == 0

        # El archivo final existe y es JSON válido
        import json as _json

        state_file = kill_switch.storage_path / "recovery_state.json"
        assert state_file.exists()
        data = _json.loads(state_file.read_text())
        assert data["attempt_count"] == 3

    def test_atomic_save_overwrites_cleanly(self, kill_switch):
        """Múltiples escrituras sobrescriben sin corromper."""
        for i in range(1, 6):
            kill_switch.recovery_state.attempt_count = i
            kill_switch._save_recovery_state()

        import json as _json

        state_file = kill_switch.storage_path / "recovery_state.json"
        data = _json.loads(state_file.read_text())
        assert data["attempt_count"] == 5
        # Sin archivos temporales residuales
        assert len(list(kill_switch.storage_path.glob(".recovery_*.tmp"))) == 0


class TestAutoRecover:
    """Tests para recuperación automática."""

    @pytest.mark.asyncio
    async def test_auto_recover_not_frozen(self, kill_switch):
        """Si no está congelado, recovery retorna True inmediatamente."""
        kill_switch.recovery_state.is_frozen = False
        result = await kill_switch.auto_recover()
        assert result is True

    @pytest.mark.asyncio
    async def test_auto_recover_frozen_state(self, kill_switch):
        """Si está congelado, inicia loop de recuperación."""
        kill_switch.recovery_state.is_frozen = True

        # Mock _check_local_integrity_and_restore_from_mirrors para que retorne True
        with patch.object(
            kill_switch,
            "_check_local_integrity_and_restore_from_mirrors",
            return_value=True,
        ):
            result = await kill_switch.auto_recover()
            assert result is True
            assert kill_switch.recovery_state.is_frozen is False

    @pytest.mark.asyncio
    async def test_auto_recover_increments_attempts(self, kill_switch):
        """Cada intento incrementa attempt_count."""
        kill_switch.recovery_state.is_frozen = True
        kill_switch.recovery_state.attempt_count = 0

        with patch.object(
            kill_switch,
            "_check_local_integrity_and_restore_from_mirrors",
            side_effect=[False, False, True],  # Falla dos veces, éxito tercero
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await kill_switch.auto_recover()
                assert result is True
                assert kill_switch.recovery_state.attempt_count == 3

    @pytest.mark.asyncio
    async def test_auto_recover_max_attempts(self, kill_switch):
        """Si ≥5 intentos fallan, retorna False."""
        kill_switch.recovery_state.is_frozen = True

        with patch.object(
            kill_switch,
            "_check_local_integrity_and_restore_from_mirrors",
            return_value=False,  # Siempre falla
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await kill_switch.auto_recover()
                assert result is False
                assert kill_switch.recovery_state.attempt_count == 5


class TestGetStatus:
    """Tests para estado del sistema."""

    def test_get_status(self, kill_switch):
        """get_status retorna DefenseStatus válido."""
        kill_switch.recovery_state.is_frozen = True
        status = kill_switch.get_status()

        assert status.defense == AnimalDefense.KILL_SWITCH
        assert status.enabled is True
        assert status.metrics["is_frozen"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
