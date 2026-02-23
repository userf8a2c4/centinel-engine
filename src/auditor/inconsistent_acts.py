"""Forensic tracking for inconsistent acts and special scrutiny votes.

Módulo de seguimiento forense para actas inconsistentes y votos de escrutinio especial.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path
from typing import Any

from scipy.stats import binomtest, chi2, norm


@dataclass
class SnapshotRecord:
    """Immutable per-cycle snapshot used by the tracker.

    Registro inmutable por ciclo utilizado por el rastreador.
    """

    timestamp: datetime
    inconsistent_count: int
    candidate_votes: dict[str, int]
    source_hash: str


@dataclass
class ChangeEvent:
    """State transition detected between two snapshots.

    Transición de estado detectada entre dos snapshots.
    """

    event_type: str
    delta_actas: int
    previous_inconsistent_count: int
    current_inconsistent_count: int
    delta_votos_por_candidato: dict[str, int]
    pct_por_candidato: dict[str, float]
    impacted_total_votes: int
    is_bulk_resolution: bool
    stagnation_cycles: int
    timestamp: datetime


@dataclass
class Anomaly:
    """Structured anomaly record for dashboards and reports.

    Registro estructurado de anomalía para paneles y reportes.
    """

    kind: str
    severity: str
    message: str
    timestamp: datetime
    metadata: dict[str, Any]


class InconsistentActsTracker:
    """Track, isolate, and audit votes entering via inconsistent-act resolutions.

    Rastrea, aísla y audita votos que ingresan por resoluciones de actas inconsistentes.
    """

    POSSIBLE_INCONSISTENT_KEYS = (
        "actasInconsistentes",
        "totalInconsistentes",
        "actasPendientes",
        "actasEnEscrutinioEspecial",
        "inconsistencias",
    )

    def __init__(
        self,
        *,
        config_path: str | Path = "config/inconsistent_key.json",
        bulk_resolution_threshold: int = 300,
        stagnation_cycles_threshold: int = 6,
        prolonged_stagnation_cycles: int = 12,
        high_impact_resolution_ratio: float = 0.10,
    ) -> None:
        """Initialize tracker with persistent key detection and thresholds.

        Inicializa el rastreador con detección persistente de clave y umbrales.
        """
        self.config_path = Path(config_path)
        self.bulk_resolution_threshold = bulk_resolution_threshold
        self.stagnation_cycles_threshold = stagnation_cycles_threshold
        self.prolonged_stagnation_cycles = prolonged_stagnation_cycles
        self.high_impact_resolution_ratio = high_impact_resolution_ratio

        self.detected_inconsistent_key = self._load_persisted_key()
        self.snapshots: list[SnapshotRecord] = []
        self.events: list[ChangeEvent] = []
        self.normal_votes: dict[str, int] = {}
        self.special_scrutiny_votes: dict[str, int] = {}
        self.stagnation_cycles = 0

    def load_snapshot(self, json_data: dict, timestamp: datetime) -> None:
        """Load one JSON snapshot and classify vote deltas by layer.

        Carga un snapshot JSON y clasifica deltas de voto por capa.
        """
        if self.detected_inconsistent_key is None:
            self.detected_inconsistent_key = self._detect_inconsistent_key(json_data)
            self._persist_key(self.detected_inconsistent_key)

        inconsistent_count = self._extract_inconsistent_count(json_data, self.detected_inconsistent_key)
        candidate_votes = self._extract_candidate_votes(json_data)
        source_hash = hashlib.sha256(
            json.dumps(json_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        snapshot = SnapshotRecord(
            timestamp=timestamp,
            inconsistent_count=inconsistent_count,
            candidate_votes=candidate_votes,
            source_hash=source_hash,
        )

        if not self.snapshots:
            self.snapshots.append(snapshot)
            return

        previous = self.snapshots[-1]
        self.snapshots.append(snapshot)
        change = self.analyze_change(previous)

        # English/Español: classify votes strictly on the resolution boundary / clasificar votos estrictamente en la frontera de resolución.
        if change.delta_actas > 0:
            for candidate, delta in change.delta_votos_por_candidato.items():
                self.special_scrutiny_votes[candidate] = self.special_scrutiny_votes.get(candidate, 0) + delta
        else:
            for candidate, delta in change.delta_votos_por_candidato.items():
                self.normal_votes[candidate] = self.normal_votes.get(candidate, 0) + delta

        self.events.append(change)

    def analyze_change(self, previous_snapshot: SnapshotRecord | dict[str, Any]) -> ChangeEvent:
        """Analyze delta between previous snapshot and latest loaded snapshot.

        Analiza el delta entre snapshot previo y el último cargado.
        """
        if not self.snapshots:
            raise ValueError("No snapshot loaded to analyze changes against.")

        current = self.snapshots[-1]
        previous = previous_snapshot if isinstance(previous_snapshot, SnapshotRecord) else SnapshotRecord(**previous_snapshot)

        previous_count = int(previous.inconsistent_count)
        current_count = int(current.inconsistent_count)
        delta_actas = max(previous_count - current_count, 0)

        candidate_deltas = self._candidate_deltas(previous.candidate_votes, current.candidate_votes)
        total_delta = sum(candidate_deltas.values())
        pct_by_candidate = {
            candidate: ((delta / total_delta) * 100.0 if total_delta > 0 else 0.0)
            for candidate, delta in candidate_deltas.items()
        }

        if current_count == previous_count:
            self.stagnation_cycles += 1
            if self.stagnation_cycles >= self.stagnation_cycles_threshold:
                event_type = "stagnation"
            else:
                event_type = "no_change"
        else:
            self.stagnation_cycles = 0
            event_type = "resolution" if delta_actas > 0 else "non_resolution_change"

        is_bulk = delta_actas >= self.bulk_resolution_threshold
        if is_bulk:
            event_type = "bulk_resolution"

        return ChangeEvent(
            event_type=event_type,
            delta_actas=delta_actas,
            previous_inconsistent_count=previous_count,
            current_inconsistent_count=current_count,
            delta_votos_por_candidato=candidate_deltas,
            pct_por_candidato=pct_by_candidate,
            impacted_total_votes=total_delta,
            is_bulk_resolution=is_bulk,
            stagnation_cycles=self.stagnation_cycles,
            timestamp=current.timestamp,
        )

    def get_special_scrutiny_cumulative(self) -> dict:
        """Return cumulative votes attributed to special scrutiny only.

        Devuelve votos acumulados atribuidos solo al escrutinio especial.
        """
        total = sum(self.special_scrutiny_votes.values())
        return {
            "inconsistent_key": self.detected_inconsistent_key,
            "total_special_scrutiny_votes": total,
            "votes_by_candidate": dict(sorted(self.special_scrutiny_votes.items())),
        }

    def run_statistical_tests(self) -> dict:
        """Run publication-grade statistical checks for special scrutiny votes.

        Ejecuta pruebas estadísticas de nivel publicación para votos especiales.
        """
        special_total = sum(self.special_scrutiny_votes.values())
        normal_total = sum(self.normal_votes.values())
        national_total = special_total + normal_total

        if special_total == 0 or national_total == 0:
            return {"status": "insufficient_data", "special_total": special_total, "normal_total": normal_total}

        special_props = self._proportions(self.special_scrutiny_votes)
        normal_props = self._proportions(self.normal_votes)
        national_props = self._proportions(self._merge_votes(self.special_scrutiny_votes, self.normal_votes))

        chi_stat = 0.0
        for candidate, observed in self.special_scrutiny_votes.items():
            expected = special_total * national_props.get(candidate, 0.0)
            if expected > 0:
                chi_stat += (observed - expected) ** 2 / expected
        dof = max(len(self.special_scrutiny_votes) - 1, 1)
        chi_pvalue = float(chi2.sf(chi_stat, dof))

        per_candidate_tests: dict[str, Any] = {}
        raw_pvalues: list[float] = []
        for candidate, special_votes in self.special_scrutiny_votes.items():
            p0 = national_props.get(candidate, 0.0)
            if p0 <= 0:
                continue
            bt = binomtest(k=special_votes, n=special_total, p=p0)
            normal_candidate_votes = self.normal_votes.get(candidate, 0)
            p1 = special_votes / special_total
            p2 = normal_candidate_votes / normal_total if normal_total > 0 else 0.0
            p_pool = (special_votes + normal_candidate_votes) / (special_total + normal_total)
            denom = sqrt(max(p_pool * (1 - p_pool) * ((1 / special_total) + (1 / max(normal_total, 1))), 1e-12))
            z_score = (p1 - p2) / denom if denom else 0.0
            z_pvalue = 2 * (1 - norm.cdf(abs(z_score)))

            ci = self._proportion_confidence_interval(p1, special_total)
            power = self._approx_power_two_proportion(p1, p2, special_total, max(normal_total, 1))
            raw_pvalues.append(bt.pvalue)

            per_candidate_tests[candidate] = {
                "binomial_exact_pvalue": bt.pvalue,
                "z_score_diff_proportions": z_score,
                "z_test_pvalue": z_pvalue,
                "special_proportion": p1,
                "normal_proportion": p2,
                "ci95_special": ci,
                "power_estimate": power,
            }

        m = max(len(raw_pvalues), 1)
        for candidate, test in per_candidate_tests.items():
            test["bonferroni_adjusted_pvalue"] = min(test["binomial_exact_pvalue"] * m, 1.0)

        trend = self._special_time_series_trend()
        return {
            "status": "ok",
            "totals": {
                "special_total": special_total,
                "normal_total": normal_total,
                "national_total": national_total,
            },
            "proportions": {
                "special": special_props,
                "normal": normal_props,
                "national": national_props,
            },
            "chi_square_goodness_of_fit": {
                "statistic": chi_stat,
                "dof": dof,
                "pvalue": chi_pvalue,
            },
            "per_candidate": per_candidate_tests,
            "special_time_series_linear_trend": trend,
        }

    def detect_anomalies(self) -> list[Anomaly]:
        """Detect high-severity forensic anomalies over events and vote deltas.

        Detecta anomalías forenses de alta severidad sobre eventos y deltas de voto.
        """
        anomalies: list[Anomaly] = []
        special_deltas = [event.impacted_total_votes for event in self.events if event.delta_actas > 0]

        if len(special_deltas) >= 2:
            mean_delta = sum(special_deltas) / len(special_deltas)
            variance = sum((value - mean_delta) ** 2 for value in special_deltas) / len(special_deltas)
            sigma = sqrt(variance)
            threshold = mean_delta + (3 * sigma)
            for event in self.events:
                if event.delta_actas > 0 and event.impacted_total_votes > threshold:
                    anomalies.append(
                        Anomaly(
                            kind="vote_outlier_3sigma",
                            severity="critical",
                            message="Special scrutiny vote delta exceeds 3σ threshold.",
                            timestamp=event.timestamp,
                            metadata={"delta_votes": event.impacted_total_votes, "threshold": threshold},
                        )
                    )

        for event in self.events:
            if event.delta_actas > 0:
                prev = max(event.previous_inconsistent_count, 1)
                ratio = event.delta_actas / prev
                if ratio >= self.high_impact_resolution_ratio:
                    anomalies.append(
                        Anomaly(
                            kind="high_impact_resolution",
                            severity="critical",
                            message="Resolution exceeded 10% of pending inconsistent acts in one cycle.",
                            timestamp=event.timestamp,
                            metadata={"ratio": ratio, "delta_actas": event.delta_actas},
                        )
                    )
            if event.is_bulk_resolution:
                anomalies.append(
                    Anomaly(
                        kind="bulk_resolution",
                        severity="critical",
                        message="Bulk resolution threshold reached.",
                        timestamp=event.timestamp,
                        metadata={"delta_actas": event.delta_actas},
                    )
                )
            if event.stagnation_cycles >= self.prolonged_stagnation_cycles:
                anomalies.append(
                    Anomaly(
                        kind="prolonged_stagnation",
                        severity="warning",
                        message="Inconsistent count stagnated for over 1 hour.",
                        timestamp=event.timestamp,
                        metadata={"stagnation_cycles": event.stagnation_cycles},
                    )
                )

        stats = self.run_statistical_tests()
        if stats.get("status") == "ok":
            for candidate, payload in stats.get("per_candidate", {}).items():
                if payload.get("bonferroni_adjusted_pvalue", 1.0) < 0.01:
                    anomalies.append(
                        Anomaly(
                            kind="statistical_bias",
                            severity="critical",
                            message=f"Statistically significant bias detected for {candidate} (p<0.01).",
                            timestamp=self.snapshots[-1].timestamp if self.snapshots else datetime.now(timezone.utc),
                            metadata={
                                "candidate": candidate,
                                "adjusted_pvalue": payload["bonferroni_adjusted_pvalue"],
                                "z_score": payload["z_score_diff_proportions"],
                            },
                        )
                    )

        return anomalies

    def generate_forensic_report(self) -> str:
        """Generate markdown+LaTeX forensic report with source JSON hashes.

        Genera reporte forense markdown+LaTeX con hashes de JSON de origen.
        """
        stats = self.run_statistical_tests()
        anomalies = self.detect_anomalies()
        generated_at = datetime.now(timezone.utc).isoformat()

        hashes = "\n".join(f"- `{snapshot.timestamp.isoformat()}`: `{snapshot.source_hash}`" for snapshot in self.snapshots)

        latex_block = r"""
\[
z = \frac{\hat{p}_{special} - \hat{p}_{normal}}{\sqrt{\hat{p}(1-\hat{p})(\frac{1}{n_{special}}+\frac{1}{n_{normal}})}}
\]
\[
\chi^2 = \sum_i \frac{(O_i - E_i)^2}{E_i}, \quad E_i = n_{special}\,p_{national,i}
\]
""".strip()

        return (
            f"# Forensic Report: Inconsistent Acts / Reporte Forense: Actas Inconsistentes\n\n"
            f"Generated at / Generado en: `{generated_at}`\n\n"
            f"## Detected key / Clave detectada\n"
            f"- `{self.detected_inconsistent_key}`\n\n"
            f"## Special scrutiny cumulative / Acumulado escrutinio especial\n"
            f"- `{json.dumps(self.get_special_scrutiny_cumulative(), ensure_ascii=False)}`\n\n"
            f"## Statistical tests / Pruebas estadísticas\n"
            f"```json\n{json.dumps(stats, indent=2, ensure_ascii=False)}\n```\n\n"
            f"## Anomalies / Anomalías\n"
            f"```json\n{json.dumps([asdict(anomaly) for anomaly in anomalies], indent=2, default=str, ensure_ascii=False)}\n```\n\n"
            f"## Equations / Ecuaciones\n{latex_block}\n\n"
            f"## Source hashes SHA-256 / Hashes de fuente SHA-256\n{hashes}\n"
        )

    def _load_persisted_key(self) -> str | None:
        """Load previously detected key from config file.

        Carga la clave detectada previamente desde archivo de configuración.
        """
        if not self.config_path.exists():
            return None
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        key = payload.get("inconsistent_key")
        return key if isinstance(key, str) else None

    def _persist_key(self, key: str | None) -> None:
        """Persist detected inconsistent key for reproducible runs.

        Persiste la clave inconsistente detectada para ejecuciones reproducibles.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"inconsistent_key": key, "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2),
            encoding="utf-8",
        )

    def _detect_inconsistent_key(self, json_data: dict) -> str:
        """Detect the inconsistent-count key from one snapshot recursively.

        Detecta la clave de conteo inconsistente desde un snapshot recursivamente.
        """
        flattened = self._flatten_numeric_fields(json_data)
        candidates: list[str] = []
        for key in flattened:
            lowered = key.lower()
            if any(token.lower() in lowered for token in self.POSSIBLE_INCONSISTENT_KEYS):
                candidates.append(key)
            elif "incons" in lowered or "escrutinio" in lowered or "pend" in lowered:
                candidates.append(key)
        if not candidates:
            raise ValueError("Unable to detect inconsistent acts key in JSON payload.")
        candidates.sort(key=lambda name: ("actas" not in name.lower(), len(name), name))
        return candidates[0]

    def _extract_inconsistent_count(self, json_data: dict, key_path: str) -> int:
        """Extract integer inconsistent count from dotted key path.

        Extrae conteo entero de inconsistentes desde ruta de clave con puntos.
        """
        value: Any = json_data
        for token in key_path.split("."):
            if token.isdigit():
                value = value[int(token)]
            else:
                value = value[token]
        return int(value)

    def _extract_candidate_votes(self, json_data: dict) -> dict[str, int]:
        """Extract candidate votes from flexible CNE-like structures.

        Extrae votos de candidatos desde estructuras flexibles tipo CNE.
        """
        candidates = self._find_candidates_container(json_data)
        votes: dict[str, int] = {}
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            # English/Español: stable neutral identifier without party semantics / identificador neutral estable sin semántica partidaria.
            name = str(
                candidate.get("candidate_id")
                or candidate.get("id")
                or candidate.get("name")
                or candidate.get("nombre")
                or candidate.get("slot")
                or "unknown"
            )
            vote_value = int(candidate.get("votes") or candidate.get("votos") or 0)
            votes[name] = vote_value
        return votes

    def _find_candidates_container(self, payload: Any) -> list[dict[str, Any]]:
        """Find candidate list recursively for multiple snapshot schemas.

        Encuentra lista de candidatos recursivamente para múltiples esquemas.
        """
        if isinstance(payload, dict):
            for key, value in payload.items():
                lowered = key.lower()
                if lowered in {"candidates", "candidatos"} and isinstance(value, list):
                    return value
                found = self._find_candidates_container(value)
                if found:
                    return found
        elif isinstance(payload, list):
            for item in payload:
                found = self._find_candidates_container(item)
                if found:
                    return found
        return []

    def _flatten_numeric_fields(self, payload: Any, prefix: str = "") -> dict[str, int]:
        """Flatten numeric fields for key detection.

        Aplana campos numéricos para detección de claves.
        """
        result: dict[str, int] = {}
        if isinstance(payload, dict):
            for key, value in payload.items():
                path = f"{prefix}.{key}" if prefix else key
                result.update(self._flatten_numeric_fields(value, path))
        elif isinstance(payload, list):
            for index, item in enumerate(payload):
                path = f"{prefix}.{index}" if prefix else str(index)
                result.update(self._flatten_numeric_fields(item, path))
        elif isinstance(payload, (int, float)):
            result[prefix] = int(payload)
        return result

    def _candidate_deltas(self, previous: dict[str, int], current: dict[str, int]) -> dict[str, int]:
        """Compute per-candidate vote deltas.

        Calcula deltas de votos por candidato.
        """
        all_candidates = sorted(set(previous) | set(current))
        return {candidate: current.get(candidate, 0) - previous.get(candidate, 0) for candidate in all_candidates}

    def _proportions(self, votes_by_candidate: dict[str, int]) -> dict[str, float]:
        """Compute proportions safely from vote dictionary.

        Calcula proporciones de forma segura desde diccionario de votos.
        """
        total = sum(votes_by_candidate.values())
        if total <= 0:
            return {candidate: 0.0 for candidate in votes_by_candidate}
        return {candidate: votes / total for candidate, votes in votes_by_candidate.items()}

    def _merge_votes(self, a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
        """Merge vote dictionaries by candidate with integer sums.

        Fusiona diccionarios de votos por candidato con sumas enteras.
        """
        merged = dict(a)
        for candidate, votes in b.items():
            merged[candidate] = merged.get(candidate, 0) + votes
        return merged

    def _proportion_confidence_interval(self, p: float, n: int) -> dict[str, float]:
        """Compute normal-approximation 95% confidence interval.

        Calcula intervalo de confianza 95% por aproximación normal.
        """
        if n <= 0:
            return {"low": 0.0, "high": 0.0}
        z = 1.96
        margin = z * sqrt(max(p * (1 - p) / n, 0.0))
        return {"low": max(p - margin, 0.0), "high": min(p + margin, 1.0)}

    def _approx_power_two_proportion(self, p1: float, p2: float, n1: int, n2: int, alpha: float = 0.05) -> float:
        """Approximate power for two-proportion z test.

        Aproxima potencia para prueba z de dos proporciones.
        """
        diff = abs(p1 - p2)
        if diff == 0:
            return 0.0
        se = sqrt(max((p1 * (1 - p1) / n1) + (p2 * (1 - p2) / n2), 1e-12))
        z_alpha = norm.ppf(1 - alpha / 2)
        z_effect = diff / se
        return float(max(min(1 - norm.cdf(z_alpha - z_effect), 1.0), 0.0))

    def _special_time_series_trend(self) -> dict[str, float]:
        """Compute linear trend over special-scrutiny vote deltas per event.

        Calcula tendencia lineal sobre deltas por evento de escrutinio especial.
        """
        y_values = [event.impacted_total_votes for event in self.events if event.delta_actas > 0]
        n = len(y_values)
        if n < 2:
            return {"slope": 0.0, "intercept": y_values[0] if y_values else 0.0, "r2": 0.0}
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        den = sum((x - x_mean) ** 2 for x in x_values)
        slope = num / den if den else 0.0
        intercept = y_mean - slope * x_mean
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))
        r2 = 1 - (ss_res / ss_tot) if ss_tot else 0.0
        return {"slope": slope, "intercept": intercept, "r2": r2}
