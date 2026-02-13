.PHONY: init snapshot collect audit analyze summary pipeline test-stress security-scan test lint test-security test-security-chaos test-security-all

PYTHON_COMMAND ?= python

init:
	$(PYTHON_COMMAND) scripts/bootstrap.py

snapshot:
	$(PYTHON_COMMAND) scripts/download_and_hash.py

collect:
	mkdir -p logs
	$(PYTHON_COMMAND) -m scripts.collector 2>&1 | tee logs/collector.log

audit:
	mkdir -p logs
	$(PYTHON_COMMAND) -m scripts.snapshot 2>&1 | tee logs/audit.log

analyze:
	$(PYTHON_COMMAND) scripts/analyze_rules.py

summary:
	$(PYTHON_COMMAND) scripts/summarize_findings.py

pipeline:
	$(PYTHON_COMMAND) scripts/run_pipeline.py --once

test-stress:
	$(PYTHON_COMMAND) -m pytest tests/test_stress.py

test:
	$(PYTHON_COMMAND) -m pytest --import-mode=importlib

lint:
	$(PYTHON_COMMAND) -m flake8 .
	$(PYTHON_COMMAND) -m black --check .

security-scan:
	$(PYTHON_COMMAND) -m bandit -r .
	$(PYTHON_COMMAND) -m safety check --full-report -r requirements.txt


test-security:
	$(PYTHON_COMMAND) -m pytest tests/test_attack_logger.py tests/test_advanced_security.py tests/test_security_ecosystem.py

test-security-chaos:
	$(PYTHON_COMMAND) -m pytest tests/chaos/test_security_chaos.py

test-security-all:
	$(PYTHON_COMMAND) -m pytest tests/test_attack_logger.py tests/test_advanced_security.py tests/test_security_ecosystem.py tests/chaos/test_security_chaos.py
