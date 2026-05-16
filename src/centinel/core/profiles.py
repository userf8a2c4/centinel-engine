"""One-dial security orchestration on top of the existing CENTINEL_MODE.

The hardening work (mandatory signing, cert pinning, breaker HMAC,
external anchoring) is powerful but exposes several independent
environment switches. An ordinary field operator should not have to
remember six flags the night before an election.

`CENTINEL_MODE` already exists and governs *capture cadence*
(`maintenance` ~30d, `monitoring` ~24h, `election` ~5m). This module
reuses that same dial — without changing its cadence meaning — to also
derive the *security posture* that fits the stakes of each mode:

  - maintenance : off-season, low stakes. Signing/pinning optional,
                  breaker on, external anchor on.
  - monitoring  : elevated. Signing/pinning recommended, breaker on,
                  external anchor on.
  - election    : maximum. Signing REQUIRED, cert pinning REQUIRED,
                  breaker enforced, external anchor on.

Non-regression contract: an environment variable the operator set
explicitly always wins. `apply_profile_defaults()` only fills in the
switches the operator left unset, so existing deployments that pin
flags by hand keep their exact behavior. A profile never relaxes a
switch the operator tightened.

Bilingüe: un solo dial (CENTINEL_MODE) deriva la postura de seguridad
adecuada al riesgo de cada modo. Lo que el operador fija a mano siempre
gana; el perfil solo rellena lo que quedó sin definir.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

_LOGGER = logging.getLogger("centinel.profiles")

_MODE_ENV = "CENTINEL_MODE"
_DEFAULT_MODE = "maintenance"
_VALID_MODES = ("maintenance", "monitoring", "election")

_TRUTHY = ("1", "true", "yes", "on")


@dataclass(frozen=True)
class SecurityProfile:
    """Resolved security posture for a given CENTINEL_MODE.

    `signature_required` and `cne_pinning_required` are hard gates that
    `doctor` blocks on. `*_recommended` are soft: missing them is a
    WARNING, not a halt.
    """

    mode: str
    signature_required: bool
    signature_recommended: bool
    cne_pinning_required: bool
    cne_pinning_recommended: bool
    breaker_enforced: bool
    external_anchor_enabled: bool

    def as_dict(self) -> Dict[str, object]:
        return {
            "mode": self.mode,
            "signature_required": self.signature_required,
            "signature_recommended": self.signature_recommended,
            "cne_pinning_required": self.cne_pinning_required,
            "cne_pinning_recommended": self.cne_pinning_recommended,
            "breaker_enforced": self.breaker_enforced,
            "external_anchor_enabled": self.external_anchor_enabled,
        }


_PROFILES: Dict[str, SecurityProfile] = {
    "maintenance": SecurityProfile(
        mode="maintenance",
        signature_required=False,
        signature_recommended=True,
        cne_pinning_required=False,
        cne_pinning_recommended=False,
        breaker_enforced=True,
        external_anchor_enabled=True,
    ),
    "monitoring": SecurityProfile(
        mode="monitoring",
        signature_required=False,
        signature_recommended=True,
        cne_pinning_required=False,
        cne_pinning_recommended=True,
        breaker_enforced=True,
        external_anchor_enabled=True,
    ),
    "election": SecurityProfile(
        mode="election",
        signature_required=True,
        signature_recommended=True,
        cne_pinning_required=True,
        cne_pinning_recommended=True,
        breaker_enforced=True,
        external_anchor_enabled=True,
    ),
}


def resolve_mode(explicit: Optional[str] = None) -> str:
    """Return a valid CENTINEL_MODE, falling back to maintenance.

    An unknown value degrades to the safest-cadence mode rather than
    raising: a misconfigured dial must not crash election-night capture.
    """
    raw = explicit if explicit is not None else os.getenv(_MODE_ENV, _DEFAULT_MODE)
    mode = raw.strip().lower()
    if mode not in _VALID_MODES:
        _LOGGER.warning("centinel_mode_unknown value=%r falling_back=%s", raw, _DEFAULT_MODE)
        return _DEFAULT_MODE
    return mode


def resolve_profile(explicit_mode: Optional[str] = None) -> SecurityProfile:
    """Resolve the security posture for the active (or given) mode."""
    return _PROFILES[resolve_mode(explicit_mode)]


def _set_default(name: str, value: str) -> bool:
    """Set env `name` to `value` only if unset/blank. Returns True if set."""
    current = os.environ.get(name)
    if current is not None and current.strip() != "":
        return False
    os.environ[name] = value
    return True


def apply_profile_defaults(explicit_mode: Optional[str] = None) -> Dict[str, object]:
    """Fill unset security switches from the resolved profile.

    Only touches variables the operator left unset — explicit operator
    configuration always wins, so this never reverses a deliberate
    choice (no regression). Returns a summary describing the resolved
    profile and exactly which defaults were applied vs. left to the
    operator's explicit value.
    """
    profile = resolve_profile(explicit_mode)
    applied: Dict[str, str] = {}

    if profile.signature_required:
        if _set_default("CENTINEL_REQUIRE_SIGNATURE", "true"):
            applied["CENTINEL_REQUIRE_SIGNATURE"] = "true"

    if profile.external_anchor_enabled:
        # Only express the default as the *absence* of the opt-out, so an
        # operator who explicitly disabled OTS keeps that choice.
        if os.environ.get("CENTINEL_DISABLE_OPENTIMESTAMPS") is None:
            os.environ["CENTINEL_DISABLE_OPENTIMESTAMPS"] = "false"
            applied["CENTINEL_DISABLE_OPENTIMESTAMPS"] = "false"

    _LOGGER.info(
        "security_profile_applied mode=%s defaults_applied=%s",
        profile.mode,
        sorted(applied),
    )
    return {
        "profile": profile.as_dict(),
        "defaults_applied": applied,
        "note": (
            "Operator-set variables were preserved; only unset switches "
            "were filled. Hard gates (signing key, CNE cert pinning) are "
            "verified by `centinel doctor`, not auto-fabricated."
        ),
    }
