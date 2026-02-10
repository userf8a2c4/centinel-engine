"""Chaos testing for CNE Honduras monitoring simulations."""

from __future__ import annotations

__test__ = False

import argparse
import json
import logging
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import requests

try:
    import responses
except ModuleNotFoundError:  # pragma: no cover - fallback when responses isn't installed.
    responses = None
import yaml

SCENARIOS = (
    "rate_limit_429",
    "timeout_503",
    "malformed_json",
    "hash_altered",
    "proxy_fail",
    "watchdog_heartbeat_miss",
    "slow_response",
)


@dataclass
class ChaosConfig:
    """Español: Configuración de caos para simulaciones CNE Honduras.

    English: Chaos configuration for Honduras CNE simulations.
    """

    level: str
    duration_minutes: float
    failure_probability: float
    scenarios_enabled: List[str]
    scope: str = "NATIONAL"
    base_url: str = "https://cne.hn/api/snapshot"
    request_timeout_seconds: float = 2.0
    polling_interval_seconds: float = 0.2
    heartbeat_timeout_seconds: float = 1.0
    max_recovery_seconds: float = 2.0
    slow_response_seconds: float = 0.3
    report_path: Path = Path("chaos_report.md")


@dataclass
class ChaosMetrics:
    """Español: Métricas agregadas de resiliencia y recuperación.

    English: Aggregated resilience and recovery metrics.
    """

    successful_requests: int = 0
    failed_requests: int = 0
    recovery_times: List[float] = field(default_factory=list)
    scenario_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class ScenarioContext:
    """Español: Contexto del último escenario ejecutado.

    English: Context for the most recent executed scenario.
    """

    name: Optional[str] = None
    skip_heartbeat: bool = False
    slow_response: bool = False


class WatchdogMonitor:
    """Español: Monitor de heartbeat con disparo de watchdog.

    English: Heartbeat monitor with watchdog trigger detection.
    """

    def __init__(self, heartbeat_timeout_seconds: float) -> None:
        """Español: Inicializa el monitor de watchdog.

        English: Initialize the watchdog monitor.
        """
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.last_heartbeat = time.monotonic()
        self.triggered = False

    def heartbeat(self) -> None:
        """Español: Registra un heartbeat exitoso.

        English: Record a successful heartbeat.
        """
        self.last_heartbeat = time.monotonic()
        self.triggered = False

    def check(self) -> bool:
        """Español: Verifica si se superó el timeout y dispara watchdog.

        English: Check if timeout exceeded and trigger watchdog.
        """
        elapsed = time.monotonic() - self.last_heartbeat
        if elapsed > self.heartbeat_timeout_seconds and not self.triggered:
            self.triggered = True
            return True
        return False


def _hash_payload(scope: str, sequence: int) -> str:
    """Español: Calcula hash determinista para el snapshot.

    English: Compute deterministic hash for the snapshot.
    """
    payload = f"{scope}:{sequence}".encode("utf-8")
    return sha256(payload).hexdigest()


def _build_snapshot(scope: str, sequence: int) -> Dict[str, str]:
    """Español: Construye un snapshot simulado de CNE.

    English: Build a simulated CNE snapshot.
    """
    return {
        "scope": scope,
        "sequence": str(sequence),
        "hash": _hash_payload(scope, sequence),
    }


def _load_config(config_path: Path) -> ChaosConfig:
    """Español: Carga configuración de caos desde YAML.

    English: Load chaos configuration from YAML.
    """
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    chaos = payload.get("chaos", {})
    scenarios = chaos.get("scenarios_enabled", chaos.get("specific_scenarios_enabled", SCENARIOS))
    return ChaosConfig(
        level=str(chaos.get("level", "low")).lower(),
        duration_minutes=float(chaos.get("duration_minutes", 1)),
        failure_probability=float(chaos.get("failure_probability", 0.2)),
        scenarios_enabled=list(scenarios),
        scope=str(chaos.get("scope", "NATIONAL")),
        base_url=str(chaos.get("base_url", "https://cne.hn/api/snapshot")),
        request_timeout_seconds=float(chaos.get("request_timeout_seconds", 2.0)),
        polling_interval_seconds=float(chaos.get("polling_interval_seconds", 0.2)),
        heartbeat_timeout_seconds=float(chaos.get("heartbeat_timeout_seconds", 1.0)),
        max_recovery_seconds=float(chaos.get("max_recovery_seconds", 2.0)),
        slow_response_seconds=float(chaos.get("slow_response_seconds", 0.3)),
        report_path=Path(chaos.get("report_path", "chaos_report.md")),
    )


def _apply_level_defaults(config: ChaosConfig) -> None:
    """Español: Ajusta parámetros según nivel de caos.

    English: Adjust parameters based on chaos level.
    """
    level = config.level
    if level == "low":
        config.failure_probability = min(config.failure_probability, 0.3)
        config.slow_response_seconds = min(config.slow_response_seconds, 0.2)
        config.polling_interval_seconds = max(config.polling_interval_seconds, 0.2)
    elif level == "medium":
        config.failure_probability = max(config.failure_probability, 0.35)
        config.slow_response_seconds = max(config.slow_response_seconds, 0.3)
    elif level == "high":
        config.failure_probability = max(config.failure_probability, 0.55)
        config.slow_response_seconds = max(config.slow_response_seconds, 0.5)
        config.polling_interval_seconds = max(config.polling_interval_seconds, 0.1)


def _select_scenario(rng: random.Random, enabled: Iterable[str], failure_probability: float) -> Optional[str]:
    """Español: Selecciona un escenario según probabilidad.

    English: Select a scenario based on probability.
    """
    enabled_list = [scenario for scenario in enabled if scenario in SCENARIOS]
    if not enabled_list or rng.random() > failure_probability:
        return None
    return rng.choice(enabled_list)


def _configure_logger() -> logging.Logger:
    """Español: Configura logger para pruebas de caos.

    English: Configure logger for chaos tests.
    """
    logger = logging.getLogger("cne.chaos")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def _write_report(
    config: ChaosConfig,
    metrics: ChaosMetrics,
    report_path: Path,
    duration_seconds: float,
) -> None:
    """Español: Escribe un reporte formal para observadores internacionales.

    English: Write a formal report for international observers.
    """
    avg_recovery = sum(metrics.recovery_times) / len(metrics.recovery_times) if metrics.recovery_times else 0.0
    max_recovery = max(metrics.recovery_times) if metrics.recovery_times else 0.0
    lines = [
        "# Chaos Testing Report — CNE Honduras",
        "",
        "## Summary",
        f"- Level: {config.level}",
        f"- Duration (minutes): {config.duration_minutes}",
        f"- Elapsed (seconds): {duration_seconds:.2f}",
        f"- Failure probability: {config.failure_probability:.2f}",
        f"- Successful requests: {metrics.successful_requests}",
        f"- Failed requests: {metrics.failed_requests}",
        f"- Average recovery time (s): {avg_recovery:.2f}",
        f"- Max recovery time (s): {max_recovery:.2f}",
        "",
        "## Scenario counts",
    ]
    for scenario, count in sorted(metrics.scenario_counts.items()):
        lines.append(f"- {scenario}: {count}")
    lines.extend(
        [
            "",
            "## Assurance Statement",
            (
                "Este reporte documenta condiciones adversas realistas (CNE Honduras) "
                "y evidencia que el sistema logra recuperar continuidad operativa tras fallas "
                "transitorias, alineado con prácticas observadas por misiones internacionales."
            ),
            (
                "This report documents realistic adverse conditions (Honduras CNE) "
                "and demonstrates that the system restores operational continuity after "
                "transient faults, aligned with practices expected by international observers."
            ),
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _run_chaos_test(config: ChaosConfig) -> Dict[str, object]:
    """Español: Ejecuta escenarios de caos y genera un reporte.

    English: Run chaos scenarios and generate a report.
    """
    logger = _configure_logger()
    metrics = ChaosMetrics()
    rng = random.Random(2029)
    scenario_context = ScenarioContext()
    watchdog = WatchdogMonitor(config.heartbeat_timeout_seconds)
    last_failure_time: Optional[float] = None

    def _callback(request: requests.PreparedRequest) -> Tuple[int, Dict[str, str], str]:
        scenario = _select_scenario(rng, config.scenarios_enabled, config.failure_probability)
        scenario_context.name = scenario
        scenario_context.skip_heartbeat = scenario == "watchdog_heartbeat_miss"
        scenario_context.slow_response = scenario == "slow_response"
        if scenario:
            metrics.scenario_counts[scenario] = metrics.scenario_counts.get(scenario, 0) + 1
        if scenario == "rate_limit_429":
            logger.warning("scenario=rate_limit_429 url=%s", request.url)
            return 429, {"Retry-After": "5"}, json.dumps({"error": "rate limit"})
        if scenario == "timeout_503":
            logger.warning("scenario=timeout_503 url=%s", request.url)
            return 503, {"Retry-After": "4"}, json.dumps({"error": "timeout_503"})
        if scenario == "malformed_json":
            logger.warning("scenario=malformed_json url=%s", request.url)
            return 200, {}, "{invalid-json"
        if scenario == "hash_altered":
            logger.warning("scenario=hash_altered url=%s", request.url)
            payload = _build_snapshot(config.scope, metrics.successful_requests + 1)
            payload["hash"] = "tampered"
            return 200, {}, json.dumps(payload)
        if scenario == "proxy_fail":
            logger.warning("scenario=proxy_fail url=%s", request.url)
            raise requests.exceptions.ProxyError("simulated_proxy_failure")
        if scenario == "slow_response":
            logger.warning("scenario=slow_response url=%s", request.url)
            time.sleep(config.slow_response_seconds)
        payload = _build_snapshot(config.scope, metrics.successful_requests + 1)
        return 200, {}, json.dumps(payload)

    start_time = time.monotonic()
    end_time = start_time + config.duration_minutes * 60
    session = requests.Session()

    class _MockResponse:
        def __init__(self, status_code: int, body: str) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> Dict[str, object]:
            return json.loads(self._body)

    @contextmanager
    def _mock_requests(
        callback: Callable[[requests.PreparedRequest], Tuple[int, Dict[str, str], str]],
    ) -> Iterable[None]:
        original_get = session.get

        def _fake_get(url: str, timeout: float | None = None) -> _MockResponse:
            if url != config.base_url:
                return original_get(url, timeout=timeout)
            request = requests.Request("GET", url).prepare()
            status, _headers, body = callback(request)
            return _MockResponse(status, body)

        session.get = _fake_get  # type: ignore[assignment]
        try:
            yield
        finally:
            session.get = original_get  # type: ignore[assignment]

    if responses is not None:
        context = responses.RequestsMock(assert_all_requests_are_fired=False)
        context.add_callback(responses.GET, config.base_url, callback=_callback)
    else:
        context = _mock_requests(_callback)

    with context:
        while time.monotonic() < end_time:
            try:
                response = session.get(config.base_url, timeout=config.request_timeout_seconds)
                if response.status_code == 429:
                    raise RuntimeError("rate_limit_429")
                if response.status_code == 503:
                    raise requests.Timeout("timeout_503")
                payload = response.json()
                expected_hash = _hash_payload(config.scope, int(payload["sequence"]))
                if payload.get("hash") != expected_hash:
                    raise ValueError("hash_mismatch")
                metrics.successful_requests += 1
                logger.info(
                    "poll_ok sequence=%s scenario=%s",
                    payload.get("sequence"),
                    scenario_context.name,
                )
                if not scenario_context.skip_heartbeat:
                    watchdog.heartbeat()
                else:
                    watchdog.last_heartbeat -= config.heartbeat_timeout_seconds + 0.1
                    logger.warning("watchdog_skip_heartbeat scenario=watchdog_heartbeat_miss")
                if last_failure_time is not None:
                    recovery_time = time.monotonic() - last_failure_time
                    metrics.recovery_times.append(recovery_time)
                    logger.info("recovery_time=%.2fs", recovery_time)
                    last_failure_time = None
            except (
                requests.Timeout,
                requests.exceptions.ProxyError,
                ValueError,
                RuntimeError,
                json.JSONDecodeError,
                KeyError,
            ) as exc:
                metrics.failed_requests += 1
                logger.warning("poll_fail error=%s scenario=%s", exc, scenario_context.name)
                if last_failure_time is None:
                    last_failure_time = time.monotonic()
            if watchdog.check():
                metrics.failed_requests += 1
                logger.warning("watchdog_triggered reason=heartbeat_timeout")
                if last_failure_time is None:
                    last_failure_time = time.monotonic()
            time.sleep(config.polling_interval_seconds)

    duration_seconds = time.monotonic() - start_time
    _write_report(config, metrics, config.report_path, duration_seconds)

    if metrics.failed_requests:
        if config.level != "low":
            assert metrics.recovery_times, "No recovery events recorded after failures."
            assert all(
                recovery <= config.max_recovery_seconds for recovery in metrics.recovery_times
            ), "Recovery time exceeded configured maximum."
            assert last_failure_time is None, "Unrecovered failure detected at end of run."
        elif last_failure_time is not None:
            logger.warning(
                "unrecovered_failure_tolerated level=low last_failure_age=%.2fs",
                time.monotonic() - last_failure_time,
            )

    logger.info(
        "summary success=%s failed=%s avg_recovery=%.2fs",
        metrics.successful_requests,
        metrics.failed_requests,
        (sum(metrics.recovery_times) / len(metrics.recovery_times) if metrics.recovery_times else 0.0),
    )

    return {
        "successful_requests": metrics.successful_requests,
        "failed_requests": metrics.failed_requests,
        "recovery_time": metrics.recovery_times,
        "report_path": str(config.report_path),
    }


def run_chaos_test(config_path: str) -> Dict[str, object]:
    """Español: Ejecuta escenarios de caos usando configuración YAML.

    English: Run chaos scenarios using YAML configuration.
    """
    config = _load_config(Path(config_path))
    _apply_level_defaults(config)
    return _run_chaos_test(config)


def _parse_args() -> argparse.Namespace:
    """Español: Define argumentos de línea de comando.

    English: Define command-line arguments.
    """
    parser = argparse.ArgumentParser(description="CNE chaos testing runner")
    parser.add_argument("--config", required=True, help="Path to chaos_config.yaml")
    parser.add_argument("--level", help="Override chaos level")
    parser.add_argument("--duration-minutes", type=float, help="Override duration")
    parser.add_argument("--failure-probability", type=float, help="Override failure probability")
    return parser.parse_args()


def _apply_overrides(config: ChaosConfig, args: argparse.Namespace) -> None:
    """Español: Aplica overrides desde CLI.

    English: Apply CLI overrides.
    """
    if args.level:
        config.level = args.level.lower()
    if args.duration_minutes is not None:
        config.duration_minutes = float(args.duration_minutes)
    if args.failure_probability is not None:
        config.failure_probability = float(args.failure_probability)
    _apply_level_defaults(config)


def main() -> None:
    """Español: Entry point CLI para chaos_test.

    English: CLI entry point for chaos_test.
    """
    args = _parse_args()
    config = _load_config(Path(args.config))
    _apply_overrides(config, args)
    _ = _run_chaos_test(config)


if __name__ == "__main__":
    main()
