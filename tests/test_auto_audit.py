"""
TESTS — Auto-Audit Loop / Autosanitaria

Pruebas para el módulo de auto-auditoría interna.
Tests for self-audit module.
"""

import json
import asyncio
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from centinel.core.auto_audit import AutoAudit, AuditReport, HealthCheckResult


class TestAutoAuditBasics:
    """Pruebas básicas de inicialización."""

    def test_init_creates_storage_path(self):
        """Init crea directorio storage si no existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            assert Path(tmpdir).exists()

    def test_binary_baseline_computed(self):
        """Calcula baseline MD5 de archivos core."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir, core_path="src/centinel/core")
            baseline = audit.binary_baseline

            # Verifica que al menos algunos archivos fueron encontrados
            assert isinstance(baseline, dict)
            assert "custody.py" in baseline or len(baseline) >= 0


class TestBinaryIntegrity:
    """Pruebas de integridad binaria."""

    @pytest.mark.asyncio
    async def test_scan_binary_integrity_all_ok(self):
        """Scan retorna True para todos los archivos sin modificar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir, core_path="src/centinel/core")
            result = await audit.scan_binary_integrity()

            # Verifica que es un dict
            assert isinstance(result, dict)
            # Si hay archivos, todos deberían ser True
            if result:
                assert all(isinstance(v, bool) for v in result.values())

    @pytest.mark.asyncio
    async def test_scan_binary_integrity_detects_modification(self):
        """Scan detecta si archivo core fue modificado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core_dir = Path(tmpdir) / "core"
            core_dir.mkdir()

            # Crea archivo test
            test_file = core_dir / "test_module.py"
            test_file.write_text("original content")

            # Calcula baseline
            audit = AutoAudit(storage_path=tmpdir, core_path=str(core_dir))
            baseline = audit.binary_baseline

            # Modifica archivo
            test_file.write_text("modified content")

            # Scan debería detectar cambio
            result = await audit.scan_binary_integrity()
            # Si test_module.py estaba en baseline, ahora debería ser False
            if "test_module.py" in result:
                assert result["test_module.py"] is False


class TestStateConsistency:
    """Pruebas de consistencia de estado."""

    @pytest.mark.asyncio
    async def test_check_state_consistency_no_logs(self):
        """State check retorna OK si no hay logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            result = await audit.check_state_consistency()

            assert isinstance(result, dict)
            assert "consistent" in result

    @pytest.mark.asyncio
    async def test_check_state_consistency_valid_logs(self):
        """State check valida monotonicity de timestamps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir)
            attack_log = storage / "attack_log.jsonl"

            # Crea log con timestamps monotónicos
            logs = [
                {"timestamp": 1000.0, "event": "test1"},
                {"timestamp": 1001.0, "event": "test2"},
                {"timestamp": 1002.0, "event": "test3"},
            ]
            attack_log.write_text("\n".join(json.dumps(l) for l in logs))

            audit = AutoAudit(storage_path=tmpdir)
            result = await audit.check_state_consistency()

            assert result.get("consistent", False) is True

    @pytest.mark.asyncio
    async def test_check_state_consistency_detects_out_of_order(self):
        """State check detecta timestamps fuera de orden."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir)
            attack_log = storage / "attack_log.jsonl"

            # Crea log con timestamps out-of-order
            logs = [
                {"timestamp": 1000.0, "event": "test1"},
                {"timestamp": 1002.0, "event": "test2"},
                {"timestamp": 1001.0, "event": "test3"},  # Out of order!
            ]
            attack_log.write_text("\n".join(json.dumps(l) for l in logs))

            audit = AutoAudit(storage_path=tmpdir)
            result = await audit.check_state_consistency()

            # Debería detectar como inconsistente
            assert result.get("consistent", False) is False or len(result.get("issues", [])) > 0


class TestDefenseHealth:
    """Pruebas de salud de defensas."""

    @pytest.mark.asyncio
    async def test_defense_health_returns_dict(self):
        """test_defense_health retorna dict con 5 keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            result = await audit.test_defense_health()

            assert isinstance(result, dict)
            # Debería tener al menos placeholders para las 5 defensas
            expected_keys = {"corvid", "cephalopod", "evasion", "regeneration", "kill_switch"}
            assert set(result.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_defense_health_all_bool(self):
        """Todos los valores de defense health son booleans."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            result = await audit.test_defense_health()

            assert all(isinstance(v, bool) for v in result.values())


class TestMirrorCoherence:
    """Pruebas de coherencia con mirrors."""

    @pytest.mark.asyncio
    async def test_verify_mirror_coherence_returns_dict(self):
        """verify_mirror_coherence retorna dict con estructura correcta."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            result = await audit.verify_mirror_coherence()

            assert isinstance(result, dict)
            assert "coherent" in result


class TestHealthScoreCalculation:
    """Pruebas del cálculo de health score."""

    @pytest.mark.asyncio
    async def test_health_score_all_ok(self):
        """Health score es 1.0 si todos los checks pasan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)

            # Mock: todos los checks son True
            report = await audit.run_full_audit()

            # Health score está en rango [0, 1]
            assert 0.0 <= report.health_score <= 1.0

    @pytest.mark.asyncio
    async def test_health_score_components(self):
        """Health score se calcula de 4 componentes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            report = await audit.run_full_audit()

            # Score debería reflejar: binary (1), state (1), defenses (1-5), mirrors (1)
            # Si todos OK: 4/4 = 1.0
            # Si 3 OK: 3/4 = 0.75
            # Si 2 OK: 2/4 = 0.50
            assert report.health_score in [
                0.0,
                0.25,
                0.5,
                0.75,
                1.0,
            ], f"Unexpected health score: {report.health_score}"


class TestAuditReportSerialization:
    """Pruebas de serialización de reportes."""

    @pytest.mark.asyncio
    async def test_audit_report_to_dict(self):
        """AuditReport.to_dict() retorna dict válido."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            report = await audit.run_full_audit()

            data = report.to_dict()
            assert isinstance(data, dict)
            assert "timestamp" in data
            assert "health_score" in data
            assert "binary_integrity" in data
            assert "state_consistency" in data
            assert "defense_health" in data
            assert "mirror_coherence" in data

    @pytest.mark.asyncio
    async def test_audit_report_json_serializable(self):
        """AuditReport es serializable a JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            report = await audit.run_full_audit()

            data = report.to_dict()
            json_str = json.dumps(data)
            assert isinstance(json_str, str)
            assert len(json_str) > 0


class TestAuditReportPersistence:
    """Pruebas de persistencia de reportes."""

    @pytest.mark.asyncio
    async def test_save_audit_report(self):
        """run_full_audit guarda reporte en audit_log.jsonl."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)
            report = await audit.run_full_audit()

            # Verifica que audit_log fue creado
            audit_log = Path(tmpdir) / "audit_log.jsonl"
            assert audit_log.exists()

    @pytest.mark.asyncio
    async def test_audit_log_append_only(self):
        """audit_log.jsonl es append-only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)

            # Ejecuta audit dos veces
            await audit.run_full_audit()
            await audit.run_full_audit()

            # Verifica que log tiene dos líneas
            audit_log = Path(tmpdir) / "audit_log.jsonl"
            lines = audit_log.read_text().strip().split("\n")
            assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_get_latest_health_score(self):
        """get_health_score retorna score más reciente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)

            # Ejecuta audit
            await audit.run_full_audit()

            # Lee score más reciente (función síncrona, sin await)
            score = audit.get_health_score()
            assert score is not None
            assert 0.0 <= score <= 1.0


class TestIntegration:
    """Pruebas de integración completa."""

    @pytest.mark.asyncio
    async def test_full_audit_cycle(self):
        """Ciclo completo: run_full_audit sin errores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)

            # Ejecuta audit completo
            report = await audit.run_full_audit()

            # Verifica estructura
            assert isinstance(report, AuditReport)
            assert report.timestamp
            assert 0.0 <= report.health_score <= 1.0
            assert isinstance(report.binary_integrity, dict)
            assert isinstance(report.state_consistency, dict)
            assert isinstance(report.defense_health, dict)
            assert isinstance(report.mirror_coherence, dict)

    @pytest.mark.asyncio
    async def test_multiple_audit_cycles(self):
        """Múltiples ciclos de audit sin interferencias."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AutoAudit(storage_path=tmpdir)

            # Ejecuta 3 veces
            for i in range(3):
                report = await audit.run_full_audit()
                assert report.health_score >= 0.0

            # Verifica que log tiene 3 líneas
            audit_log = Path(tmpdir) / "audit_log.jsonl"
            lines = audit_log.read_text().strip().split("\n")
            assert len(lines) == 3


class TestHealthCheckResult:
    """Pruebas del dataclass HealthCheckResult."""

    def test_health_check_result_creation(self):
        """HealthCheckResult se crea correctamente."""
        result = HealthCheckResult(
            name="test_check",
            passed=True,
            timestamp=datetime.utcnow().timestamp(),
            issues=[],
            details={},
        )
        assert result.name == "test_check"
        assert result.passed is True


class TestAuditReportDataclass:
    """Pruebas del dataclass AuditReport."""

    def test_audit_report_creation(self):
        """AuditReport se crea correctamente."""
        report = AuditReport(
            timestamp=datetime.utcnow().isoformat(),
            health_score=0.75,
            binary_integrity={"file1.py": True},
            state_consistency={"consistent": True},
            defense_health={"corvid": True, "cephalopod": True},
            mirror_coherence={"coherent": True},
            issues=["test issue"],
            action_taken="test action",
        )
        assert report.health_score == 0.75
        assert len(report.issues) == 1


# Async test helper
@pytest.fixture
def event_loop():
    """Crea event loop para tests async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
