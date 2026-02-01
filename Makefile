.PHONY: init snapshot analyze summary pipeline scan-security

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

scan-security:
	gh workflow run security-scan.yml
