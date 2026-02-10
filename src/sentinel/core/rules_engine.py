"""Motor unificado de reglas para análisis estadístico de snapshots.

Punto de entrada único: ``RulesEngine.run()``.  Todas las reglas se
auto-registran vía el decorador ``@rule`` al ser importadas aquí.

Unified rules engine for statistical snapshot analysis.

Single entry point: ``RulesEngine.run()``.  All rules self-register via the
``@rule`` decorator when imported here.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Importar TODAS las reglas para que se auto-registren ────────────────
# Import ALL rules so they self-register via @rule decorator.
from sentinel.core.rules import (  # noqa: F401
    basic_diff_rule,
    benford_first_digit_rule,
    benford_law_rule,
    correlation_participation_vote_rule,
    geographic_dispersion_rule,
    granular_anomaly_rule,
    irreversibility_rule,
    large_numbers_rule,
    last_digit_uniformity_rule,
    mesas_diff_rule,
    ml_outliers_rule,
    null_blank_rule,
    participation_anomaly_advanced_rule,
    participation_anomaly_rule,
    processing_speed_rule,
    runs_test_rule,
    snapshot_jump_rule,
    table_consistency_rule,
    trend_shift_rule,
    turnout_impossible_rule,
)
from sentinel.core.hashchain import compute_hash
from sentinel.core.rules.registry import RuleDefinition, list_rules

logger = logging.getLogger(__name__)

RULE_CONFIG_ALIASES: dict[str, str] = {
    "benford": "benford_first_digit",
    "benford_law": "benford_first_digit",
    "irreversibility": "irreversibility_rule",
    "processing_speed": "processing_speed_rule",
    "ml_outliers": "ml_outliers_rule",
    "participation_anomaly": "participation_anomaly_rule",
    "snapshot_jump": "snapshot_jump_rule",
    "null_blank": "null_blank_votes",
    "turnout": "turnout_impossible",
}


@dataclass(frozen=True)
class RulesEngineResult:
    """Resultado agregado de la ejecución de reglas.

    Aggregated result from running rules.
    """

    alerts: list[dict] = field(default_factory=list)
    critical_alerts: list[dict] = field(default_factory=list)
    pause_snapshots: bool = False


class RulesEngine:
    """Ejecuta reglas avanzadas sobre snapshots actuales y previos.

    Único punto de entrada para ejecutar TODAS las reglas registradas,
    verificar la cadena de hashes y generar reportes.

    Runs advanced rules on current and previous snapshots.

    Single entry point to execute ALL registered rules, verify the hash
    chain, and generate reports.
    """

    def __init__(self, config: dict, log_path: Optional[Path] = None) -> None:
        """Inicializa el motor con configuración de reglas y logging opcional.

        English:
            Initialize the engine with rule configuration and optional logging.
        """
        self.config = config
        self.log_path = log_path

    # ── helpers ──────────────────────────────────────────────────────────

    def _get_rule_config(self, rule: RuleDefinition) -> dict:
        """Obtiene la configuración específica de una regla con aliases.

        English:
            Get rule-specific config, resolving aliases when necessary.
        """
        rules_config = self.config.get("rules", {})
        rule_config = rules_config.get(rule.config_key)
        if rule_config is None:
            alias = RULE_CONFIG_ALIASES.get(rule.config_key)
            if alias:
                rule_config = rules_config.get(alias)
        return rule_config if rule_config is not None else {}

    def _rule_enabled(self, rule: RuleDefinition) -> bool:
        """Determina si una regla está habilitada según la configuración.

        Todas las reglas están habilitadas por defecto.

        English:
            Determine whether a rule is enabled based on configuration.

            All rules are enabled by default.
        """
        rules_config = self.config.get("rules", {})
        if not rules_config.get("global_enabled", True):
            return False
        return self._get_rule_config(rule).get("enabled", True)

    # ── hashchain verification ───────────────────────────────────────────

    @staticmethod
    def verify_hashchain(
        normalized_dir: Path, hashchain_path: Path
    ) -> list[dict]:
        """Verifica la integridad de la cadena de hashes de snapshots.

        English:
            Verify snapshot hash-chain integrity.
        """
        alerts: list[dict] = []
        try:
            entries = json.loads(hashchain_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return alerts

        previous_hash: Optional[str] = None
        for entry in entries:
            snapshot_name = entry.get("snapshot")
            if not snapshot_name:
                continue
            snapshot_path = normalized_dir / f"{snapshot_name}.json"
            if not snapshot_path.exists():
                alerts.append(
                    {
                        "type": "Hashchain Inconsistente",
                        "severity": "CRITICAL",
                        "snapshot": snapshot_name,
                        "justification": (
                            "Falta el snapshot esperado en el directorio normalizado. "
                            f"snapshot={snapshot_name}."
                        ),
                    }
                )
                previous_hash = entry.get("hash") or previous_hash
                continue
            canonical_json = snapshot_path.read_text(encoding="utf-8").strip()
            expected_previous = entry.get("previous_hash")
            if expected_previous != previous_hash:
                alerts.append(
                    {
                        "type": "Hashchain Inconsistente",
                        "severity": "CRITICAL",
                        "snapshot": snapshot_name,
                        "justification": (
                            "El hash previo no coincide con la cadena esperada. "
                            f"previo_esperado={expected_previous}, "
                            f"previo_calculado={previous_hash}."
                        ),
                    }
                )
            computed_hash = compute_hash(canonical_json, previous_hash)
            expected_hash = entry.get("hash")
            if expected_hash != computed_hash:
                alerts.append(
                    {
                        "type": "Tampering Retroactivo (Hashchain)",
                        "severity": "CRITICAL",
                        "snapshot": snapshot_name,
                        "justification": (
                            "El hash encadenado no coincide con el contenido canónico. "
                            f"hash_esperado={expected_hash}, hash_calculado={computed_hash}."
                        ),
                    }
                )
            previous_hash = expected_hash or previous_hash
        return alerts

    # ── report helpers ───────────────────────────────────────────────────

    @staticmethod
    def snapshot_hash(payload: dict) -> str:
        """Calcula el hash SHA-256 del snapshot canónico.

        English:
            Compute the canonical SHA-256 hash of a snapshot payload.
        """
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode(
            "utf-8"
        )
        return hashlib.sha256(canonical).hexdigest()

    @staticmethod
    def write_report(
        result: RulesEngineResult,
        snapshot_path: Path,
        snapshot_id: str,
        output_dir: Path,
    ) -> Path:
        """Escribe el reporte JSON de la ejecución de reglas.

        English:
            Write the JSON report for a rules-engine execution.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "snapshot": {
                "path": snapshot_path.as_posix(),
                "hash": snapshot_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "alerts": result.alerts,
            "critical_alerts": result.critical_alerts,
            "pause_snapshots": result.pause_snapshots,
        }
        report_path = output_dir / f"rules_report_{snapshot_path.stem}.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # Fichero auxiliar para consumidores ligeros.
        (output_dir.parent / "anomalies_report.json").write_text(
            json.dumps(result.alerts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return report_path

    # ── punto de entrada principal ───────────────────────────────────────

    def run(
        self,
        current_data: dict,
        previous_data: Optional[dict],
        snapshot_id: Optional[str] = None,
    ) -> RulesEngineResult:
        """Ejecuta todas las reglas registradas sobre el snapshot actual.

        Acumula alertas, destaca severidades críticas y puede pausar snapshots
        cuando existen alertas críticas.

        English:
            Run all registered rules against the current snapshot.

            Accumulates alerts, highlights critical severities, and can signal
            snapshot pause when critical alerts exist.
        """
        alerts: list[dict] = []
        critical_alerts: list[dict] = []

        for rule in list_rules():
            if not self._rule_enabled(rule):
                self._log_rule_event(
                    rule,
                    snapshot_id,
                    status="skipped",
                    alerts=[],
                )
                logger.debug(
                    "rule_skipped rule=%s snapshot_id=%s config_key=%s",
                    rule.name,
                    snapshot_id,
                    rule.config_key,
                )
                continue

            rule_config = self._get_rule_config(rule)
            try:
                rule_alerts = rule.func(current_data, previous_data, rule_config) or []
            except Exception as exc:  # noqa: BLE001
                self._log_rule_event(
                    rule,
                    snapshot_id,
                    status="error",
                    alerts=[],
                    error=str(exc),
                )
                logger.error(
                    "rule_error rule=%s snapshot_id=%s error=%s",
                    rule.name,
                    snapshot_id,
                    str(exc),
                )
                continue

            for alert in rule_alerts:
                alert.setdefault("rule", rule.name)
                alerts.append(alert)
                severity = str(alert.get("severity", "")).upper()
                if severity in {"CRITICAL", "HIGH"}:
                    critical_alerts.append(alert)

            self._log_rule_event(
                rule,
                snapshot_id,
                status="ok",
                alerts=rule_alerts,
            )
            if rule_alerts:
                logger.warning(
                    "rule_alerts rule=%s snapshot_id=%s alerts_count=%d",
                    rule.name,
                    snapshot_id,
                    len(rule_alerts),
                )
            else:
                logger.info(
                    "rule_ok rule=%s snapshot_id=%s",
                    rule.name,
                    snapshot_id,
                )

        return RulesEngineResult(
            alerts=alerts,
            critical_alerts=critical_alerts,
            pause_snapshots=bool(critical_alerts),
        )

    def _log_rule_event(
        self,
        rule: RuleDefinition,
        snapshot_id: Optional[str],
        status: str,
        alerts: list[dict],
        error: Optional[str] = None,
    ) -> None:
        """Registra en disco el resultado de ejecutar una regla.

        English:
            Persist the result of a rule execution to disk.
        """
        if not self.log_path:
            return
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rule": rule.name,
            "config_key": rule.config_key,
            "severity": rule.severity,
            "status": status,
            "snapshot_id": snapshot_id,
            "alerts_count": len(alerts),
            "alerts": [
                {
                    "severity": alert.get("severity"),
                    "message": alert.get("message"),
                    "value": alert.get("value"),
                    "threshold": alert.get("threshold"),
                    "result": alert.get("result"),
                    "justification": alert.get("justification"),
                }
                for alert in alerts
            ],
        }
        if error:
            event["error"] = error
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
