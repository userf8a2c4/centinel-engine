.PHONY: help quickstart wizard setup install start stop restart status logs \
        init snapshot collect audit analyze summary pipeline \
        security test-stress security-scan test lint \
        test-security test-security-chaos test-security-all

PYTHON_COMMAND ?= python
SERVICE        := scripts/centinel_service.sh

# ══════════════════════════════════════════════════════════════════════════════
#  INICIO RÁPIDO / QUICK START
# ══════════════════════════════════════════════════════════════════════════════

help: ## Muestra esta ayuda / Show this help
	@printf '\n\033[1mCentinel Engine — Comandos disponibles / Available commands\033[0m\n\n'
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf '\n\033[1mEjemplo de inicio rápido / Quick start example:\033[0m\n'
	@printf '  make install   # instalar dependencias\n'
	@printf '  make wizard    # configurar el sistema\n'
	@printf '  make start     # arrancar el pipeline\n\n'

quickstart: ## Todo en uno: instalar + configurar + iniciar / All-in-one: install + configure + start
	@./scripts/bootstrap.sh
	@$(PYTHON_COMMAND) scripts/setup_wizard.py
	@bash $(SERVICE) start

install: ## Instalar dependencias (Poetry o pip) / Install dependencies
	@./scripts/bootstrap.sh

wizard: ## Asistente de configuración interactivo / Interactive configuration wizard
	@$(PYTHON_COMMAND) scripts/setup_wizard.py

setup: wizard ## Alias de wizard / Alias for wizard

# ══════════════════════════════════════════════════════════════════════════════
#  GESTIÓN DEL SERVICIO / SERVICE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

start: ## Iniciar el pipeline en segundo plano (autónomo) / Start pipeline in background
	@bash $(SERVICE) start

stop: ## Detener el pipeline / Stop the pipeline
	@bash $(SERVICE) stop

restart: ## Reiniciar el pipeline / Restart the pipeline
	@bash $(SERVICE) restart

status: ## Ver estado del pipeline / Check pipeline status
	@bash $(SERVICE) status

logs: ## Ver logs en tiempo real (Ctrl-C para salir) / Tail logs live
	@bash $(SERVICE) logs

# ══════════════════════════════════════════════════════════════════════════════
#  OPERACIÓN MANUAL / MANUAL OPERATION
# ══════════════════════════════════════════════════════════════════════════════

init: ## Inicializar configuración y hashes / Initialize config and hashes
	$(PYTHON_COMMAND) scripts/bootstrap.py

snapshot: ## Capturar y hashear snapshot del CNE / Capture and hash CNE snapshot
	$(PYTHON_COMMAND) scripts/download_and_hash.py

collect: ## Recolectar datos / Collect data
	mkdir -p logs
	$(PYTHON_COMMAND) -m scripts.collector 2>&1 | tee logs/collector.log

audit: ## Analizar snapshot actual / Analyze current snapshot
	mkdir -p logs
	$(PYTHON_COMMAND) -m scripts.snapshot 2>&1 | tee logs/audit.log

analyze: ## Correr análisis de reglas / Run rules analysis
	$(PYTHON_COMMAND) scripts/analyze_rules.py

summary: ## Resumir hallazgos / Summarize findings
	$(PYTHON_COMMAND) scripts/summarize_findings.py

pipeline: ## Ejecutar pipeline UNA vez / Run pipeline ONCE
	$(PYTHON_COMMAND) scripts/run_pipeline.py --once

# ══════════════════════════════════════════════════════════════════════════════
#  TESTS Y CALIDAD / TESTS AND QUALITY
# ══════════════════════════════════════════════════════════════════════════════

test: ## Correr todos los tests / Run all tests
	$(PYTHON_COMMAND) -m pytest --import-mode=importlib

test-stress: ## Tests de estrés / Stress tests
	$(PYTHON_COMMAND) -m pytest tests/test_stress.py

lint: ## Linter (flake8 + black) / Lint check
	$(PYTHON_COMMAND) -m flake8 .
	$(PYTHON_COMMAND) -m black --check .

security: ## Escaneo de seguridad + tests / Security scan and tests
	mkdir -p logs
	$(PYTHON_COMMAND) -m bandit -r . -c bandit.yaml --severity-level medium 2>&1 | tee logs/security-bandit.log
	$(PYTHON_COMMAND) -m pytest tests/test_security.py tests/test_attack_logger.py tests/test_advanced_security.py 2>&1 | tee logs/security-tests.log

security-scan: ## Bandit + safety check
	$(PYTHON_COMMAND) -m bandit -r .
	$(PYTHON_COMMAND) -m safety check --full-report -r requirements.txt

test-security: ## Tests de seguridad / Security tests
	$(PYTHON_COMMAND) -m pytest tests/test_attack_logger.py tests/test_advanced_security.py tests/test_security_ecosystem.py

test-security-chaos: ## Tests de caos / Chaos tests
	$(PYTHON_COMMAND) -m pytest tests/chaos/test_security_chaos.py

test-security-all: ## Todos los tests de seguridad / All security tests
	$(PYTHON_COMMAND) -m pytest tests/test_attack_logger.py tests/test_advanced_security.py tests/test_security_ecosystem.py tests/chaos/test_security_chaos.py
