"""Chaos testing script for Centinel Engine auto-resume validation."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pytest


REPORT_DATA: Dict[str, Dict[str, str]] = {}
REPORT_DETAILS: Dict[str, Dict[str, str]] = {}
REPORT_PATH = Path(os.environ.get("CHAOS_REPORT_PATH", "chaos_report.md"))


class SimulatedNetworkError(RuntimeError):
    """Raised when the simulated network is unavailable."""


class SimulatedDiskFullError(OSError):
    """Raised when the simulated disk is full."""


class SimulatedBucketError(RuntimeError):
    """Raised when the simulated bucket write fails."""


@dataclass
class PipelineState:
    """Español: Clase PipelineState del módulo chaos_test.py.

    English: PipelineState class defined in chaos_test.py.
    """
    processed: int = 0
    hashes: List[str] = field(default_factory=list)
    last_checkpoint: int = 0


@dataclass
class FakeBucket:
    """Español: Clase FakeBucket del módulo chaos_test.py.

    English: FakeBucket class defined in chaos_test.py.
    """
    base_dir: Path
    force_write_error: bool = False

    def write_checkpoint(self, payload: Dict[str, int]) -> None:
        """Español: Función write_checkpoint del módulo chaos_test.py.

        English: Function write_checkpoint defined in chaos_test.py.
        """
        if self.force_write_error:
            raise SimulatedBucketError("simulated_bucket_write_failure")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "checkpoint.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def corrupt_checkpoint(self) -> None:
        """Español: Función corrupt_checkpoint del módulo chaos_test.py.

        English: Function corrupt_checkpoint defined in chaos_test.py.
        """
        target = self.base_dir / "checkpoint.json"
        target.write_text("{invalid-json", encoding="utf-8")


@dataclass
class FakePipelineRunner:
    """Español: Clase FakePipelineRunner del módulo chaos_test.py.

    English: FakePipelineRunner class defined in chaos_test.py.
    """
    temp_dir: Path
    actas_target: int = 120
    checkpoint_interval: int = 5
    network_available: bool = True
    disk_full: bool = False
    alert_log: List[str] = field(default_factory=list)
    recovery_log: List[str] = field(default_factory=list)
    state: PipelineState = field(default_factory=PipelineState)

    def __post_init__(self) -> None:
        """Español: Función __post_init__ del módulo chaos_test.py.

        English: Function __post_init__ defined in chaos_test.py.
        """
        self.log_path = self.temp_dir / "recovery.log"
        self.checkpoint_path = self.temp_dir / "pipeline_checkpoint.json"
        self.checkpoint_backup_path = self.temp_dir / "pipeline_checkpoint.bak"
        self.bucket = FakeBucket(self.temp_dir / "bucket")
        self.logger = logging.getLogger(f"chaos.{id(self)}")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.log_path)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self.logger.addHandler(handler)

    def start_test_pipeline(self) -> None:
        """Español: Función start_test_pipeline del módulo chaos_test.py.

        English: Function start_test_pipeline defined in chaos_test.py.
        """
        self.logger.info("pipeline_start mode=test")

    def process_until(self, target: int) -> None:
        """Español: Función process_until del módulo chaos_test.py.

        English: Function process_until defined in chaos_test.py.
        """
        while self.state.processed < target:
            self._assert_operational()
            self._process_one()

    def _process_one(self) -> None:
        """Español: Función _process_one del módulo chaos_test.py.

        English: Function _process_one defined in chaos_test.py.
        """
        self.state.processed += 1
        payload = f"acta-{self.state.processed}".encode("utf-8")
        self.state.hashes.append(sha256(payload).hexdigest())
        if self.state.processed % self.checkpoint_interval == 0:
            self._save_checkpoint()

    def _assert_operational(self) -> None:
        """Español: Función _assert_operational del módulo chaos_test.py.

        English: Function _assert_operational defined in chaos_test.py.
        """
        if not self.network_available:
            raise SimulatedNetworkError("network_blocked_ports_80_443")

    def _save_checkpoint(self) -> None:
        """Español: Función _save_checkpoint del módulo chaos_test.py.

        English: Function _save_checkpoint defined in chaos_test.py.
        """
        if self.disk_full:
            raise SimulatedDiskFullError("disk_full")
        payload = {"processed": self.state.processed, "hashes": self.state.hashes}
        self.checkpoint_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        self.checkpoint_backup_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        try:
            self.bucket.write_checkpoint(payload)
        except SimulatedBucketError as exc:
            self._alert("critical_bucket_write_failure")
            self.logger.info("bucket_write_error error=%s", exc)

    def simulate_kill(self) -> None:
        """Español: Función simulate_kill del módulo chaos_test.py.

        English: Function simulate_kill defined in chaos_test.py.
        """
        self.logger.info("failure kill -9")
        self._alert("critical_process_killed")

    def simulate_docker_kill(self) -> None:
        """Español: Función simulate_docker_kill del módulo chaos_test.py.

        English: Function simulate_docker_kill defined in chaos_test.py.
        """
        self.logger.info("failure docker_kill")
        self._alert("critical_container_killed")

    def simulate_docker_stop(self) -> None:
        """Español: Función simulate_docker_stop del módulo chaos_test.py.

        English: Function simulate_docker_stop defined in chaos_test.py.
        """
        self.logger.info("failure docker_stop")
        self._save_checkpoint()

    def simulate_network_cut(self) -> None:
        """Español: Función simulate_network_cut del módulo chaos_test.py.

        English: Function simulate_network_cut defined in chaos_test.py.
        """
        self.logger.info("failure network_cut")
        self.network_available = False

    def simulate_disk_fill(self) -> None:
        """Español: Función simulate_disk_fill del módulo chaos_test.py.

        English: Function simulate_disk_fill defined in chaos_test.py.
        """
        self.logger.info("failure disk_full")
        self.disk_full = True
        filler = self.temp_dir / "disk_fill.bin"
        filler.write_bytes(b"0" * 1024)

    def simulate_bucket_write_failure(self) -> None:
        """Español: Función simulate_bucket_write_failure del módulo chaos_test.py.

        English: Function simulate_bucket_write_failure defined in chaos_test.py.
        """
        self.logger.info("failure bucket_write")
        self.bucket.force_write_error = True

    def simulate_checkpoint_corruption(self) -> None:
        """Español: Función simulate_checkpoint_corruption del módulo chaos_test.py.

        English: Function simulate_checkpoint_corruption defined in chaos_test.py.
        """
        self.logger.info("failure checkpoint_corruption")
        self.bucket.corrupt_checkpoint()
        self.checkpoint_path.write_text("{corrupt}", encoding="utf-8")

    def restart_within(self, timeout_seconds: int = 120) -> None:
        """Español: Función restart_within del módulo chaos_test.py.

        English: Function restart_within defined in chaos_test.py.
        """
        start = time.monotonic()
        while time.monotonic() - start < timeout_seconds:
            try:
                self._recover_from_checkpoint()
                self.logger.info("recovery_complete")
                self.recovery_log.append("recovery_complete")
                return
            except (SimulatedDiskFullError, SimulatedNetworkError) as exc:
                self.logger.info("recovery_waiting error=%s", exc)
                time.sleep(0.01)
        raise TimeoutError("recovery_timeout")

    def _recover_from_checkpoint(self) -> None:
        """Español: Función _recover_from_checkpoint del módulo chaos_test.py.

        English: Function _recover_from_checkpoint defined in chaos_test.py.
        """
        checkpoint = self._load_checkpoint(self.checkpoint_path)
        if not checkpoint:
            checkpoint = self._load_checkpoint(self.checkpoint_backup_path)
        if checkpoint:
            self.state.processed = checkpoint.get("processed", 0)
            self.state.hashes = list(checkpoint.get("hashes", []))
        self.network_available = True
        self.disk_full = False
        self.bucket.force_write_error = False
        self.logger.info("recovery_resume processed=%s", self.state.processed)
        self.recovery_log.append("recovery_resume")

    def _load_checkpoint(self, path: Path) -> Dict[str, int]:
        """Español: Función _load_checkpoint del módulo chaos_test.py.

        English: Function _load_checkpoint defined in chaos_test.py.
        """
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._alert("critical_checkpoint_corrupt")
            self.logger.info("checkpoint_corrupt path=%s", path)
            return {}

    def _alert(self, code: str) -> None:
        """Español: Función _alert del módulo chaos_test.py.

        English: Function _alert defined in chaos_test.py.
        """
        self.alert_log.append(code)
        self.logger.info("alert code=%s", code)


@dataclass
class ChaosScenario:
    """Español: Clase ChaosScenario del módulo chaos_test.py.

    English: ChaosScenario class defined in chaos_test.py.
    """
    name: str
    failure: Callable[[FakePipelineRunner], None]
    expect_alert: bool


def _scenario_kill(runner: FakePipelineRunner) -> None:
    """Español: Función _scenario_kill del módulo chaos_test.py.

    English: Function _scenario_kill defined in chaos_test.py.
    """
    runner.simulate_kill()


def _scenario_docker_kill(runner: FakePipelineRunner) -> None:
    """Español: Función _scenario_docker_kill del módulo chaos_test.py.

    English: Function _scenario_docker_kill defined in chaos_test.py.
    """
    runner.simulate_docker_kill()


def _scenario_docker_stop(runner: FakePipelineRunner) -> None:
    """Español: Función _scenario_docker_stop del módulo chaos_test.py.

    English: Function _scenario_docker_stop defined in chaos_test.py.
    """
    runner.simulate_docker_stop()


def _scenario_network_cut(runner: FakePipelineRunner) -> None:
    """Español: Función _scenario_network_cut del módulo chaos_test.py.

    English: Function _scenario_network_cut defined in chaos_test.py.
    """
    runner.simulate_network_cut()
    with pytest.raises(SimulatedNetworkError):
        runner.process_until(runner.state.processed + 1)


def _scenario_disk_fill(runner: FakePipelineRunner) -> None:
    """Español: Función _scenario_disk_fill del módulo chaos_test.py.

    English: Function _scenario_disk_fill defined in chaos_test.py.
    """
    runner.simulate_disk_fill()
    with pytest.raises(SimulatedDiskFullError):
        runner.process_until(runner.state.processed + runner.checkpoint_interval)


def _scenario_bucket_write(runner: FakePipelineRunner) -> None:
    """Español: Función _scenario_bucket_write del módulo chaos_test.py.

    English: Function _scenario_bucket_write defined in chaos_test.py.
    """
    runner.simulate_bucket_write_failure()
    runner.process_until(runner.state.processed + runner.checkpoint_interval)


def _scenario_checkpoint_corruption(runner: FakePipelineRunner) -> None:
    """Español: Función _scenario_checkpoint_corruption del módulo chaos_test.py.

    English: Function _scenario_checkpoint_corruption defined in chaos_test.py.
    """
    runner.simulate_checkpoint_corruption()


SCENARIOS = [
    ChaosScenario("kill -9", _scenario_kill, True),
    ChaosScenario("docker kill", _scenario_docker_kill, True),
    ChaosScenario("docker stop", _scenario_docker_stop, False),
    ChaosScenario("network cut", _scenario_network_cut, True),
    ChaosScenario("disk fill", _scenario_disk_fill, True),
    ChaosScenario("bucket write failure", _scenario_bucket_write, True),
    ChaosScenario("checkpoint corruption", _scenario_checkpoint_corruption, True),
]


@pytest.fixture()
def pipeline_runner(tmp_path: Path) -> FakePipelineRunner:
    """Español: Función pipeline_runner del módulo chaos_test.py.

    English: Function pipeline_runner defined in chaos_test.py.
    """
    runner = FakePipelineRunner(temp_dir=tmp_path)
    runner.start_test_pipeline()
    return runner


@pytest.fixture()
def report_context(request):
    """Español: Función report_context del módulo chaos_test.py.

    English: Function report_context defined in chaos_test.py.
    """
    details: Dict[str, str] = {}
    REPORT_DETAILS[request.node.nodeid] = details
    return details


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.name for s in SCENARIOS])
def test_chaos_auto_resume(
    scenario: ChaosScenario, pipeline_runner: FakePipelineRunner, report_context
) -> None:
    """Español: Función test_chaos_auto_resume del módulo chaos_test.py.

    English: Function test_chaos_auto_resume defined in chaos_test.py.
    """
    runner = pipeline_runner
    runner.process_until(100)
    before_failure_processed = runner.state.processed
    before_failure_hashes = list(runner.state.hashes)

    scenario.failure(runner)

    runner.restart_within(timeout_seconds=120)
    resume_delta = abs(before_failure_processed - runner.state.processed)
    runner.process_until(runner.actas_target)

    report_context["resume_delta"] = str(resume_delta)
    report_context["processed_total"] = str(runner.state.processed)

    assert resume_delta <= 5
    assert runner.state.hashes[: len(before_failure_hashes)] == before_failure_hashes
    assert any("recovery" in entry for entry in runner.recovery_log)
    assert "recovery_resume" in runner.log_path.read_text(encoding="utf-8")
    if scenario.expect_alert:
        assert runner.alert_log


def pytest_runtest_logreport(report):
    """Español: Función pytest_runtest_logreport del módulo chaos_test.py.

    English: Function pytest_runtest_logreport defined in chaos_test.py.
    """
    if report.when != "call":
        return
    REPORT_DATA[report.nodeid] = {
        "outcome": report.outcome,
        "duration": f"{report.duration:.2f}s",
        "longrepr": report.longreprtext if report.failed else "",
    }


def pytest_sessionfinish(session, exitstatus):
    """Español: Función pytest_sessionfinish del módulo chaos_test.py.

    English: Function pytest_sessionfinish defined in chaos_test.py.
    """
    lines = ["# Chaos Test Report", "", f"Exit status: {exitstatus}", ""]
    for nodeid, result in REPORT_DATA.items():
        details = REPORT_DETAILS.get(nodeid, {})
        lines.append(f"## {nodeid}")
        lines.append(f"- Outcome: {result['outcome']}")
        lines.append(f"- Duration: {result['duration']}")
        for key, value in details.items():
            lines.append(f"- {key}: {value}")
        if result["longrepr"]:
            lines.append("- Failure:")
            lines.append("```\n" + result["longrepr"] + "\n```")
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
