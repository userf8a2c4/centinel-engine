# Scripts

## [ES] Español

Esta carpeta contiene los ejecutables principales del pipeline:

- `bootstrap.py`: inicializa archivos de configuración si no existen.
- `download_and_hash.py`: descarga datos por departamento, normaliza y calcula hash.
- `analyze_rules.py`: analiza series temporales y genera reportes de anomalías.
- `summarize_findings.py`: genera resúmenes diarios (si aplica).
- `run_pipeline.py`: orquesta el pipeline completo en orden y puede correr una vez.
- `cli.py`: utilidades CLI para normalización, hashing y auditorías locales.
- `replay_2025_demo.py`: genera un reporte neutral de diffs para el replay 2025.
- `validate_hashes.py`: valida la cadena de hashes y el anclaje (o simulación).
- `evidence_bundle.py`: construye un bundle reproducible (manifest + Merkle root) para verificación externa.
- `verify_evidence_bundle.py`: verifica hashes/merkle de un bundle y retorna PASS/FAIL determinista.
- `verify_snapshot_bundle.py`: verificación externa 1-click (snapshot + hashchain + reglas + versión de pipeline), con opción de firma Ed25519 y anclaje.

Uso típico:
1. Ejecutar `bootstrap.py` para crear configuración inicial.
2. Ejecutar `download_and_hash.py` para capturar datos.
3. Ejecutar `analyze_rules.py` para generar reportes.
4. Ejecutar `summarize_findings.py` para generar resúmenes.
5. (Alternativa) Ejecutar `run_pipeline.py --once` para el flujo completo.

---

## [EN] English

This folder contains the main pipeline executables:

- `bootstrap.py`: initializes configuration files if missing.
- `download_and_hash.py`: downloads department data, normalizes, and hashes.
- `analyze_rules.py`: analyzes time series and generates anomaly reports.
- `summarize_findings.py`: generates daily summaries (if applicable).
- `run_pipeline.py`: orchestrates the full pipeline in order and can run once.
- `cli.py`: CLI utilities for normalization, hashing, and local audits.
- `replay_2025_demo.py`: generates a neutral diff report for the 2025 replay.
- `validate_hashes.py`: validates the hash chain and anchor (or simulation).
- `evidence_bundle.py`: builds a reproducible bundle (manifest + Merkle root) for external verification.
- `verify_evidence_bundle.py`: verifies bundle hashes/merkle and returns deterministic PASS/FAIL.
- `verify_snapshot_bundle.py`: one-click external verification (snapshot + hashchain + rules + pipeline version), with optional Ed25519 signature and anchor checks.

Typical usage:
1. Run `bootstrap.py` to create initial configuration.
2. Run `download_and_hash.py` to capture data.
3. Run `analyze_rules.py` to generate reports.
4. Run `summarize_findings.py` to produce summaries.
5. (Alternative) Run `run_pipeline.py --once` for the full flow.


Notas fase 2 / Phase 2 notes:
- `hash.py` soporta `--pipeline-version`, `--sign-records`, `--key-path`, `--operator-id` para firmar registros de hash por versión.
- `verify_snapshot_bundle.py` soporta `--require-signature` y `--anchor-log` para validación criptográfica reforzada.
