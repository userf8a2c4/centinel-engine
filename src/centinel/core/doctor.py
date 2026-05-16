"""Preflight self-audit — `centinel doctor`.

The hardening is only as good as the configuration it runs under. An
operator preparing a polling-place deployment needs to know, *before*
election night, whether the security posture their CENTINEL_MODE
promises is actually satisfied — not discover a missing signing key at
20:00 when results start flowing.

`run_doctor()` resolves the active security profile (see profiles.py)
and checks the live environment against it. Every check returns one of:

  READY   — satisfied.
  WARNING — degraded but not fatal; capture still works, defense weaker.
  BLOCKED — a hard gate the active mode requires is unmet; fix before
            running an election.

It is a pure read: it never writes evidence, never mutates the chain,
and never fabricates the things it checks for (a missing signing key is
reported, not silently generated). Writability probes use throwaway
temp files in the real target directories and clean up after themselves.

Bilingüe: autoauditoría previa. Verifica que la postura de seguridad
que promete el modo activo se cumple de verdad, antes de la elección.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .profiles import SecurityProfile, resolve_profile

_HEX64 = frozenset("0123456789abcdef")

READY = "READY"
WARNING = "WARNING"
BLOCKED = "BLOCKED"

_SEVERITY_ORDER = {READY: 0, WARNING: 1, BLOCKED: 2}


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    remedy: str = ""


@dataclass(frozen=True)
class DoctorReport:
    profile: SecurityProfile
    checks: List[CheckResult]

    @property
    def overall(self) -> str:
        worst = READY
        for c in self.checks:
            if _SEVERITY_ORDER[c.status] > _SEVERITY_ORDER[worst]:
                worst = c.status
        return worst

    @property
    def election_ready(self) -> bool:
        return self.overall != BLOCKED


def _looks_like_sha256(value: str) -> bool:
    v = value.strip().lower().replace(":", "")
    return len(v) == 64 and set(v) <= _HEX64


def _check_mode(profile: SecurityProfile) -> CheckResult:
    return CheckResult(
        name="mode",
        status=READY,
        detail=(
            f"CENTINEL_MODE resolved to '{profile.mode}'. "
            f"Security posture: signing_required={profile.signature_required}, "
            f"cne_pinning_required={profile.cne_pinning_required}, "
            f"breaker_enforced={profile.breaker_enforced}."
        ),
    )


def _check_signing(profile: SecurityProfile) -> CheckResult:
    env_path = os.getenv("CENTINEL_OPERATOR_KEY_PATH")
    key_path = Path(env_path) if env_path else Path("keys") / "operator_private.pem"
    exists = key_path.exists()

    if exists:
        return CheckResult(
            name="signing_key",
            status=READY,
            detail=f"Operator signing key present at {key_path}.",
        )
    if profile.signature_required:
        return CheckResult(
            name="signing_key",
            status=BLOCKED,
            detail=(
                f"Mode '{profile.mode}' REQUIRES signed evidence but no "
                f"operator key was found at {key_path}."
            ),
            remedy=(
                "Generate one with generate_operator_keypair() (or set "
                "CENTINEL_OPERATOR_KEY_PATH to an existing Ed25519 key) "
                "before running an election."
            ),
        )
    return CheckResult(
        name="signing_key",
        status=WARNING,
        detail=(
            f"No operator signing key at {key_path}. Snapshots will be "
            f"unsigned in mode '{profile.mode}'."
        ),
        remedy="Recommended: generate a key so evidence is attributable.",
    )


def _check_cne_pinning(profile: SecurityProfile) -> CheckResult:
    raw = os.getenv("CENTINEL_CNE_CERT_SHA256", "").strip()
    if raw and _looks_like_sha256(raw):
        return CheckResult(
            name="cne_cert_pinning",
            status=READY,
            detail="CNE TLS certificate fingerprint pinned (anti state-MITM).",
        )
    if raw and not _looks_like_sha256(raw):
        return CheckResult(
            name="cne_cert_pinning",
            status=BLOCKED if profile.cne_pinning_required else WARNING,
            detail=(
                "CENTINEL_CNE_CERT_SHA256 is set but is not a valid 64-char "
                "hex SHA-256 fingerprint."
            ),
            remedy=(
                "Set it to the exact SHA-256 of the expected CNE leaf "
                "certificate (lowercase hex, colons optional)."
            ),
        )
    if profile.cne_pinning_required:
        return CheckResult(
            name="cne_cert_pinning",
            status=BLOCKED,
            detail=(
                f"Mode '{profile.mode}' REQUIRES CNE certificate pinning "
                f"but CENTINEL_CNE_CERT_SHA256 is unset. A state-level MITM "
                f"with a compromised CA would be undetectable."
            ),
            remedy=(
                "Capture the CNE leaf cert fingerprint now and export "
                "CENTINEL_CNE_CERT_SHA256 before election day."
            ),
        )
    return CheckResult(
        name="cne_cert_pinning",
        status=WARNING,
        detail=f"CNE cert pinning inactive in mode '{profile.mode}'.",
        remedy="Recommended before any real capture against the live CNE.",
    )


def _probe_writable_durable(target: Path, label: str) -> CheckResult:
    """Verify `target` can hold an atomically-written, fsync'd file."""
    try:
        target.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".doctor_", dir=str(target))
        try:
            os.write(fd, b"centinel-doctor-probe")
            os.fsync(fd)
        finally:
            os.close(fd)
            os.unlink(tmp_name)
        dir_fd = os.open(str(target), os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError as exc:
        return CheckResult(
            name=label,
            status=BLOCKED,
            detail=f"{target} is not writable/durable: {exc}",
            remedy=f"Ensure the process can create and fsync files in {target}.",
        )
    return CheckResult(
        name=label,
        status=READY,
        detail=f"{target} is writable and fsync-durable.",
    )


def _check_breaker_secret() -> CheckResult:
    env_key = os.getenv("CENTINEL_STATE_HMAC_KEY", "").strip()
    if len(env_key) >= 16:
        return CheckResult(
            name="breaker_state_integrity",
            status=READY,
            detail="Circuit-breaker state HMAC key supplied via env.",
        )
    if env_key:
        return CheckResult(
            name="breaker_state_integrity",
            status=WARNING,
            detail=(
                "CENTINEL_STATE_HMAC_KEY is set but shorter than 16 chars; "
                "a local on-disk secret will be used instead."
            ),
            remedy="Use a >=16-char key, or rely on the auto-generated file.",
        )
    return CheckResult(
        name="breaker_state_integrity",
        status=READY,
        detail=(
            "No env HMAC key; breaker will use an auto-generated 0600 "
            "local secret (still tamper-evident)."
        ),
    )


def run_doctor(explicit_mode: str | None = None) -> DoctorReport:
    """Run all preflight checks for the active (or given) mode."""
    profile = resolve_profile(explicit_mode)
    checks = [
        _check_mode(profile),
        _check_signing(profile),
        _check_cne_pinning(profile),
        _probe_writable_durable(Path("data") / "snapshots", "snapshot_storage"),
        _probe_writable_durable(Path("data") / "transparency", "transparency_log"),
        _check_breaker_secret(),
    ]
    return DoctorReport(profile=profile, checks=checks)


def format_report(report: DoctorReport) -> str:
    """Render a human-readable bilingual report block."""
    icon = {READY: "[ OK ]", WARNING: "[WARN]", BLOCKED: "[STOP]"}
    lines = [
        "Centinel preflight / autoauditoría previa",
        f"  mode: {report.profile.mode}",
        f"  overall: {report.overall} " f"(election_ready={report.election_ready})",
        "",
    ]
    for c in report.checks:
        lines.append(f"  {icon[c.status]} {c.name}: {c.detail}")
        if c.remedy and c.status != READY:
            lines.append(f"         -> {c.remedy}")
    if report.overall == BLOCKED:
        lines.append("")
        lines.append(
            "  BLOCKED: fix the [STOP] items before running an election. "
            "/ Corrige los puntos [STOP] antes de una elección."
        )
    return "\n".join(lines)
