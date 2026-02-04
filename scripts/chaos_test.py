"""Chaos testing for CENTINEL Engine polling resiliency.

Español:
Este módulo expande los escenarios de chaos testing para simular fallos reales
observados en el CNE (rate limits, timeouts, JSON malformado, hashes alterados,
fallos de proxy y watchdog). El objetivo es validar la capacidad de recuperación
sobre endpoints agregados (departamental/nacional) sin tocar mesas ni actas, y
registrar métricas que refuercen la credibilidad de la auditoría digital.

English:
This module expands chaos testing scenarios to simulate real-world failures
observed at the CNE (rate limits, timeouts, malformed JSON, altered hashes,
proxy failures, and watchdog triggers). The goal is to validate recovery
behavior on aggregated polling endpoints (department/national) while recording
metrics that strengthen the credibility of the digital audit.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import responses
import yaml


DEFAULT_CONFIG_PATH = Path("chaos_config.yaml")
DEFAULT_REPORT_PATH = Path("chaos_report.json")
CNE_BASE_URL = "https://cne.example/api"  # Placeholder for mock endpoints.
CNE_ENDPOINTS = (
    f"{CNE_BASE_URL}/polling/national.json",
    f"{CNE_BASE_URL}/polling/departamental.json",
)


class ChaosScenarioError(RuntimeError):
    """Español: Error base para fallos simulados de chaos testing.

    English: Base error for simulated chaos testing failures.
    """


class RateLimitError(ChaosScenarioError):
    """Español: Error de rate limit 429 simulado.

    English: Simulated 429 rate limit error.
    """


class ServerTimeoutError(ChaosScenarioError):
    """Español: Error de timeout 503 simulado.

    English: Simulated 503 timeout error.
    """


class MalformedPayloadError(ChaosScenarioError):
    """Español: Error por JSON malformado simulado.

    English: Simulated malformed JSON error.
    """


class HashMismatchError(ChaosScenarioError):
    """Español: Error por hash alterado simulado.

    English: Simulated altered hash error.
    """


class ProxyFailureError(ChaosScenarioError):
    """Español: Error por fallo de proxy simulado.

    English: Simulated proxy failure error.
    """


@dataclass
class ChaosScenarioProfile:
    """Español: Configuración por escenario de caos.

    Incluye probabilidad y peso relativo para simular fallos reales del CNE.

    English: Per-scenario chaos configuration.

    Includes probability and relative weight to simulate real CNE failures.
    """

    probability: float = 0.0


@dataclass
class ChaosLevelConfig:
    """Español: Configuración del nivel de caos.

    Define duración, probabilidad global y parámetros de retry para validar
    resiliencia del pipeline de auditoría.

    English: Chaos level configuration.

    Defines duration, global failure probability, and retry parameters to
    validate audit pipeline resilience.
    """

    name: str
    duration_seconds: float
    request_interval_seconds: float
    failure_probability: float
    timeout_seconds: float
    max_attempts: int
    backoff_seconds: float
    watchdog_inactivity_seconds: float
    scenarios: Dict[str, ChaosScenarioProfile] = field(default_factory=dict)


@dataclass
class ChaosMetrics:
    """Español: Métricas de resiliencia capturadas por el experimento.

    Incluye conteo de fallos, anomalías, tiempos de recuperación y placeholders
    para p-values de futuras pruebas estadísticas.

    English: Resilience metrics captured by the experiment.

    Includes failure counts, anomaly flags, recovery times, and placeholders for
    future p-value statistical tests.
    """

    failures: Dict[str, int] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)
    first_failure_time: Optional[float] = None
    first_recovery_time: Optional[float] = None
    p_values: Dict[str, Optional[float]] = field(default_factory=dict)

    def record_failure(self, scenario: str) -> None:
        """Español: Registra un fallo por escenario.

        English: Record a failure by scenario.
        """

        self.failures[scenario] = self.failures.get(scenario, 0) + 1
        if self.first_failure_time is None:
            self.first_failure_time = time.monotonic()

    def record_anomaly(self, anomaly: str) -> None:
        """Español: Registra una anomalía detectada.

        English: Record a detected anomaly.
        """

        if anomaly not in self.anomalies:
            self.anomalies.append(anomaly)

    def record_recovery(self) -> None:
        """Español: Registra el primer evento de recuperación.

        English: Record the first recovery event.
        """

        if self.first_failure_time is not None and self.first_recovery_time is None:
            self.first_recovery_time = time.monotonic()

    def recovery_time_seconds(self) -> Optional[float]:
        """Español: Devuelve el tiempo de recuperación si existe.

        English: Return recovery time if available.
        """

        if self.first_failure_time is None or self.first_recovery_time is None:
            return None
        return self.first_recovery_time - self.first_failure_time


@dataclass
class ChaosReport:
    """Español: Reporte final del experimento de caos.

    English: Final report from the chaos experiment.
    """

    level: str
    total_requests: int
    metrics: ChaosMetrics

    def to_dict(self) -> Dict[str, Any]:
        """Español: Convierte el reporte a un diccionario serializable.

        English: Convert the report to a serializable dictionary.
        """

        return {
            "level": self.level,
            "total_requests": self.total_requests,
            "failures": self.metrics.failures,
            "anomalies": self.metrics.anomalies,
            "recovery_time_seconds": self.metrics.recovery_time_seconds(),
            "p_values": self.metrics.p_values,
        }


def load_chaos_config(path: Path) -> Dict[str, Any]:
    """Español: Carga configuración YAML para chaos testing.

    Si el archivo no existe, retorna un default seguro para CI.

    English: Load YAML configuration for chaos testing.

    If the file does not exist, returns a safe default for CI.
    """

    if not path.exists():
        return {
            "chaos": {
                "default_level": "low",
                "levels": {
                    "low": {
                        "duration_seconds": 10,
                        "request_interval_seconds": 0.0,
                        "failure_probability": 0.2,
                        "timeout_seconds": 1.0,
                        "max_attempts": 3,
                        "backoff_seconds": 0.0,
                        "watchdog_inactivity_seconds": 3,
                        "scenarios": {
                            "rate_limit_429": {"probability": 0.3},
                            "timeout_503": {"probability": 0.2},
                            "malformed_json": {"probability": 0.1},
                            "hash_altered": {"probability": 0.1},
                            "proxy_fail": {"probability": 0.1},
                            "watchdog_trigger": {"probability": 0.2},
                        },
                    }
                },
            }
        }
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_level_config(config: Dict[str, Any], level: str) -> ChaosLevelConfig:
    """Español: Construye la configuración de un nivel específico.

    English: Build the configuration for a specific level.
    """

    chaos_config = config.get("chaos", {})
    levels = chaos_config.get("levels", {})
    if level not in levels:
        raise ValueError(f"Unknown chaos level: {level}")
    level_cfg = levels[level]
    scenarios_cfg = {
        name: ChaosScenarioProfile(probability=values.get("probability", 0.0))
        for name, values in (level_cfg.get("scenarios", {}) or {}).items()
    }
    return ChaosLevelConfig(
        name=level,
        duration_seconds=float(level_cfg.get("duration_seconds", 30)),
        request_interval_seconds=float(level_cfg.get("request_interval_seconds", 0.1)),
        failure_probability=float(level_cfg.get("failure_probability", 0.2)),
        timeout_seconds=float(level_cfg.get("timeout_seconds", 3.0)),
        max_attempts=int(level_cfg.get("max_attempts", 4)),
        backoff_seconds=float(level_cfg.get("backoff_seconds", 0.5)),
        watchdog_inactivity_seconds=float(
            level_cfg.get("watchdog_inactivity_seconds", 10)
        ),
        scenarios=scenarios_cfg,
    )


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Español: Calcula hash SHA-256 para un payload de resultados.

    English: Compute SHA-256 hash for a results payload.
    """

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256(canonical).hexdigest()


def build_polling_payload(scope: str, attempt: int) -> Dict[str, Any]:
    """Español: Construye un payload de resultados con hash consistente.

    English: Build a results payload with a consistent hash.
    """

    data = {
        "scope": scope,
        "attempt": attempt,
        "totals": {"participation": 0.64, "votes": 123456},
    }
    payload = {"data": data, "hash": compute_payload_hash(data)}
    return payload


def validate_payload(payload: Dict[str, Any]) -> None:
    """Español: Valida consistencia de hash en el payload.

    English: Validate hash consistency in the payload.
    """

    data = payload.get("data")
    expected_hash = compute_payload_hash(data)
    if payload.get("hash") != expected_hash:
        raise HashMismatchError("hash_mismatch_detected")


def evaluate_watchdog(last_success: float, now: float, threshold: float) -> bool:
    """Español: Evalúa si el watchdog detecta inactividad.

    English: Evaluate if the watchdog detects inactivity.
    """

    return (now - last_success) > threshold


def select_scenario(
    rng: random.Random, level: ChaosLevelConfig
) -> Optional[str]:
    """Español: Selecciona un escenario de fallo según probabilidad.

    English: Select a failure scenario based on probability.
    """

    if rng.random() > level.failure_probability:
        return None
    scenarios = list(level.scenarios.items())
    if not scenarios:
        return None
    weights = [profile.probability for _, profile in scenarios]
    total = sum(weights)
    if total <= 0:
        return None
    choice = rng.random() * total
    cumulative = 0.0
    for name, profile in scenarios:
        cumulative += profile.probability
        if choice <= cumulative:
            return name
    return scenarios[-1][0]


def build_mock_callback(
    rng: random.Random,
    level: ChaosLevelConfig,
    metrics: ChaosMetrics,
    logger: logging.Logger,
    scope: str,
) -> callable:
    """Español: Genera un callback de responses con escenarios CNE-specific.

    English: Generate a responses callback with CNE-specific scenarios.
    """

    attempt_counter = {"count": 0}

    def _callback(request: requests.PreparedRequest) -> Tuple[int, Dict[str, str], str]:
        attempt_counter["count"] += 1
        scenario = select_scenario(rng, level)
        if scenario == "rate_limit_429":
            metrics.record_failure("rate_limit_429")
            logger.warning("scenario=rate_limit_429 url=%s", request.url)
            return 429, {"Retry-After": "5"}, json.dumps({"error": "rate limit"})
        if scenario == "timeout_503":
            metrics.record_failure("timeout_503")
            logger.warning("scenario=timeout_503 url=%s", request.url)
            raise requests.Timeout("simulated_timeout")
        if scenario == "malformed_json":
            metrics.record_failure("malformed_json")
            logger.warning("scenario=malformed_json url=%s", request.url)
            return 200, {}, "{invalid-json"
        if scenario == "hash_altered":
            metrics.record_failure("hash_altered")
            logger.warning("scenario=hash_altered url=%s", request.url)
            payload = build_polling_payload(scope, attempt_counter["count"])
            payload["hash"] = "tampered"
            return 200, {}, json.dumps(payload)
        if scenario == "proxy_fail":
            metrics.record_failure("proxy_fail")
            logger.warning("scenario=proxy_fail url=%s", request.url)
            raise requests.ProxyError("simulated_proxy_failure")
        if scenario == "watchdog_trigger":
            metrics.record_failure("watchdog_trigger")
            logger.warning("scenario=watchdog_trigger url=%s", request.url)
            return 503, {}, json.dumps({"error": "watchdog_triggered"})
        payload = build_polling_payload(scope, attempt_counter["count"])
        return 200, {}, json.dumps(payload)

    return _callback


def fetch_polling_json(
    session: requests.Session,
    url: str,
    level: ChaosLevelConfig,
    metrics: ChaosMetrics,
    logger: logging.Logger,
) -> Dict[str, Any]:
    """Español: Descarga y valida un JSON de polling con reintentos.

    English: Download and validate a polling JSON with retries.
    """

    for attempt in range(1, level.max_attempts + 1):
        try:
            response = session.get(url, timeout=level.timeout_seconds)
            if response.status_code == 429:
                raise RateLimitError("rate_limit_429")
            if response.status_code >= 500:
                raise ServerTimeoutError("timeout_503")
            payload = response.json()
            validate_payload(payload)
            if metrics.first_failure_time is not None:
                metrics.record_recovery()
            return payload
        except RateLimitError:
            metrics.record_failure("rate_limit_429")
            logger.info("retrying due to rate limit attempt=%s", attempt)
        except ServerTimeoutError:
            metrics.record_failure("timeout_503")
            logger.info("retrying due to timeout attempt=%s", attempt)
        except requests.Timeout:
            metrics.record_failure("timeout_503")
            logger.info("retrying due to timeout exception attempt=%s", attempt)
        except requests.ProxyError:
            metrics.record_failure("proxy_fail")
            logger.info("retrying due to proxy error attempt=%s", attempt)
        except (ValueError, json.JSONDecodeError):
            metrics.record_failure("malformed_json")
            logger.info("retrying due to malformed json attempt=%s", attempt)
        except HashMismatchError:
            metrics.record_failure("hash_altered")
            metrics.record_anomaly("hash_mismatch")
            logger.info("retrying due to hash mismatch attempt=%s", attempt)
        if attempt < level.max_attempts:
            time.sleep(level.backoff_seconds)
    raise ChaosScenarioError("max_attempts_exceeded")


def run_chaos_experiment(
    level: ChaosLevelConfig,
    logger: logging.Logger,
    rng: Optional[random.Random] = None,
) -> ChaosReport:
    """Español: Ejecuta el experimento de caos y genera un reporte.

    English: Run the chaos experiment and generate a report.
    """

    rng = rng or random.Random()
    metrics = ChaosMetrics()
    for scenario in level.scenarios:
        metrics.p_values[scenario] = None
    total_requests = 0
    last_success = time.monotonic()

    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        for endpoint in CNE_ENDPOINTS:
            scope = "national" if "national" in endpoint else "departamental"
            callback = build_mock_callback(rng, level, metrics, logger, scope)
            mock.add_callback(
                responses.GET,
                endpoint,
                callback=callback,
                content_type="application/json",
            )

        session = requests.Session()
        start = time.monotonic()
        while time.monotonic() - start < level.duration_seconds:
            for endpoint in CNE_ENDPOINTS:
                total_requests += 1
                try:
                    fetch_polling_json(session, endpoint, level, metrics, logger)
                    last_success = time.monotonic()
                except ChaosScenarioError as exc:
                    logger.warning("request_failed error=%s", exc)
                now = time.monotonic()
                if evaluate_watchdog(last_success, now, level.watchdog_inactivity_seconds):
                    metrics.record_anomaly("watchdog_trigger")
                    logger.error("watchdog_triggered inactivity=%.2fs", now - last_success)
                if level.request_interval_seconds > 0:
                    time.sleep(level.request_interval_seconds)

    report = ChaosReport(level=level.name, total_requests=total_requests, metrics=metrics)
    logger.info(
        "chaos_report level=%s total_requests=%s recovery_time=%s anomalies=%s",
        report.level,
        report.total_requests,
        report.metrics.recovery_time_seconds(),
        report.metrics.anomalies,
    )
    return report


def write_report(report: ChaosReport, path: Path) -> None:
    """Español: Escribe el reporte de caos en disco como JSON.

    English: Write the chaos report to disk as JSON.
    """

    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def parse_args(args: Optional[Iterable[str]] = None) -> argparse.Namespace:
    """Español: Parsea argumentos CLI del script.

    English: Parse CLI arguments for the script.
    """

    parser = argparse.ArgumentParser(description="Run CNE chaos testing")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Ruta al chaos_config.yaml",
    )
    parser.add_argument(
        "--level",
        type=str,
        default=None,
        help="Nivel de caos (low/mid/high)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Archivo de salida para reporte JSON",
    )
    return parser.parse_args(args)


def main(args: Optional[Iterable[str]] = None) -> int:
    """Español: Punto de entrada principal para ejecutar chaos testing.

    English: Main entry point for running chaos testing.
    """

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("centinel.chaos")
    parsed = parse_args(args)
    config = load_chaos_config(parsed.config)
    default_level = config.get("chaos", {}).get("default_level", "low")
    level_name = parsed.level or default_level
    level = build_level_config(config, level_name)
    report = run_chaos_experiment(level, logger)
    write_report(report, parsed.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
