"""Forensic tracking for inconsistent acts and special scrutiny votes.

Módulo de seguimiento forense para actas inconsistentes y votos de escrutinio especial.

Capacidades forenses / Forensic capabilities:
- Separación de votos normales vs escrutinio especial
- Detección de inyección progresiva controlada
- Velocidad de resolución anómala (actas/minuto)
- Distribución asimétrica en resoluciones (sesgo hacia un candidato)
- Patrón hold-and-release (estancamiento → resolución masiva)
- Benford's Law sobre votos de escrutinio especial
- Detección de apagón comunicacional con cambio de tendencia
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from math import log10, sqrt
from pathlib import Path
from typing import Any

from scipy.stats import binomtest, chi2, chisquare, norm


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

    # Resolución manual realista: ~2 actas/minuto por mesa de escrutinio.
    # Un valor superior indica procesamiento automatizado o irregular.
    DEFAULT_MAX_RESOLUTION_RATE = 10.0  # actas por minuto

    # Umbral de gap temporal para considerar un apagón comunicacional.
    DEFAULT_BLACKOUT_GAP_MINUTES = 30

    def __init__(
        self,
        *,
        config_path: str | Path = "config/inconsistent_key.json",
        runtime_config_path: str | Path = "config.json",
        bulk_resolution_threshold: int = 300,
        stagnation_cycles_threshold: int = 6,
        prolonged_stagnation_cycles: int = 12,
        high_impact_resolution_ratio: float = 0.10,
        progressive_injection_threshold: int = 800,
        min_consecutive_injections: int = 5,
        high_inconsistent_threshold: int = 1000,
        run_test_pvalue_threshold: float = 0.05,
        max_resolution_rate: float | None = None,
        blackout_gap_minutes: int | None = None,
    ) -> None:
        """Initialize tracker with persistent key detection and thresholds.

        Inicializa el rastreador con detección persistente de clave y umbrales.
        """
        self.config_path = Path(config_path)
        self.runtime_config_path = Path(runtime_config_path)
        runtime_config = self._load_runtime_config()
        self.bulk_resolution_threshold = bulk_resolution_threshold
        self.stagnation_cycles_threshold = stagnation_cycles_threshold
        self.prolonged_stagnation_cycles = prolonged_stagnation_cycles
        self.high_impact_resolution_ratio = high_impact_resolution_ratio
        self.progressive_injection_threshold = int(
            runtime_config.get("progressive_injection_threshold", progressive_injection_threshold)
        )
        self.min_consecutive_injections = int(
            runtime_config.get("min_consecutive_injections", min_consecutive_injections)
        )
        self.high_inconsistent_threshold = int(runtime_config.get("high_inconsistent_threshold", high_inconsistent_threshold))
        self.run_test_pvalue_threshold = float(runtime_config.get("run_test_pvalue_threshold", run_test_pvalue_threshold))
        self.max_resolution_rate = float(
            runtime_config.get("max_resolution_rate", max_resolution_rate or self.DEFAULT_MAX_RESOLUTION_RATE)
        )
        self.blackout_gap_minutes = int(
            runtime_config.get("blackout_gap_minutes", blackout_gap_minutes or self.DEFAULT_BLACKOUT_GAP_MINUTES)
        )

        self.detected_inconsistent_key = self._load_persisted_key()
        self.snapshots: list[SnapshotRecord] = []
        self.events: list[ChangeEvent] = []
        self.normal_votes: dict[str, int] = {}
        self.special_scrutiny_votes: dict[str, int] = {}
        self.stagnation_cycles = 0
        self.injection_history: list[dict[str, Any]] = []
        self.realtime_alerts: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

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

        delta_total = change.impacted_total_votes
        if inconsistent_count > self.high_inconsistent_threshold and delta_total < self.progressive_injection_threshold:
            # English/Español: track low-delta injection while inconsistent acts remain high / registrar inyección de delta bajo con AI altas.
            self.injection_history.append(
                {
                    "timestamp": snapshot.timestamp,
                    "delta_total": delta_total,
                    "delta_por_candidato": change.delta_votos_por_candidato,
                    "inconsistent_count_en_ese_momento": inconsistent_count,
                }
            )

            if len(self.injection_history) >= self.min_consecutive_injections:
                progressive = self.detect_progressive_injection()
                if progressive and progressive.get("detected"):
                    self.logger.critical(progressive["description"])
                    self.realtime_alerts.append(progressive)
        else:
            # English/Español: only consecutive windows count / solo cuentan ventanas consecutivas.
            self.injection_history.clear()

    def detect_progressive_injection(self) -> dict[str, Any] | None:
        """Detect sustained low-delta injections under high inconsistency backlog.

        Detecta inyecciones sostenidas de bajo delta bajo una alta cola de inconsistencias.
        """
        if len(self.injection_history) < self.min_consecutive_injections:
            return None

        candidate_net: dict[str, int] = {}
        deltas = [float(item["delta_total"]) for item in self.injection_history]
        for item in self.injection_history:
            for candidate, delta in item["delta_por_candidato"].items():
                candidate_net[candidate] = candidate_net.get(candidate, 0) + int(delta)

        stats = self.run_injection_statistical_tests(deltas)
        statistically_unlikely = bool(
            stats["improbable"] or stats["autocorrelation_lag1"] > 0.5 or stats["run_test_pvalue"] < self.run_test_pvalue_threshold
        )
        detection = {
            "detected": statistically_unlikely,
            "start_timestamp": self.injection_history[0]["timestamp"],
            "end_timestamp": self.injection_history[-1]["timestamp"],
            "cycles_count": len(self.injection_history),
            "avg_delta_per_cycle": sum(deltas) / len(deltas),
            "net_swing": candidate_net,
            "z_score_acumulado": stats["z_score_acumulado"],
            "z_score_pvalue": stats["z_score_pvalue"],
            "run_test_pvalue": stats["run_test_pvalue"],
            "autocorrelation_lag1": stats["autocorrelation_lag1"],
            "description": (
                "Patrón de inyección progresiva detectado: "
                f"{len(self.injection_history)} ciclos consecutivos con delta <{self.progressive_injection_threshold} "
                f"mientras AI >{self.high_inconsistent_threshold}"
            ),
        }
        return detection if detection["detected"] else None

    def run_injection_statistical_tests(self, deltas: list[float]) -> dict[str, float | bool]:
        """Run improbability tests over progressive injection deltas.

        Ejecuta pruebas de improbabilidad sobre deltas de inyección progresiva.
        """
        if not deltas:
            return {
                "z_score_acumulado": 0.0,
                "z_score_pvalue": 1.0,
                "run_test_pvalue": 1.0,
                "autocorrelation_lag1": 0.0,
                "variance": 0.0,
                "improbable": False,
            }

        historical = [float(event.impacted_total_votes) for event in self.events if event.impacted_total_votes > 0]
        baseline = historical[:-len(deltas)] if len(historical) > len(deltas) else historical
        if len(baseline) < 2:
            baseline = deltas

        baseline_mean = sum(baseline) / len(baseline)
        baseline_var = sum((value - baseline_mean) ** 2 for value in baseline) / max(len(baseline) - 1, 1)
        baseline_sigma = sqrt(max(baseline_var, 1e-9))

        # English/Español: cumulative z-score against dynamic baseline / z-score acumulado contra línea base dinámica.
        observed_sum = sum(deltas)
        expected_sum = baseline_mean * len(deltas)
        z_score = (observed_sum - expected_sum) / (baseline_sigma * sqrt(len(deltas)))
        z_pvalue = float(2 * (1 - norm.cdf(abs(z_score))))

        run_pvalue = self._runs_test_pvalue(deltas)
        autocorr = self._autocorrelation_lag1(deltas)
        deltas_variance = sum((value - (sum(deltas) / len(deltas))) ** 2 for value in deltas) / max(len(deltas) - 1, 1)
        # English/Español: near-zero variance in consecutive micro-deltas is itself non-random / varianza casi cero en micro-deltas consecutivos ya es no aleatoria.
        improbable = bool(
            z_pvalue < 0.01 or run_pvalue < self.run_test_pvalue_threshold or (len(deltas) >= self.min_consecutive_injections and deltas_variance < 1.0)
        )

        return {
            "z_score_acumulado": float(z_score),
            "z_score_pvalue": z_pvalue,
            "run_test_pvalue": run_pvalue,
            "autocorrelation_lag1": autocorr,
            "variance": float(deltas_variance),
            "improbable": improbable,
        }

    def detect_resolution_velocity_anomalies(self) -> list[dict[str, Any]]:
        """Detect resolutions that exceed the maximum plausible rate (actas/minute).

        Detecta resoluciones que exceden la tasa máxima plausible (actas/minuto).
        Un comité de escrutinio especial revisa cada acta manualmente: lectura de votos,
        verificación de firmas, cotejo con copias de partidos. Tasas superiores a
        ~2-3 actas/minuto por mesa son físicamente implausibles para un proceso humano.
        """
        anomalies: list[dict[str, Any]] = []
        for i in range(1, len(self.snapshots)):
            prev = self.snapshots[i - 1]
            curr = self.snapshots[i]
            delta_actas = max(prev.inconsistent_count - curr.inconsistent_count, 0)
            if delta_actas == 0:
                continue
            elapsed_seconds = (curr.timestamp - prev.timestamp).total_seconds()
            if elapsed_seconds <= 0:
                continue
            elapsed_minutes = elapsed_seconds / 60.0
            rate = delta_actas / elapsed_minutes
            if rate > self.max_resolution_rate:
                anomalies.append({
                    "timestamp": curr.timestamp,
                    "delta_actas": delta_actas,
                    "elapsed_minutes": round(elapsed_minutes, 2),
                    "rate_per_minute": round(rate, 2),
                    "threshold": self.max_resolution_rate,
                    "description": (
                        f"Velocidad de resolución anómala: {rate:.1f} actas/min "
                        f"({delta_actas} actas en {elapsed_minutes:.1f} min). "
                        f"Umbral plausible: {self.max_resolution_rate} actas/min."
                    ),
                })
        return anomalies

    def detect_asymmetric_benefit(self) -> dict[str, Any] | None:
        """Detect disproportionate benefit to one candidate in special scrutiny.

        Detecta beneficio desproporcionado a un candidato en escrutinio especial.
        Compara la distribución de votos en actas de escrutinio especial contra
        la distribución en actas normales. Si un candidato recibe un porcentaje
        significativamente mayor en escrutinio especial, esto indica sesgo dirigido.
        """
        if not self.special_scrutiny_votes or not self.normal_votes:
            return None

        special_total = sum(self.special_scrutiny_votes.values())
        normal_total = sum(self.normal_votes.values())
        if special_total == 0 or normal_total == 0:
            return None

        special_props = self._proportions(self.special_scrutiny_votes)
        normal_props = self._proportions(self.normal_votes)

        max_swing_candidate = None
        max_swing = 0.0
        swings: dict[str, float] = {}

        for candidate in sorted(set(special_props) | set(normal_props)):
            sp = special_props.get(candidate, 0.0)
            np_ = normal_props.get(candidate, 0.0)
            swing = sp - np_
            swings[candidate] = swing
            if swing > max_swing:
                max_swing = swing
                max_swing_candidate = candidate

        if max_swing_candidate is None or max_swing < 0.02:
            return None

        beneficiary_special = self.special_scrutiny_votes.get(max_swing_candidate, 0)
        beneficiary_normal = self.normal_votes.get(max_swing_candidate, 0)
        p_special = beneficiary_special / special_total
        p_normal = beneficiary_normal / normal_total
        p_pool = (beneficiary_special + beneficiary_normal) / (special_total + normal_total)
        denom = sqrt(max(p_pool * (1 - p_pool) * ((1 / special_total) + (1 / normal_total)), 1e-12))
        z_score = (p_special - p_normal) / denom if denom else 0.0
        z_pvalue = float(2 * (1 - norm.cdf(abs(z_score))))

        extra_votes = int(max_swing * special_total)

        return {
            "beneficiary": max_swing_candidate,
            "swing_pp": round(max_swing * 100, 2),
            "special_proportion": round(p_special * 100, 2),
            "normal_proportion": round(p_normal * 100, 2),
            "z_score": round(z_score, 3),
            "z_pvalue": z_pvalue,
            "estimated_extra_votes": extra_votes,
            "all_swings_pp": {c: round(s * 100, 2) for c, s in sorted(swings.items())},
            "significant": z_pvalue < 0.01,
            "description": (
                f"Beneficio asimétrico detectado: {max_swing_candidate} recibe "
                f"{p_special:.1%} en escrutinio especial vs {p_normal:.1%} en normal "
                f"(+{max_swing:.1%} pp, z={z_score:+.3f}, p={z_pvalue:.5f}). "
                f"Votos extra estimados: ~{extra_votes:,}."
            ),
        }

    def detect_hold_and_release(self) -> list[dict[str, Any]]:
        """Detect hold-and-release patterns: stagnation followed by bulk resolution.

        Detecta patrones retener-y-soltar: estancamiento seguido de resolución masiva.
        Este patrón es indicativo de manipulación coordinada: se detiene el procesamiento
        de actas inconsistentes (hold) y luego se liberan muchas a la vez (release),
        típicamente en horarios de baja vigilancia o durante apagones comunicacionales.
        """
        patterns: list[dict[str, Any]] = []
        if len(self.events) < 2:
            return patterns

        stagnation_start: int | None = None
        stagnation_count = 0

        for i, event in enumerate(self.events):
            if event.event_type in ("stagnation", "no_change"):
                if stagnation_start is None:
                    stagnation_start = i
                stagnation_count += 1
            else:
                if (
                    stagnation_count >= self.stagnation_cycles_threshold
                    and event.delta_actas > 0
                    and event.is_bulk_resolution
                ):
                    stag_start_ts = self.events[stagnation_start].timestamp if stagnation_start is not None else event.timestamp
                    patterns.append({
                        "stagnation_start": stag_start_ts,
                        "stagnation_cycles": stagnation_count,
                        "release_timestamp": event.timestamp,
                        "released_actas": event.delta_actas,
                        "released_votes": event.impacted_total_votes,
                        "vote_distribution": dict(event.pct_por_candidato),
                        "description": (
                            f"Patrón hold-and-release: {stagnation_count} ciclos de estancamiento "
                            f"seguidos de resolución masiva de {event.delta_actas} actas "
                            f"({event.impacted_total_votes} votos) en {event.timestamp}."
                        ),
                    })
                stagnation_start = None
                stagnation_count = 0

        return patterns

    def detect_benford_special_scrutiny(self) -> dict[str, Any] | None:
        """Apply Benford's Law to vote counts from special scrutiny resolutions.

        Aplica la Ley de Benford a conteos de votos de resoluciones de escrutinio especial.
        Los datos electorales reales siguen la distribución de Benford para el primer
        dígito. Datos fabricados o manipulados tienden a desviarse significativamente.
        """
        resolution_vote_deltas: list[int] = []
        for event in self.events:
            if event.delta_actas > 0:
                for delta in event.delta_votos_por_candidato.values():
                    if delta > 0:
                        resolution_vote_deltas.append(delta)

        if len(resolution_vote_deltas) < 10:
            return None

        digits: list[int] = []
        for value in resolution_vote_deltas:
            if value > 0:
                digits.append(int(str(abs(value))[0]))

        if len(digits) < 10:
            return None

        observed = [0] * 9
        for d in digits:
            observed[d - 1] += 1

        n = len(digits)
        expected = [n * log10(1 + 1 / d) for d in range(1, 10)]

        chi_result = chisquare(observed, f_exp=expected)

        digit_table: dict[int, dict[str, float]] = {}
        for d in range(1, 10):
            obs_pct = observed[d - 1] / n * 100
            exp_pct = expected[d - 1] / n * 100
            digit_table[d] = {
                "observed_pct": round(obs_pct, 2),
                "expected_pct": round(exp_pct, 2),
                "deviation_pp": round(obs_pct - exp_pct, 2),
            }

        return {
            "n_samples": n,
            "chi2_statistic": round(float(chi_result.statistic), 4),
            "chi2_pvalue": float(chi_result.pvalue),
            "significant": bool(chi_result.pvalue < 0.05),
            "digit_analysis": digit_table,
            "description": (
                f"Benford's Law test sobre {n} deltas de votos en escrutinio especial: "
                f"χ²={chi_result.statistic:.4f}, p={chi_result.pvalue:.5f}. "
                + ("Desviación significativa detectada." if chi_result.pvalue < 0.05 else "Sin desviación significativa.")
            ),
        }

    def detect_blackout_windows(self) -> list[dict[str, Any]]:
        """Detect communication blackout windows followed by trend shifts.

        Detecta ventanas de apagón comunicacional seguidas de cambios de tendencia.
        Un apagón es un gap temporal inusualmente largo entre snapshots consecutivos.
        Si después del gap la tendencia de un candidato cambia significativamente,
        esto indica que durante el apagón se alteraron datos.
        """
        blackouts: list[dict[str, Any]] = []
        if len(self.snapshots) < 2:
            return blackouts

        gap_threshold = timedelta(minutes=self.blackout_gap_minutes)

        for i in range(1, len(self.snapshots)):
            prev = self.snapshots[i - 1]
            curr = self.snapshots[i]
            gap = curr.timestamp - prev.timestamp

            if gap < gap_threshold:
                continue

            # Calcular proporciones antes y después del gap.
            pre_total = sum(prev.candidate_votes.values())
            post_total = sum(curr.candidate_votes.values())
            if pre_total == 0 or post_total == 0:
                continue

            pre_props = {c: v / pre_total for c, v in prev.candidate_votes.items()}
            post_props = {c: v / post_total for c, v in curr.candidate_votes.items()}

            trend_shifts: dict[str, float] = {}
            for candidate in sorted(set(pre_props) | set(post_props)):
                shift = post_props.get(candidate, 0.0) - pre_props.get(candidate, 0.0)
                if abs(shift) > 0.005:
                    trend_shifts[candidate] = round(shift * 100, 3)

            delta_inconsistent = prev.inconsistent_count - curr.inconsistent_count
            delta_votes = {
                c: curr.candidate_votes.get(c, 0) - prev.candidate_votes.get(c, 0)
                for c in sorted(set(prev.candidate_votes) | set(curr.candidate_votes))
            }

            blackouts.append({
                "gap_start": prev.timestamp,
                "gap_end": curr.timestamp,
                "gap_minutes": round(gap.total_seconds() / 60, 1),
                "inconsistent_before": prev.inconsistent_count,
                "inconsistent_after": curr.inconsistent_count,
                "delta_inconsistent": delta_inconsistent,
                "delta_votes": delta_votes,
                "trend_shifts_pp": trend_shifts,
                "description": (
                    f"Apagón comunicacional de {gap.total_seconds() / 60:.0f} min "
                    f"({prev.timestamp} → {curr.timestamp}). "
                    f"AI: {prev.inconsistent_count} → {curr.inconsistent_count} "
                    f"(Δ={delta_inconsistent}). "
                    + (
                        "Cambios de tendencia: "
                        + ", ".join(f"{c}: {s:+.3f}pp" for c, s in trend_shifts.items())
                        if trend_shifts
                        else "Sin cambio de tendencia significativo."
                    )
                ),
            })

        return blackouts

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
        Incluye: outliers 3σ, resoluciones de alto impacto, resoluciones masivas,
        estancamiento prolongado, sesgo estadístico, velocidad anómala, asimetría,
        hold-and-release, Benford, y apagones comunicacionales.
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

        # Velocidad de resolución anómala.
        for velocity in self.detect_resolution_velocity_anomalies():
            anomalies.append(
                Anomaly(
                    kind="anomalous_resolution_velocity",
                    severity="critical",
                    message=velocity["description"],
                    timestamp=velocity["timestamp"],
                    metadata={
                        "rate_per_minute": velocity["rate_per_minute"],
                        "delta_actas": velocity["delta_actas"],
                        "elapsed_minutes": velocity["elapsed_minutes"],
                    },
                )
            )

        # Beneficio asimétrico.
        asymmetry = self.detect_asymmetric_benefit()
        if asymmetry and asymmetry["significant"]:
            anomalies.append(
                Anomaly(
                    kind="asymmetric_benefit",
                    severity="critical",
                    message=asymmetry["description"],
                    timestamp=self.snapshots[-1].timestamp if self.snapshots else datetime.now(timezone.utc),
                    metadata={
                        "beneficiary": asymmetry["beneficiary"],
                        "swing_pp": asymmetry["swing_pp"],
                        "z_score": asymmetry["z_score"],
                        "estimated_extra_votes": asymmetry["estimated_extra_votes"],
                    },
                )
            )

        # Patrones hold-and-release.
        for pattern in self.detect_hold_and_release():
            anomalies.append(
                Anomaly(
                    kind="hold_and_release",
                    severity="critical",
                    message=pattern["description"],
                    timestamp=pattern["release_timestamp"],
                    metadata={
                        "stagnation_cycles": pattern["stagnation_cycles"],
                        "released_actas": pattern["released_actas"],
                        "released_votes": pattern["released_votes"],
                    },
                )
            )

        # Benford sobre escrutinio especial.
        benford = self.detect_benford_special_scrutiny()
        if benford and benford["significant"]:
            anomalies.append(
                Anomaly(
                    kind="benford_deviation",
                    severity="critical",
                    message=benford["description"],
                    timestamp=self.snapshots[-1].timestamp if self.snapshots else datetime.now(timezone.utc),
                    metadata={
                        "chi2_statistic": benford["chi2_statistic"],
                        "chi2_pvalue": benford["chi2_pvalue"],
                        "n_samples": benford["n_samples"],
                    },
                )
            )

        # Apagones comunicacionales.
        for blackout in self.detect_blackout_windows():
            if blackout["trend_shifts_pp"]:
                anomalies.append(
                    Anomaly(
                        kind="blackout_with_trend_shift",
                        severity="critical",
                        message=blackout["description"],
                        timestamp=blackout["gap_end"],
                        metadata={
                            "gap_minutes": blackout["gap_minutes"],
                            "delta_inconsistent": blackout["delta_inconsistent"],
                            "trend_shifts_pp": blackout["trend_shifts_pp"],
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

        sections = [
            f"# Forensic Report: Inconsistent Acts / Reporte Forense: Actas Inconsistentes\n\n"
            f"Generated at / Generado en: `{generated_at}`\n\n"
            f"## 1. Clave detectada / Detected key\n"
            f"- `{self.detected_inconsistent_key}`\n",

            f"## 2. Acumulado escrutinio especial / Special scrutiny cumulative\n"
            f"```json\n{json.dumps(self.get_special_scrutiny_cumulative(), indent=2, ensure_ascii=False)}\n```\n",

            f"## 3. Pruebas estadísticas / Statistical tests\n"
            f"```json\n{json.dumps(stats, indent=2, ensure_ascii=False)}\n```\n",

            f"## 4. Anomalías detectadas / Detected anomalies\n"
            f"```json\n{json.dumps([asdict(a) for a in anomalies], indent=2, default=str, ensure_ascii=False)}\n```\n",

            f"## 5. Detección de Inyección Progresiva Controlada\n"
            f"{self._render_progressive_injection_section()}\n",

            f"## 6. Velocidad de Resolución / Resolution Velocity\n"
            f"{self._render_velocity_section()}\n",

            f"## 7. Beneficio Asimétrico / Asymmetric Benefit\n"
            f"{self._render_asymmetry_section()}\n",

            f"## 8. Patrón Hold-and-Release\n"
            f"{self._render_hold_and_release_section()}\n",

            f"## 9. Ley de Benford en Escrutinio Especial / Benford's Law\n"
            f"{self._render_benford_section()}\n",

            f"## 10. Apagones Comunicacionales / Communication Blackouts\n"
            f"{self._render_blackout_section()}\n",

            f"## Ecuaciones / Equations\n{latex_block}\n",

            f"## Hashes de fuente SHA-256 / Source hashes SHA-256\n{hashes}\n",
        ]

        return "\n".join(sections)

    def _render_progressive_injection_section(self) -> str:
        """Render progressive injection section for forensic markdown report.

        Renderiza la sección de inyección progresiva para el reporte forense en markdown.
        """
        detection = self.detect_progressive_injection()
        if not detection:
            return "Patrón detectado en: N/A"

        net_swing = ", ".join(f"{candidate} {delta:+d} votos" for candidate, delta in sorted(detection["net_swing"].items()))
        return (
            f"Patrón detectado en: {detection['start_timestamp']} – {detection['end_timestamp']}  \n"
            f"Ciclos consecutivos: {detection['cycles_count']}  \n"
            f"Delta promedio por ciclo: {detection['avg_delta_per_cycle']:.2f} votos  \n"
            f"Swing neto acumulado: {net_swing}  \n"
            f"Z-score acumulativo: {detection['z_score_acumulado']:+.3f} "
            f"(p = {detection['z_score_pvalue']:.5f})  \n"
            f"Test de runs (Wald-Wolfowitz): p = {detection['run_test_pvalue']:.5f} "
            f"(no aleatoriedad si <0.05)  \n"
            f"Autocorrelación lag-1: {detection['autocorrelation_lag1']:.3f} "
            f"(persistencia si >0.4)  \n"
            "Referencia histórica: comparar contra ventanas previas del mismo proceso electoral para validar desviación estructural"
        )

    def _render_velocity_section(self) -> str:
        """Render resolution velocity analysis section.

        Renderiza la sección de análisis de velocidad de resolución.
        """
        anomalies = self.detect_resolution_velocity_anomalies()
        if not anomalies:
            return "No se detectaron resoluciones con velocidad anómala."
        lines = [f"Se detectaron {len(anomalies)} ciclos con velocidad de resolución anómala:\n"]
        for a in anomalies:
            lines.append(
                f"- **{a['timestamp']}**: {a['delta_actas']} actas en {a['elapsed_minutes']} min "
                f"= {a['rate_per_minute']} actas/min (umbral: {a['threshold']})"
            )
        return "\n".join(lines)

    def _render_asymmetry_section(self) -> str:
        """Render asymmetric benefit analysis section.

        Renderiza la sección de análisis de beneficio asimétrico.
        """
        result = self.detect_asymmetric_benefit()
        if not result:
            return "No se detectó beneficio asimétrico significativo entre escrutinio especial y normal."
        lines = [
            f"**Beneficiario principal**: {result['beneficiary']}  ",
            f"Proporción en escrutinio especial: {result['special_proportion']}%  ",
            f"Proporción en voto normal: {result['normal_proportion']}%  ",
            f"Swing: +{result['swing_pp']} pp  ",
            f"Z-score: {result['z_score']:+.3f} (p = {result['z_pvalue']:.5f})  ",
            f"Votos extra estimados: ~{result['estimated_extra_votes']:,}  ",
            f"Significativo: {'Sí' if result['significant'] else 'No'}  \n",
            "Swings por candidato (pp):  ",
        ]
        for c, s in sorted(result["all_swings_pp"].items()):
            lines.append(f"- {c}: {s:+.2f} pp")
        return "\n".join(lines)

    def _render_hold_and_release_section(self) -> str:
        """Render hold-and-release pattern section.

        Renderiza la sección de patrones hold-and-release.
        """
        patterns = self.detect_hold_and_release()
        if not patterns:
            return "No se detectaron patrones hold-and-release."
        lines = [f"Se detectaron {len(patterns)} patrones hold-and-release:\n"]
        for p in patterns:
            lines.append(
                f"- Estancamiento desde {p['stagnation_start']} ({p['stagnation_cycles']} ciclos) "
                f"→ resolución masiva en {p['release_timestamp']}: "
                f"{p['released_actas']} actas, {p['released_votes']} votos"
            )
        return "\n".join(lines)

    def _render_benford_section(self) -> str:
        """Render Benford's Law analysis section.

        Renderiza la sección de análisis de Ley de Benford.
        """
        result = self.detect_benford_special_scrutiny()
        if not result:
            return "Datos insuficientes para test de Benford (se requieren ≥10 deltas positivos)."
        lines = [
            f"Muestras analizadas: {result['n_samples']}  ",
            f"χ² = {result['chi2_statistic']:.4f}, p = {result['chi2_pvalue']:.5f}  ",
            f"Resultado: {'**Desviación significativa**' if result['significant'] else 'Sin desviación significativa'}  \n",
            "| Dígito | Observado % | Esperado % | Desviación pp |",
            "|--------|------------|------------|---------------|",
        ]
        for d, info in sorted(result["digit_analysis"].items()):
            lines.append(f"| {d} | {info['observed_pct']:.2f} | {info['expected_pct']:.2f} | {info['deviation_pp']:+.2f} |")
        return "\n".join(lines)

    def _render_blackout_section(self) -> str:
        """Render blackout detection section.

        Renderiza la sección de detección de apagones comunicacionales.
        """
        blackouts = self.detect_blackout_windows()
        if not blackouts:
            return "No se detectaron apagones comunicacionales significativos."
        lines = [f"Se detectaron {len(blackouts)} ventanas de apagón:\n"]
        for b in blackouts:
            lines.append(
                f"### Apagón: {b['gap_start']} → {b['gap_end']} ({b['gap_minutes']} min)\n"
                f"- AI antes: {b['inconsistent_before']}, después: {b['inconsistent_after']} "
                f"(Δ = {b['delta_inconsistent']})"
            )
            if b["trend_shifts_pp"]:
                lines.append("- Cambios de tendencia:")
                for c, s in sorted(b["trend_shifts_pp"].items()):
                    lines.append(f"  - {c}: {s:+.3f} pp")
            else:
                lines.append("- Sin cambio de tendencia significativo")
        return "\n".join(lines)

    def _load_runtime_config(self) -> dict[str, Any]:
        """Load optional runtime thresholds from config.json.

        Carga umbrales opcionales en tiempo de ejecución desde config.json.
        """
        if not self.runtime_config_path.exists():
            return {}
        payload = json.loads(self.runtime_config_path.read_text(encoding="utf-8"))
        section = payload.get("inconsistent_acts", payload)
        return section if isinstance(section, dict) else {}

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

    def _runs_test_pvalue(self, values: list[float]) -> float:
        """Compute Wald-Wolfowitz runs-test p-value using median split.

        Calcula p-value de Wald-Wolfowitz usando separación por mediana.
        """
        if len(values) < 3:
            return 1.0
        median = sorted(values)[len(values) // 2]
        signs = [1 if value >= median else 0 for value in values]
        n1 = sum(signs)
        n2 = len(signs) - n1
        if n1 == 0 or n2 == 0:
            return 1.0

        runs = 1
        for previous, current in zip(signs, signs[1:]):
            if current != previous:
                runs += 1

        mean_runs = 1 + (2 * n1 * n2) / (n1 + n2)
        variance_runs = (2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / (((n1 + n2) ** 2) * (n1 + n2 - 1))
        if variance_runs <= 0:
            return 1.0
        z_score = (runs - mean_runs) / sqrt(variance_runs)
        return float(2 * (1 - norm.cdf(abs(z_score))))

    def _autocorrelation_lag1(self, values: list[float]) -> float:
        """Compute lag-1 autocorrelation for injection delta persistence.

        Calcula autocorrelación lag-1 para persistencia en deltas de inyección.
        """
        if len(values) < 2:
            return 0.0
        x = values[:-1]
        y = values[1:]
        x_mean = sum(x) / len(x)
        y_mean = sum(y) / len(y)
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        denominator = sqrt(sum((xi - x_mean) ** 2 for xi in x) * sum((yi - y_mean) ** 2 for yi in y))
        if denominator == 0:
            return 0.0
        return float(numerator / denominator)
