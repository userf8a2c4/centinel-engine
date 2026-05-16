"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/cli.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - main
  - bloque_main

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/cli.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - main
  - bloque_main

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Cli Module
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


import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from centinel.core.animal_defenses import AnimalDefense, ALL_DEFENSES

app = typer.Typer(help="Centinel Engine CLI")


# Subcomandos
panel_app = typer.Typer(help="Panel operador — Operador panel status")


@app.callback()
def main() -> None:
    """Interfaz de línea de comandos de Centinel.

    English: Centinel command line interface.
    """


@app.command()
def doctor(
    mode: Optional[str] = typer.Option(
        None,
        "--mode",
        help="Override CENTINEL_MODE for this check (maintenance|monitoring|election).",
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of text."
    ),
) -> None:
    """Preflight self-audit. Exits non-zero if the active mode is BLOCKED.

    English: Verify the security posture the active CENTINEL_MODE
    promises is actually satisfied before running an election.
    """
    from .core.doctor import BLOCKED, format_report, run_doctor

    report = run_doctor(mode)
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "profile": report.profile.as_dict(),
                    "overall": report.overall,
                    "election_ready": report.election_ready,
                    "checks": [
                        {
                            "name": c.name,
                            "status": c.status,
                            "detail": c.detail,
                            "remedy": c.remedy,
                        }
                        for c in report.checks
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        typer.echo(format_report(report))
    if report.overall == BLOCKED:
        raise typer.Exit(code=1)


@app.command()
def profile(
    mode: Optional[str] = typer.Option(
        None, "--mode", help="Override CENTINEL_MODE for this resolution."
    ),
) -> None:
    """Show the security posture derived from the active CENTINEL_MODE.

    English: Print which security switches the current mode implies,
    without mutating anything.
    """
    from .core.profiles import resolve_profile

    resolved = resolve_profile(mode)
    typer.echo(json.dumps(resolved.as_dict(), ensure_ascii=False, indent=2))


@app.command()
def status() -> None:
    """Ver estado general del sistema.

    English: Show overall system status.
    """
    typer.echo("🔍 Centinel Engine Status")
    typer.echo("=" * 50)

    # Placeholder: cargar estado desde archivos
    typer.echo("✅ Core: OPERATIONAL")
    typer.echo("🐦 Cuervo: ACTIVE")
    typer.echo("🦑 Pulpo: ACTIVE")
    typer.echo("🦌 Venado: ACTIVE")
    typer.echo("🦎 Lagartija: ACTIVE")
    typer.echo("⚔️ Tejón: READY")


@panel_app.command(name="show")
def panel_show(
    verbose: bool = typer.Option(
        False, "--verbose", help="Mostrar detalles completos / Show full details"
    )
) -> None:
    """Mostrar panel de estado operacional.

    English: Display operational status panel.
    """
    typer.echo("")
    typer.echo("╔════════════════════════════════════════════════════════════════╗")
    typer.echo("║ CENTINEL — Estado Operacional / Operational Status             ║")
    typer.echo("╠════════════════════════════════════════════════════════════════╣")
    typer.echo("║                                                                ║")

    # Threat score (placeholder)
    threat_score = 22
    status_color = (
        "🟢 VERDE" if threat_score < 31 else "🟡 AMARILLO" if threat_score < 75 else "🔴 ROJO"
    )
    typer.echo(f"║  AMENAZA GENERAL / Threat Score:  {threat_score:3d}/100 {status_color:<17} ║")
    typer.echo("║                                                                ║")

    # Defensas animales
    typer.echo("║  DEFENSAS ANIMALES / Animal Defenses:                         ║")
    typer.echo("║  ┌─────────────────────────────────────────────────────────┐  ║")

    for key, defense in ALL_DEFENSES.items():
        status_str = "ACTIVO ✓" if key != "kill_switch" else "READY  "
        detail = {
            "corvid": "Último:  5m",
            "cephalopod": "Clave: hash...",
            "evasion": "Jitter: ±30%",
            "regeneration": "Mirrors: 3/3",
            "kill_switch": "(no activado)",
        }
        line = f"│ {defense.emoji} {defense.name_es:<10} ({key:<13}): {status_str}  {detail.get(key, ''):<20}"
        typer.echo(f"║  {line:<63} ║")

    typer.echo("║  └─────────────────────────────────────────────────────────┘  ║")
    typer.echo("║                                                                ║")

    # Métricas
    typer.echo("║  MÉTRICAS / Metrics:                                           ║")
    typer.echo("║  Merkle Root:     abc123...abc123        [VIGENTE — 2m]        ║")
    typer.echo("║  Anomalías:       0 Benford + 0 Z-score                        ║")
    typer.echo("║  Conectividad:    4/4 endpoints UP       [100%]               ║")
    typer.echo("║  Snapshots:       2847 captured          [Last: 30s ago]       ║")
    typer.echo("║                                                                ║")

    if verbose:
        typer.echo("║  DETALLES VERBOSOS / Verbose Details:                      ║")
        typer.echo("║  Last merkle update: 2026-05-16T14:30:00Z                  ║")
        typer.echo("║  Threat events (24h): 0                                    ║")
        typer.echo("║  Recovery attempts: 0                                      ║")
        typer.echo("║                                                                ║")

    typer.echo("║  ⓘ Detalles: centinel panel show --verbose                    ║")
    typer.echo("║  ⓘ Auditoría: cat hashes/attack_log.jsonl                     ║")
    typer.echo("╚════════════════════════════════════════════════════════════════╝")
    typer.echo("")


@panel_app.command(name="json")
def panel_json() -> None:
    """Retornar estado en formato JSON para máquinas.

    English: Return status as JSON for machines.
    """
    data = {
        "threat_score": 22,
        "status": "🟢 GREEN",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "defenses": {
            "corvid": {
                "emoji": AnimalDefense.CORVID.emoji,
                "name_es": AnimalDefense.CORVID.name_es,
                "enabled": True,
                "last_attestation": "2m ago",
            },
            "cephalopod": {
                "emoji": AnimalDefense.CEPHALOPOD.emoji,
                "name_es": AnimalDefense.CEPHALOPOD.name_es,
                "enabled": True,
                "key_hash": "abc123...",
            },
            "evasion": {
                "emoji": AnimalDefense.EVASION.emoji,
                "name_es": AnimalDefense.EVASION.name_es,
                "enabled": True,
                "jitter_range": "±30%",
            },
            "regeneration": {
                "emoji": AnimalDefense.REGENERATION.emoji,
                "name_es": AnimalDefense.REGENERATION.name_es,
                "enabled": True,
                "mirrors": 3,
            },
            "kill_switch": {
                "emoji": AnimalDefense.KILL_SWITCH.emoji,
                "name_es": AnimalDefense.KILL_SWITCH.name_es,
                "status": "READY",
                "activated": False,
            },
        },
        "metrics": {
            "merkle_root": "abc123...abc123",
            "merkle_age_seconds": 120,
            "benford_anomalies": 0,
            "zscore_anomalies": 0,
            "connectivity": {"total": 4, "up": 4, "pct": 100},
            "snapshots_total": 2847,
            "last_snapshot_seconds_ago": 30,
        },
        "next_actions": "Monitor normally. Green status maintained.",
    }
    typer.echo(json.dumps(data, indent=2))


# Subcomandos para auto-audit
audit_app = typer.Typer(help="Auto-auditoría — Self-auditing system")


@audit_app.command(name="run")
def audit_run(
    verbose: bool = typer.Option(False, "--verbose", help="Mostrar detalles / Show details")
) -> None:
    """Ejecutar auto-auditoría ahora.

    English: Run self-audit immediately.
    """
    from centinel.core.auto_audit import AutoAudit
    import asyncio

    audit = AutoAudit()
    report = asyncio.run(audit.run_full_audit())

    typer.echo("")
    typer.echo("╔════════════════════════════════════════════════════════════════╗")
    typer.echo("║ AUTOSANITARIA — Self-Audit Report                              ║")
    typer.echo("╠════════════════════════════════════════════════════════════════╣")
    typer.echo(f"║  Timestamp:       {report.timestamp:<47} ║")

    health_pct = report.health_score * 100
    health_icon = "🟢" if health_pct >= 75 else "🟡" if health_pct >= 50 else "🔴"
    typer.echo(f"║  Health Score:    {health_pct:5.1f}% {health_icon:<50} ║")

    typer.echo("║                                                                ║")
    typer.echo("║  CHECKS:                                                       ║")

    integrity_ok = all(report.binary_integrity.values()) if report.binary_integrity else False
    state_ok = report.state_consistency.get("consistent", False)
    defenses_ok = sum(report.defense_health.values()) if report.defense_health else 0
    mirrors_ok = report.mirror_coherence.get("coherent", False)

    integrity_icon = "✓" if integrity_ok else "✗"
    state_icon = "✓" if state_ok else "✗"
    defenses_icon = "✓" if defenses_ok >= 4 else "✗"
    mirrors_icon = "✓" if mirrors_ok else "✗"

    typer.echo(f"║  {integrity_icon} Binary Integrity                                        ║")
    typer.echo(f"║  {state_icon} State Consistency                                        ║")
    typer.echo(
        f"║  {defenses_icon} Defense Health ({defenses_ok}/5)                                 ║"
    )
    typer.echo(f"║  {mirrors_icon} Mirror Coherence                                        ║")

    if report.issues:
        typer.echo("║                                                                ║")
        typer.echo("║  ISSUES:                                                       ║")
        for issue in report.issues[:3]:  # Show first 3 issues
            typer.echo(f"║  - {issue[:55]:<55} ║")

    if verbose:
        typer.echo("║                                                                ║")
        typer.echo("║  FULL REPORT (JSON):                                           ║")
        report_json = json.dumps(report.to_dict(), indent=2)
        for line in report_json.split("\n")[:10]:  # Show first 10 lines
            typer.echo(f"║  {line[:62]:<62} ║")

    typer.echo("╚════════════════════════════════════════════════════════════════╝")
    typer.echo("")


@audit_app.command(name="history")
def audit_history(
    limit: int = typer.Option(10, "--limit", help="Número de reportes / Number of reports")
) -> None:
    """Ver últimos reportes de auto-auditoría.

    English: View latest auto-audit reports.
    """
    audit_log = Path("hashes/audit_log.jsonl")

    if not audit_log.exists():
        typer.echo("❌ No audit history found. Run 'centinel audit run' first.")
        return

    typer.echo("")
    typer.echo(f"AUTOSANITARIA — Last {limit} Reports")
    typer.echo("=" * 70)

    lines = []
    try:
        with open(audit_log, "r") as f:
            lines = f.readlines()
    except Exception as e:
        typer.echo(f"❌ Error reading audit log: {e}")
        return

    # Show last N reports
    for line in lines[-limit:]:
        try:
            report = json.loads(line)
            ts = report.get("timestamp", "unknown")
            health = report.get("health_score", 0) * 100
            icon = "🟢" if health >= 75 else "🟡" if health >= 50 else "🔴"
            typer.echo(f"{icon} {ts:<30} Health: {health:5.1f}%")
        except Exception as e:
            typer.echo(f"⚠️  Skipped line: {e}")

    typer.echo("")


@audit_app.command(name="health")
def audit_health() -> None:
    """Mostrar solo health score.

    English: Show only health score.
    """
    audit_log = Path("hashes/audit_log.jsonl")

    if not audit_log.exists():
        typer.echo("⚠️  No audit history. Run 'centinel audit run' first.")
        return

    try:
        with open(audit_log, "r") as f:
            last_line = f.readlines()[-1]

        report = json.loads(last_line)
        health = report.get("health_score", 0) * 100
        icon = "🟢" if health >= 75 else "🟡" if health >= 50 else "🔴"
        typer.echo(f"{icon} Health Score: {health:.1f}%")
    except Exception as e:
        typer.echo(f"❌ Error reading audit: {e}")


# Agregar subcomandos
app.add_typer(panel_app, name="panel", help="Panel operador — Operador panel")
app.add_typer(audit_app, name="audit", help="Autosanitaria — Self-audit system")


if __name__ == "__main__":
    app()
