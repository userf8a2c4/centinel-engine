"""
CINCO DEFENSAS ANIMALES DEL CENTINEL
(FIVE ANIMAL DEFENSES OF CENTINEL)

Sistema de protección multi-capa inspirado en comportamientos animales.
(Multi-layer protection system inspired by animal behaviors.)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


class AnimalDefense(Enum):
    """
    Defensas animales numeradas y localizadas.
    (Numbered and localized animal defenses.)
    """

    # 🐦 Cuervo: Memoria distribuida de testimonios
    CORVID = (
        "🐦",
        "Cuervo",
        "Memoria de Cuervo",
        "Gossip distribuido: testigos confirman hechos entre sí",
    )

    # 🦑 Pulpo: Cifrado de tránsito
    CEPHALOPOD = (
        "🦑",
        "Pulpo",
        "Tinta de Pulpo",
        "Cifrado ChaCha20Poly1305: oculta tráfico entre testigos",
    )

    # 🦌 Venado: Timing impredecible
    EVASION = (
        "🦌",
        "Venado",
        "Evasión de Venado",
        "Jitter + decoys: timing impredecible de snapshots",
    )

    # 🦎 Lagartija: Auto-regeneración
    REGENERATION = (
        "🦎",
        "Lagartija",
        "Regeneración de Lagartija",
        "Sync nightly con mirrors: detección + restauración de compromiso",
    )

    # ⚔️ Tejón: Congelación + recuperación
    KILL_SWITCH = (
        "⚔️",
        "Tejón",
        "Defensa de Tejón",
        "Freeze instantáneo + exponential backoff: respuesta a ataque activo",
    )

    @property
    def emoji(self) -> str:
        return self.value[0]

    @property
    def name_es(self) -> str:
        return self.value[1]

    @property
    def title_es(self) -> str:
        return self.value[2]

    @property
    def description_es(self) -> str:
        return self.value[3]


@dataclass
class DefenseStatus:
    """
    Estado operacional de una defensa.
    (Operational status of a defense.)
    """

    defense: AnimalDefense
    enabled: bool
    last_check_ts: float
    last_alert: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializar a diccionario."""
        return {
            "emoji": self.defense.emoji,
            "name_es": self.defense.name_es,
            "title_es": self.defense.title_es,
            "enabled": self.enabled,
            "last_check_ts": self.last_check_ts,
            "last_alert": self.last_alert,
            "metrics": self.metrics,
        }


# Mapeo de defensas para acceso rápido
ALL_DEFENSES = {
    "corvid": AnimalDefense.CORVID,
    "cephalopod": AnimalDefense.CEPHALOPOD,
    "evasion": AnimalDefense.EVASION,
    "regeneration": AnimalDefense.REGENERATION,
    "kill_switch": AnimalDefense.KILL_SWITCH,
}
