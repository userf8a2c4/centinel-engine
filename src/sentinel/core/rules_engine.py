"""Motor de reglas avanzadas para análisis estadístico de snapshots.

Advanced rules engine for statistical snapshot analysis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sentinel.core.rules import (
    benford_first_digit_rule,
    correlation_participation_vote_rule,
    geographic_dispersion_rule,
    last_digit_uniformity_rule,
    mesas_diff_rule,
    null_blank_rule,
    participation_anomaly_advanced_rule,
    runs_test_rule,
    snapshot_jump_rule,
    table_consistency_rule,
)
from sentinel.core.rules.registry import RuleDefinition, list_rules


@dataclass(frozen=True)
class RulesEngineResult:
    """Resultado agregado de la ejecución de reglas.

    Aggregated result from running rules.
    """

    alerts: list[dict]
    critical_alerts: list[dict]
    pause_snapshots: bool


class RulesEngine:
    """Ejecuta reglas avanzadas sobre snapshots actuales y previos.

    Runs advanced rules on current and previous snapshots.
    """

    def __init__(self, config: dict, log_path: Optional[Path] = None) -> None:
        self.config = config
        self.log_path = log_path

    def _rule_enabled(self, rule: RuleDefinition) -> bool:
        rules_config = self.config.get("rules", {})
        if not rules_config.get("global_enabled", True):
            return False
        rule_config = rules_config.get(rule.config_key, {})
        return rule_config.get("enabled", True)

    def run(
        self,
        current_data: dict,
        previous_data: Optional[dict],
        snapshot_id: Optional[str] = None,
    ) -> RulesEngineResult:
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
                continue

            rule_config = self.config.get("rules", {}).get(rule.config_key, {})
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
