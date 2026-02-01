.PHONY: init snapshot analyze summary pipeline test-stress security-scan

PYTHON_COMMAND ?= python

init:
	$(PYTHON_COMMAND) scripts/bootstrap.py

snapshot:
	$(PYTHON_COMMAND) scripts/download_and_hash.py

analyze:
	$(PYTHON_COMMAND) scripts/analyze_rules.py

summary:
	$(PYTHON_COMMAND) scripts/summarize_findings.py

pipeline:
	$(PYTHON_COMMAND) scripts/run_pipeline.py --once

test-stress:
	$(PYTHON_COMMAND) -m pytest tests/test_stress.py

security-scan:
	$(PYTHON_COMMAND) -m bandit -r .
	$(PYTHON_COMMAND) -m safety check --full-report -r requirements.txt
