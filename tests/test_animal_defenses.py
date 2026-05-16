"""
Tests para Animal Defenses (Defensas Animales)
Tests for Animal Defenses
"""

import pytest
from centinel.core.animal_defenses import AnimalDefense, DefenseStatus, ALL_DEFENSES


class TestAnimalDefenseEnum:
    """Tests para el enum AnimalDefense."""

    def test_all_defenses_have_properties(self):
        """Todos las defensas tienen propiedades requeridas."""
        for defense in AnimalDefense:
            assert defense.emoji
            assert defense.name_es
            assert defense.title_es
            assert defense.description_es
            assert isinstance(defense.emoji, str)
            assert len(defense.emoji) > 0

    def test_corvid_properties(self):
        """Test de Cuervo (Corvid Memory)."""
        defense = AnimalDefense.CORVID
        assert defense.emoji == "🐦"
        assert defense.name_es == "Cuervo"
        assert defense.title_es == "Memoria de Cuervo"
        assert "Gossip distribuido" in defense.description_es

    def test_cephalopod_properties(self):
        """Test de Pulpo (Cephalopod Ink)."""
        defense = AnimalDefense.CEPHALOPOD
        assert defense.emoji == "🦑"
        assert defense.name_es == "Pulpo"
        assert defense.title_es == "Tinta de Pulpo"
        assert "ChaCha20Poly1305" in defense.description_es

    def test_evasion_properties(self):
        """Test de Venado (Evasion/Deer)."""
        defense = AnimalDefense.EVASION
        assert defense.emoji == "🦌"
        assert defense.name_es == "Venado"
        assert defense.title_es == "Evasión de Venado"
        assert "Jitter" in defense.description_es

    def test_regeneration_properties(self):
        """Test de Lagartija (Regeneration)."""
        defense = AnimalDefense.REGENERATION
        assert defense.emoji == "🦎"
        assert defense.name_es == "Lagartija"
        assert defense.title_es == "Regeneración de Lagartija"
        assert "mirrors" in defense.description_es

    def test_kill_switch_properties(self):
        """Test de Tejón (Kill Switch/Badger)."""
        defense = AnimalDefense.KILL_SWITCH
        assert defense.emoji == "⚔️"
        assert defense.name_es == "Tejón"
        assert defense.title_es == "Defensa de Tejón"
        assert "Freeze" in defense.description_es
        assert "exponential backoff" in defense.description_es

    def test_all_defenses_mapping(self):
        """ALL_DEFENSES contiene todos los enum values."""
        assert len(ALL_DEFENSES) == 5
        assert "corvid" in ALL_DEFENSES
        assert "cephalopod" in ALL_DEFENSES
        assert "evasion" in ALL_DEFENSES
        assert "regeneration" in ALL_DEFENSES
        assert "kill_switch" in ALL_DEFENSES

    def test_all_defenses_map_to_enum(self):
        """ALL_DEFENSES values son instancias de AnimalDefense."""
        for key, defense in ALL_DEFENSES.items():
            assert isinstance(defense, AnimalDefense)


class TestDefenseStatus:
    """Tests para DefenseStatus dataclass."""

    def test_defense_status_creation(self):
        """Crear DefenseStatus válido."""
        status = DefenseStatus(
            defense=AnimalDefense.CORVID,
            enabled=True,
            last_check_ts=1234567890.0,
        )
        assert status.defense == AnimalDefense.CORVID
        assert status.enabled is True
        assert status.last_check_ts == 1234567890.0

    def test_defense_status_with_metrics(self):
        """DefenseStatus con métricas."""
        metrics = {"gossip_peers": 2, "last_attestation": "5m ago"}
        status = DefenseStatus(
            defense=AnimalDefense.CORVID,
            enabled=True,
            last_check_ts=1234567890.0,
            metrics=metrics,
        )
        assert status.metrics == metrics

    def test_defense_status_with_alert(self):
        """DefenseStatus con alerta."""
        status = DefenseStatus(
            defense=AnimalDefense.CORVID,
            enabled=True,
            last_check_ts=1234567890.0,
            last_alert="Sibling offline for 30 minutes",
        )
        assert status.last_alert == "Sibling offline for 30 minutes"

    def test_defense_status_to_dict(self):
        """Convertir DefenseStatus a diccionario."""
        status = DefenseStatus(
            defense=AnimalDefense.CORVID,
            enabled=True,
            last_check_ts=1234567890.0,
            metrics={"test": "value"},
        )
        data = status.to_dict()

        assert data["emoji"] == "🐦"
        assert data["name_es"] == "Cuervo"
        assert data["title_es"] == "Memoria de Cuervo"
        assert data["enabled"] is True
        assert data["metrics"] == {"test": "value"}

    def test_all_defense_statuses(self):
        """Crear status para todas las defensas."""
        for defense in AnimalDefense:
            status = DefenseStatus(
                defense=defense,
                enabled=True,
                last_check_ts=1234567890.0,
            )
            assert status.defense == defense
            assert status.enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
