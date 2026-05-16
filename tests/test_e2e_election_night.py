"""
Tests E2E — Escenarios de Noche Electoral
End-to-End Tests — Election Night Scenarios

Simula tres ataques realistas y verifica la respuesta defensiva integral:

1. Noche electoral con anomalía: CNE publica datos con Benford anómalo +
   Merkle divergente → kill switch freeze + auto-recovery.
2. Testigo offline: testigo B cae → consenso degrada limpiamente sin
   falsa alarma (2/3 sigue siendo válido).
3. MITM en un testigo: datos falsos solo a testigo C → federación
   detecta divergencia criptográfica.
"""

import time
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from centinel.core.anomaly_detector import AnomalyDetector
from centinel.core.kill_switch import KillSwitch, LOCK_FILE
from centinel.federation.multi_witness import FederationCoordinator


def _benford_compliant_votes(n: int) -> list[dict]:
    """Genera snapshots con votos que SIGUEN la ley de Benford.

    Crecimiento exponencial natural → primer dígito ~log10(1+1/d).
    """
    snapshots = []
    value = 137
    for i in range(n):
        value = int(value * 1.07) + (i % 7)
        snapshots.append(
            {
                "index": i,
                "timestamp": 1715875800 + i * 60,
                "total_votes": value,
                "registered_voters": value * 3,
                "valid_votes": value,
                "null_votes": i % 5,
                "blank_votes": i % 3,
            }
        )
    return snapshots


def _benford_violating_votes(n: int) -> list[dict]:
    """Genera snapshots manipulados que VIOLAN la ley de Benford.

    Todos los totales empiezan con dígito 9 (manipulación grosera:
    "rellenar" actas con números inflados sospechosamente uniformes).
    """
    snapshots = []
    for i in range(n):
        # Fuerza primer dígito = 9 siempre (anti-Benford severo)
        total = 900000 + (i * 137) % 99999
        snapshots.append(
            {
                "index": i,
                "timestamp": 1715875800 + i * 60,
                "total_votes": total,
                "registered_voters": total + 1000,
                "valid_votes": total,
                "null_votes": i % 5,
                "blank_votes": i % 3,
            }
        )
    return snapshots


class TestE2EElectionNightAnomaly:
    """Escenario 1: Noche electoral con anomalía estadística."""

    def test_benford_detector_flags_manipulated_data(self):
        """Datos manipulados (todos empiezan con 9) disparan Benford."""
        clean = _benford_compliant_votes(150)
        manipulated = _benford_violating_votes(150)

        detector = AnomalyDetector(min_snapshots=100)

        clean_report = detector.analyze(clean)
        bad_report = detector.analyze(manipulated)

        # Datos limpios: pocas o ninguna anomalía Benford
        clean_benford = [a for a in clean_report.anomalies if a.anomaly_type == "benford"]
        # Datos manipulados: Benford DEBE detectar la anomalía
        bad_benford = [a for a in bad_report.anomalies if a.anomaly_type == "benford"]

        assert bad_report.threshold_applied is True
        assert len(bad_benford) > len(clean_benford)
        assert len(bad_benford) >= 1

    def test_anomaly_detector_respects_min_snapshots(self):
        """Con <100 snapshots NO se alarma (anti-falsos-positivos)."""
        manipulated = _benford_violating_votes(50)
        detector = AnomalyDetector(min_snapshots=100)
        report = detector.analyze(manipulated)

        assert report.threshold_applied is False
        assert report.anomalies == []

    @pytest.mark.asyncio
    async def test_kill_switch_freezes_on_benford_plus_merkle(self):
        """Ataque coordinado: Merkle diverge + Benford severo + consenso
        roto (manipulación real hace divergir a testigos honestos) →
        score ≥75 → freeze.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            ks = KillSwitch(storage_path=tmpdir)

            # Escenario realista: datos manipulados causan TANTO Merkle
            # divergence (+40) y Benford (+25) COMO consenso roto (+35),
            # porque los testigos honestos divergen del comprometido.
            score = await ks.evaluate_threat(
                merkle_divergence=True,  # +40
                benford_severity=45.2,  # +25 (χ² crítico)
                connectivity_lost=False,
                federation_consensus_broken=True,  # +35
            )

            assert score >= 75, f"Score {score} debería activar kill switch"

            # Limpia lock file previo si existe
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()

            frozen = await ks.freeze(reason="E2E: Benford+Merkle anomaly")
            assert frozen is True
            assert LOCK_FILE.exists()
            assert ks.recovery_state.is_frozen is True

            # Cleanup
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()

    @pytest.mark.asyncio
    async def test_kill_switch_auto_recovers_after_freeze(self):
        """Tras freeze, auto_recover se ejecuta con backoff y se recupera."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ks = KillSwitch(storage_path=tmpdir)

            if LOCK_FILE.exists():
                LOCK_FILE.unlink()

            await ks.freeze(reason="E2E recovery test")
            assert ks.recovery_state.is_frozen is True

            # Mock: backoff sleep instantáneo + integridad local OK
            with patch("asyncio.sleep", new=MagicMock(return_value=None)), patch.object(
                ks,
                "_check_local_integrity_and_restore_from_mirrors",
                return_value=True,
            ):

                async def _instant_sleep(_):
                    return None

                with patch("centinel.core.kill_switch.asyncio.sleep", _instant_sleep):
                    recovered = await ks.auto_recover()

            assert recovered is True
            assert ks.recovery_state.is_frozen is False

            if LOCK_FILE.exists():
                LOCK_FILE.unlink()

    @pytest.mark.asyncio
    async def test_endpoint_change_does_NOT_trigger_killswitch(self):
        """CRÍTICO: cambio de endpoint/schema NO activa kill switch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ks = KillSwitch(storage_path=tmpdir)

            # Solo "cambió el endpoint" — ningún factor de integridad real
            score = await ks.evaluate_threat(
                merkle_divergence=False,
                benford_severity=0.0,
                connectivity_lost=False,
                federation_consensus_broken=False,
            )

            assert score == 0.0, "Cambio de API NO debe activar kill switch"
            assert score < 75


class TestE2EWitnessOffline:
    """Escenario 2: Testigo offline durante la noche electoral."""

    @patch("httpx.Client.get")
    def test_consensus_holds_with_one_witness_offline(self, mock_get):
        """3 testigos, B offline → 2/3 acuerdan → consenso OK (sin alarma)."""
        good_merkle = "a" * 64

        def side_effect(url, *args, **kwargs):
            resp = MagicMock()
            if "witness2" in url:
                # Testigo B offline → simula timeout
                import httpx

                raise httpx.TimeoutException("Witness B offline")
            resp.status_code = 200
            resp.json.return_value = {
                "witness_id": url.split("//")[1].split(".")[0],
                "merkle_root": good_merkle,
                "checkpoint_hash": "b" * 64,
                "chain_length": 100,
                "timestamp": time.time(),
            }
            return resp

        mock_get.side_effect = side_effect

        fed = FederationCoordinator(
            witness_urls=[
                "https://witness1.example.com",
                "https://witness2.example.com",  # offline
                "https://witness3.example.com",
            ]
        )
        report = fed.check_consensus()

        # 2 testigos responden, ambos de acuerdo → consenso alcanzado
        assert len(fed.attestations) == 2
        assert report.consensus_reached is True
        assert report.consensus_count == 2
        # NO hay divergencias (no es falsa alarma)
        assert len(report.divergences) == 0

    @patch("httpx.Client.get")
    def test_no_consensus_when_two_witnesses_offline(self, mock_get):
        """3 testigos, 2 offline → solo 1 responde → sin consenso (degradado)."""

        def side_effect(url, *args, **kwargs):
            import httpx

            if "witness1" in url:
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {
                    "witness_id": "W1",
                    "merkle_root": "a" * 64,
                    "checkpoint_hash": "b" * 64,
                    "chain_length": 100,
                    "timestamp": time.time(),
                }
                return resp
            raise httpx.TimeoutException("offline")

        mock_get.side_effect = side_effect

        fed = FederationCoordinator(
            witness_urls=[
                "https://witness1.example.com",
                "https://witness2.example.com",
                "https://witness3.example.com",
            ]
        )
        report = fed.check_consensus()

        # Solo 1 responde → no se puede formar consenso (≥2 requerido)
        assert len(fed.attestations) == 1
        assert report.consensus_reached is False


class TestE2EMitmSingleWitness:
    """Escenario 3: MITM inyecta datos falsos a un solo testigo."""

    @patch("httpx.Client.get")
    def test_mitm_on_one_witness_detected_as_divergence(self, mock_get):
        """C recibe datos falsos (MITM) → divergencia criptográfica detectada."""
        honest_merkle = "a" * 64
        forged_merkle = "f" * 64  # MITM inyectó datos distintos a C

        def side_effect(url, *args, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "witness3" in url:
                merkle = forged_merkle  # Testigo C comprometido por MITM
            else:
                merkle = honest_merkle  # A y B honestos
            resp.json.return_value = {
                "witness_id": url.split("//")[1].split(".")[0],
                "merkle_root": merkle,
                "checkpoint_hash": "b" * 64,
                "chain_length": 100,
                "timestamp": time.time(),
            }
            return resp

        mock_get.side_effect = side_effect

        fed = FederationCoordinator(
            witness_urls=[
                "https://witness1.example.com",
                "https://witness2.example.com",
                "https://witness3.example.com",  # MITM target
            ]
        )
        report = fed.check_consensus()

        # 3 testigos responden, pero C diverge
        assert len(fed.attestations) == 3
        # Byzantine: 2/3 (A,B) forman consenso sobre merkle honesto
        assert report.consensus_reached is True
        assert report.consensus_count == 2
        assert report.consensus_merkle == honest_merkle
        # La divergencia de C es detectada y registrada (evidencia forense)
        assert len(report.divergences) >= 1
        diverging = report.divergences[0]
        assert diverging.matches is False

    @patch("httpx.Client.get")
    def test_mitm_majority_compromise_breaks_consensus(self, mock_get):
        """Si MITM compromete 2/3 → consenso es 'falso' (riesgo residual conocido)."""
        forged = "f" * 64
        honest = "a" * 64

        def side_effect(url, *args, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            # A y B comprometidos (mayoría), solo C honesto
            merkle = honest if "witness3" in url else forged
            resp.json.return_value = {
                "witness_id": url.split("//")[1].split(".")[0],
                "merkle_root": merkle,
                "checkpoint_hash": "b" * 64,
                "chain_length": 100,
                "timestamp": time.time(),
            }
            return resp

        mock_get.side_effect = side_effect

        fed = FederationCoordinator(
            witness_urls=[
                "https://witness1.example.com",
                "https://witness2.example.com",
                "https://witness3.example.com",
            ]
        )
        report = fed.check_consensus()

        # Documenta el riesgo residual: si >50% comprometidos, el
        # "consenso" apunta al merkle falso. Detectable solo vía T3
        # (timestamp Bitcoin) o auditoría externa.
        assert report.consensus_merkle == forged
        assert len(report.divergences) >= 1  # C honesto diverge, queda en log
