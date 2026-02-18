"""Tests for centinel_engine.vital_signs (Level 1 homeostasis).

Pruebas para centinel_engine.vital_signs (Nivel 1 de homeostasis).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Ensure the centinel_engine package is importable /
# Asegurar que el paquete centinel_engine sea importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from centinel_engine.vital_signs import (  # noqa: E402
    DEFAULT_HEALTH_STATE,
    DEFAULT_THRESHOLDS,
    _compute_avg_latency,
    _compute_success_rate,
    check_vital_signs,
    load_health_state,
    save_health_state,
    update_status_after_scrape,
)

# ---------------------------------------------------------------------------
# Fixtures / Fixtures de prueba
# ---------------------------------------------------------------------------

BASE_CONFIG: Dict[str, Any] = {
    "scrape_interval_seconds": 300,
}


def _normal_status() -> Dict[str, Any]:
    """Return a healthy scrape status / Retorna un estado de scrape saludable."""
    return {
        "consecutive_failures": 0,
        "success_history": [True] * 10,
        "latency_history": [1.0, 1.2, 0.9, 1.1, 1.3, 0.8, 1.0, 1.1, 0.9, 1.0],
        "hash_chain_valid": True,
        "last_status_code": 200,
    }


# ---------------------------------------------------------------------------
# Test 1: Normal mode / Modo normal
# ---------------------------------------------------------------------------


class TestNormalMode:
    """Tests for normal operational mode / Pruebas para modo operativo normal."""

    def test_normal_mode_defaults(self) -> None:
        """All metrics healthy -> mode='normal', delay=300.

        Bilingual: Todas las metricas saludables -> mode='normal', delay=300.
        """
        result = check_vital_signs(BASE_CONFIG, _normal_status())

        assert result["mode"] == "normal"
        assert result["recommended_delay_seconds"] == 300
        assert result["alert_needed"] is False
        assert result["hash_chain_valid"] is True

    def test_normal_mode_no_history(self) -> None:
        """Empty histories default to normal / Historiales vacios retornan normal."""
        result = check_vital_signs(BASE_CONFIG, {})

        assert result["mode"] == "normal"
        assert result["recommended_delay_seconds"] == 300
        assert result["alert_needed"] is False

    def test_ethical_minimum_delay(self) -> None:
        """Delay never drops below 300s even with low config.

        Bilingual: El delay nunca baja de 300s incluso con config bajo.
        """
        config = {"scrape_interval_seconds": 60}
        result = check_vital_signs(config, _normal_status())

        assert result["recommended_delay_seconds"] >= 300


# ---------------------------------------------------------------------------
# Test 2: Conservative mode via consecutive failures
# ---------------------------------------------------------------------------


class TestConservativeMode:
    """Tests for conservative mode / Pruebas para modo conservador."""

    def test_conservative_by_failures(self) -> None:
        """3 consecutive failures -> conservative, delay >= 600.

        Bilingual: 3 fallos consecutivos -> conservador, delay >= 600.
        """
        status = _normal_status()
        status["consecutive_failures"] = 3

        result = check_vital_signs(BASE_CONFIG, status)

        assert result["mode"] == "conservative"
        assert result["recommended_delay_seconds"] >= 600
        assert result["alert_needed"] is True

    def test_conservative_by_low_success_rate(self) -> None:
        """Success rate below 0.70 -> conservative.

        Bilingual: Tasa de exito por debajo de 0.70 -> conservador.
        """
        status = _normal_status()
        status["success_history"] = [True, True, False, False, False, False, False, True, False, False]
        # success_rate = 3/10 = 0.30

        result = check_vital_signs(BASE_CONFIG, status)

        assert result["mode"] in {"conservative", "critical"}
        assert result["alert_needed"] is True

    def test_conservative_by_high_latency(self) -> None:
        """Average latency > 10s -> conservative.

        Bilingual: Latencia promedio > 10s -> conservador.
        """
        status = _normal_status()
        status["latency_history"] = [12.0, 15.0, 11.0, 13.0, 14.0]

        result = check_vital_signs(BASE_CONFIG, status)

        assert result["mode"] == "conservative"
        assert result["recommended_delay_seconds"] >= 600
        assert result["alert_needed"] is True


# ---------------------------------------------------------------------------
# Test 3: Critical mode via hash chain broken
# ---------------------------------------------------------------------------


class TestCriticalMode:
    """Tests for critical mode / Pruebas para modo critico."""

    def test_critical_by_hash_chain_broken(self) -> None:
        """Broken hash chain ALWAYS triggers critical, delay >= 1800.

        Bilingual: Cadena de hashes rota SIEMPRE dispara critico, delay >= 1800.
        """
        status = _normal_status()
        status["hash_chain_valid"] = False

        result = check_vital_signs(BASE_CONFIG, status)

        assert result["mode"] == "critical"
        assert result["recommended_delay_seconds"] >= 1800
        assert result["alert_needed"] is True
        assert "hash_chain_broken" in result["metrics"]["critical_reasons"]

    def test_critical_by_many_failures(self) -> None:
        """5+ consecutive failures -> critical.

        Bilingual: 5+ fallos consecutivos -> critico.
        """
        status = _normal_status()
        status["consecutive_failures"] = 5

        result = check_vital_signs(BASE_CONFIG, status)

        assert result["mode"] == "critical"
        assert result["recommended_delay_seconds"] >= 1800
        assert result["alert_needed"] is True

    def test_critical_overrides_conservative(self) -> None:
        """Critical conditions override conservative when both trigger.

        Bilingual: Condiciones criticas sobreescriben conservador cuando ambos aplican.
        """
        status = _normal_status()
        status["consecutive_failures"] = 6  # triggers both conservative and critical
        status["hash_chain_valid"] = False

        result = check_vital_signs(BASE_CONFIG, status)

        assert result["mode"] == "critical"


# ---------------------------------------------------------------------------
# Test 4: Persistence - save & load
# ---------------------------------------------------------------------------


class TestPersistence:
    """Tests for health state persistence / Pruebas para persistencia del estado."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Save then load returns the same state.

        Bilingual: Guardar y luego cargar retorna el mismo estado.
        """
        state = check_vital_signs(BASE_CONFIG, _normal_status())
        health_path = tmp_path / "health_state.json"

        save_health_state(state, health_path)
        loaded = load_health_state(health_path)

        assert loaded["mode"] == state["mode"]
        assert loaded["recommended_delay_seconds"] == state["recommended_delay_seconds"]
        assert loaded["alert_needed"] == state["alert_needed"]
        assert loaded["consecutive_failures"] == state["consecutive_failures"]

    def test_load_missing_returns_defaults(self, tmp_path: Path) -> None:
        """Loading from nonexistent path returns defaults.

        Bilingual: Cargar desde ruta inexistente retorna valores por defecto.
        """
        health_path = tmp_path / "nonexistent" / "health_state.json"
        loaded = load_health_state(health_path)

        assert loaded["mode"] == "normal"
        assert loaded["recommended_delay_seconds"] == 300
        assert loaded["alert_needed"] is False

    def test_load_corrupted_returns_defaults(self, tmp_path: Path) -> None:
        """Loading corrupted JSON returns defaults.

        Bilingual: Cargar JSON corrupto retorna valores por defecto.
        """
        health_path = tmp_path / "health_state.json"
        health_path.write_text("NOT VALID JSON {{{{", encoding="utf-8")

        loaded = load_health_state(health_path)

        assert loaded["mode"] == "normal"
        assert loaded == DEFAULT_HEALTH_STATE

    def test_load_non_dict_returns_defaults(self, tmp_path: Path) -> None:
        """Loading a JSON array (not dict) returns defaults.

        Bilingual: Cargar un array JSON (no dict) retorna valores por defecto.
        """
        health_path = tmp_path / "health_state.json"
        health_path.write_text("[1, 2, 3]", encoding="utf-8")

        loaded = load_health_state(health_path)

        assert loaded == DEFAULT_HEALTH_STATE

    def test_atomic_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """save_health_state creates parent directories.

        Bilingual: save_health_state crea directorios padre.
        """
        health_path = tmp_path / "nested" / "deep" / "health_state.json"
        state = {"mode": "normal", "test": True}

        save_health_state(state, health_path)

        assert health_path.exists()
        loaded = json.loads(health_path.read_text(encoding="utf-8"))
        assert loaded["mode"] == "normal"


# ---------------------------------------------------------------------------
# Test 5: update_status_after_scrape helper
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    """Tests for the status update helper / Pruebas para el helper de actualizacion."""

    def test_success_resets_failures(self) -> None:
        """A successful scrape resets consecutive_failures to 0.

        Bilingual: Un scrape exitoso reinicia consecutive_failures a 0.
        """
        current = {"consecutive_failures": 3, "success_history": [], "latency_history": []}
        updated = update_status_after_scrape(current, success=True, latency=1.5, status_code=200)

        assert updated["consecutive_failures"] == 0
        assert updated["success_history"] == [True]

    def test_failure_increments(self) -> None:
        """A failed scrape increments consecutive_failures.

        Bilingual: Un scrape fallido incrementa consecutive_failures.
        """
        current = {"consecutive_failures": 2, "success_history": [], "latency_history": []}
        updated = update_status_after_scrape(current, success=False, latency=30.0, status_code=429)

        assert updated["consecutive_failures"] == 3
        assert updated["success_history"] == [False]
        assert updated["last_status_code"] == 429

    def test_history_window_trimming(self) -> None:
        """Histories are trimmed to window size.

        Bilingual: Los historiales se recortan al tamano de ventana.
        """
        current = {
            "consecutive_failures": 0,
            "success_history": [True] * 10,
            "latency_history": [1.0] * 10,
        }
        updated = update_status_after_scrape(current, success=True, latency=2.0, window=10)

        assert len(updated["success_history"]) == 10
        assert len(updated["latency_history"]) == 10
        assert updated["latency_history"][-1] == 2.0


# ---------------------------------------------------------------------------
# Test 6: Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for internal helper functions / Pruebas para funciones auxiliares internas."""

    def test_success_rate_empty(self) -> None:
        """Empty history returns 1.0 / Historial vacio retorna 1.0."""
        assert _compute_success_rate([]) == 1.0

    def test_success_rate_all_success(self) -> None:
        """All True returns 1.0 / Todos True retorna 1.0."""
        assert _compute_success_rate([True, True, True]) == 1.0

    def test_success_rate_mixed(self) -> None:
        """Mixed results compute correctly / Resultados mixtos calculan correctamente."""
        rate = _compute_success_rate([True, False, True, False])
        assert abs(rate - 0.5) < 0.001

    def test_avg_latency_empty(self) -> None:
        """Empty latency returns 0.0 / Latencia vacia retorna 0.0."""
        assert _compute_avg_latency([]) == 0.0

    def test_avg_latency_values(self) -> None:
        """Average computed correctly / Promedio calculado correctamente."""
        avg = _compute_avg_latency([2.0, 4.0, 6.0])
        assert abs(avg - 4.0) < 0.001


# ---------------------------------------------------------------------------
# Test 7: Default thresholds constants
# ---------------------------------------------------------------------------


class TestDefaultConstants:
    """Tests for default constant values / Pruebas para valores constantes por defecto."""

    def test_default_thresholds_values(self) -> None:
        """DEFAULT_THRESHOLDS has expected values / Valores esperados en DEFAULT_THRESHOLDS."""
        assert DEFAULT_THRESHOLDS["consecutive_failures_conservative"] == 3
        assert DEFAULT_THRESHOLDS["consecutive_failures_critical"] == 5
        assert DEFAULT_THRESHOLDS["min_success_rate"] == 0.70
        assert DEFAULT_THRESHOLDS["max_avg_latency"] == 10.0

    def test_default_health_state_structure(self) -> None:
        """DEFAULT_HEALTH_STATE has expected structure.

        Bilingual: DEFAULT_HEALTH_STATE tiene la estructura esperada.
        """
        assert DEFAULT_HEALTH_STATE["mode"] == "normal"
        assert DEFAULT_HEALTH_STATE["recommended_delay_seconds"] == 300
        assert DEFAULT_HEALTH_STATE["alert_needed"] is False
        assert DEFAULT_HEALTH_STATE["consecutive_failures"] == 0

    def test_custom_thresholds_override(self) -> None:
        """Config overrides default thresholds.

        Bilingual: La config sobreescribe los umbrales por defecto.
        """
        config = {
            "scrape_interval_seconds": 300,
            "consecutive_failures_conservative": 1,
        }
        status = _normal_status()
        status["consecutive_failures"] = 1

        result = check_vital_signs(config, status)

        assert result["mode"] == "conservative"
