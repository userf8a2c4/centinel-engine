"""English: Auto-discovery and self-healing module for CNE presidential endpoints.
Español: Módulo de autodescubrimiento y autocuración para endpoints presidenciales del CNE.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests
import yaml

EXPECTED_DEPARTMENTS = [
    "ATLANTIDA",
    "CHOLUTECA",
    "COLON",
    "COMAYAGUA",
    "COPAN",
    "CORTES",
    "EL PARAISO",
    "FRANCISCO MORAZAN",
    "GRACIAS A DIOS",
    "INTIBUCA",
    "ISLAS DE LA BAHIA",
    "LA PAZ",
    "LEMPIRA",
    "OCOTEPEQUE",
    "OLANCHO",
    "SANTA BARBARA",
    "VALLE",
    "YORO",
]

PRESIDENTIAL_HINT_KEYS = {
    "nivel",
    "tipo",
    "presidente",
    "votos",
    "candidatos",
    "departamento",
    "total_votos",
    "porcentaje",
}

PRESIDENTIAL_HINT_VALUES = {
    "presidencial",
    "presidente",
    "presidency",
    "nacional",
}

JSON_URL_PATTERN = re.compile(r"(?:https?:)?//[^\s\"'`<>]+?\.json(?:\?[^\s\"'`<>]*)?|/[^\s\"'`<>]+?\.json(?:\?[^\s\"'`<>]*)?")

DEFAULT_TIMEOUT = 12
DEFAULT_HEADERS = {
    "User-Agent": "Centinel-Engine-Healer/9.0",
    "Accept": "application/json, text/javascript, */*;q=0.8",
}


HONEY_BADGER_THRESHOLDS = {
    "normal": 0,
    "caution": 2,
    "survival": 4,
}

HONEY_BADGER_INTERVALS = {
    "normal": 30,
    "caution": 20,
    "survival": 10,
}


@dataclass(frozen=True)
class EndpointRecord:
    """English: Canonical endpoint metadata.
    Español: Metadatos canónicos del endpoint.
    """

    url: str
    level: str
    department: str | None
    last_validated: str
    hash: str
    validation_status: str = "healthy"
    source: str = "discovered"
    last_error: Optional[str] = None


class CNEEndpointHealer:
    """English: Discover, validate, and self-heal CNE endpoint configuration.
    Español: Descubre, valida y autocura la configuración de endpoints CNE.
    """

    def __init__(
        self,
        config_path: Path | str,
        env_name: str | None = None,
        hash_dir: Path | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        resolved_config_path = Path(config_path)
        inferred_env = resolved_config_path.parent.name or "default"

        self.config_path = resolved_config_path
        self.env_name = env_name or inferred_env
        self.hash_dir = hash_dir or Path("hashes/endpoints")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.logger = logging.getLogger(f"cne_endpoint_healer.{self.env_name}")

    def heal(self) -> dict[str, Any]:
        """English: Alias to keep backward compatibility with healer naming used by schedulers.
        Español: Alias para mantener compatibilidad con el nombre heal usado por schedulers.
        """

        return self.run()

    def deep_validate(self, healing_result: dict[str, Any]) -> bool:
        """English: Perform strict post-heal validation checks on endpoint health metrics.
        Español: Ejecuta validaciones estrictas post-curación sobre métricas de salud de endpoints.
        """

        has_national = healing_result.get("healthy_count", 0) > 0
        missing_departments = healing_result.get("missing_departments", [])
        return bool(has_national and not missing_departments)

    def heal_proactive(self, force: bool = False) -> dict[str, Any]:
        """English: Execute proactive healing with timing gate, deep validation, and completeness checks.
        Español: Ejecuta curación proactiva con compuerta temporal, validación profunda y chequeos de completitud.
        """

        config = self._load_config()
        healing_cfg = config.setdefault("healing", {})
        now = datetime.now(timezone.utc)

        last_success_dt = self._parse_iso8601(healing_cfg.get("last_successful_scan"))
        elapsed_minutes = ((now - last_success_dt).total_seconds() / 60) if last_success_dt else None
        must_force_by_staleness = elapsed_minutes is None or elapsed_minutes > 45

        if not force and elapsed_minutes is not None and elapsed_minutes <= 30:
            message = "Skipping proactive scan because last successful scan is still fresh"
            self.logger.info("🟨 %s (elapsed_minutes=%.2f)", message, elapsed_minutes)
            return {
                "environment": self.env_name,
                "skipped": True,
                "reason": message,
                "elapsed_minutes": elapsed_minutes,
                "animal_mode": str(healing_cfg.get("animal_mode", "normal")),
                "recommended_interval_minutes": int(healing_cfg.get("recommended_interval_minutes", healing_cfg.get("interval_minutes", 30))),
                "trusted_for_production": bool(healing_cfg.get("trusted_for_production", False)),
                "safe_mode_active": bool(healing_cfg.get("safe_mode_active", False)),
            }

        result = self.heal()
        deep_validation_ok = self.deep_validate(result)
        completeness_ok = self._is_completeness_ok(result)
        scan_status = "success" if deep_validation_ok and completeness_ok else "degraded"

        prior_failures = int(healing_cfg.get("consecutive_failures", 0) or 0)
        consecutive_failures = 0 if scan_status == "success" else prior_failures + 1
        animal_mode = self._resolve_animal_mode(consecutive_failures)
        recommended_interval_minutes = self._recommended_interval_for_mode(animal_mode)
        trusted_for_production = bool(scan_status == "success" and deep_validation_ok and completeness_ok)
        safe_mode_active = (not trusted_for_production) or animal_mode == "survival"
        untrusted_reason = None if trusted_for_production else "deep_validation_or_completeness_failed"

        result.update(
            {
                "skipped": False,
                "forced": bool(force or must_force_by_staleness),
                "deep_validation_ok": deep_validation_ok,
                "completeness_ok": completeness_ok,
                "scan_status": scan_status,
                "animal_mode": animal_mode,
                "recommended_interval_minutes": recommended_interval_minutes,
                "consecutive_failures": consecutive_failures,
                "trusted_for_production": trusted_for_production,
                "safe_mode_active": safe_mode_active,
                "untrusted_reason": untrusted_reason,
            }
        )

        scan_hash_payload = {
            "timestamp": now.isoformat(),
            "environment": self.env_name,
            "result": result,
        }
        scan_hash = hashlib.sha256(json.dumps(scan_hash_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

        healing_cfg.update(
            {
                "interval_minutes": int(healing_cfg.get("interval_minutes", 30)),
                "last_scan_at": now.isoformat(),
                "last_scan_status": scan_status,
                "last_scan_hash": scan_hash,
                "last_scan_result": result,
                "consecutive_failures": consecutive_failures,
                "animal_mode": animal_mode,
                "recommended_interval_minutes": recommended_interval_minutes,
                "trusted_for_production": trusted_for_production,
                "safe_mode_active": safe_mode_active,
                "last_untrusted_reason": untrusted_reason,
            }
        )
        if scan_status == "success":
            healing_cfg["last_successful_scan"] = now.isoformat()
        if trusted_for_production:
            healing_cfg["last_trusted_scan"] = now.isoformat()

        self._persist_full_config(config)
        self.logger.info("🔁 Proactive scan stored with hash=%s status=%s", scan_hash, scan_status)
        return result

    def run(self) -> dict[str, Any]:
        """English: Execute full auto-discovery and self-healing cycle.
        Español: Ejecuta el ciclo completo de autodescubrimiento y autocuración.
        """

        config = self._load_config()
        main_url = config["cne"]["main_url"]
        self.logger.info("🔎 Starting endpoint discovery for %s", main_url)

        discovered = self._discover_endpoint_candidates(main_url)
        discovered_national, discovered_departments = self._validate_candidates(discovered)
        existing_national, existing_departments = self._index_existing_endpoints(config["cne"].get("presidential_endpoints", []))

        validated, summary = self._build_resilient_endpoint_set(
            discovered_national=discovered_national,
            discovered_departments=discovered_departments,
            existing_national=existing_national,
            existing_departments=existing_departments,
        )

        stored_signature = self._endpoint_signature(config["cne"].get("presidential_endpoints", []))
        discovered_signature = self._endpoint_signature([record.__dict__ for record in validated])
        stored_summary = config["cne"].get("validation_summary", {})
        changed = stored_signature != discovered_signature or stored_summary != summary

        config["cne"]["validation_summary"] = summary
        if changed:
            self.logger.warning("🩺 Endpoint change detected, applying self-healing update")
            self._write_config(config, validated)
        else:
            self.logger.info("✅ Endpoint set unchanged; config remains intact")

        history = self._write_hash_history(validated, changed, summary)
        return {
            "environment": self.env_name,
            "changed": changed,
            "count": len(validated),
            "healthy_count": summary.get("healthy_count", 0),
            "degraded_count": summary.get("degraded_count", 0),
            "missing_departments": summary.get("missing_departments", []),
            "history_file": str(history),
        }

    def _load_config(self) -> dict[str, Any]:
        """English: Load YAML config, bootstrap defaults, and validate shape.
        Español: Carga YAML, inicializa valores por defecto y valida la estructura.
        """

        if self.config_path.exists():
            config = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        else:
            config = {}

        config.setdefault("cne", {})
        config.setdefault("healing", {})
        config["cne"].setdefault("main_url", "https://resultados2029.cne.hn/")
        config["cne"].setdefault("presidential_endpoints", [])
        config["cne"].setdefault("config_sha256", "")
        config["healing"].setdefault("interval_minutes", 30)
        config["healing"].setdefault("last_successful_scan", None)
        config["healing"].setdefault("consecutive_failures", 0)
        config["healing"].setdefault("animal_mode", "normal")
        config["healing"].setdefault("safe_mode_active", False)
        config["healing"].setdefault("trusted_for_production", False)
        config["healing"].setdefault("last_trusted_scan", None)
        config["healing"].setdefault("last_untrusted_reason", None)

        if not isinstance(config["cne"]["presidential_endpoints"], list):
            raise ValueError("Invalid config: presidential_endpoints must be a list")

        if config["cne"].get("config_sha256"):
            expected_hash = self._config_hash(config)
            stored_hash = str(config["cne"]["config_sha256"])
            if stored_hash != expected_hash:
                self.logger.warning(
                    "⚠️ Config hash mismatch in %s (stored=%s, expected=%s)",
                    self.config_path,
                    stored_hash,
                    expected_hash,
                )

        return config

    def _discover_endpoint_candidates(self, main_url: str) -> list[str]:
        """English: Parse main page and Angular bundles to collect JSON endpoint candidates.
        Español: Analiza página principal y bundles Angular para detectar endpoints JSON candidatos.
        """

        html = self._http_get_text(main_url)

        bundles: list[str] = []
        try:
            # English: Prefer BeautifulSoup when available for robust HTML parsing.
            # Español: Preferir BeautifulSoup cuando está disponible para parseo HTML robusto.
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for script in soup.select("script[src]"):
                src = script.get("src", "").strip()
                if not src:
                    continue
                bundles.append(urljoin(main_url, src))
        except ImportError:
            # English: Fallback parser keeps auto-discovery operational without extra dependency.
            # Español: Parser fallback mantiene autodescubrimiento operativo sin dependencia extra.
            for src in self._extract_script_srcs(html):
                bundles.append(urljoin(main_url, src))

        raw_matches = set(JSON_URL_PATTERN.findall(html))
        for bundle_url in bundles:
            try:
                bundle_text = self._http_get_text(bundle_url)
            except requests.RequestException as exc:
                self.logger.warning("⚠️ Failed bundle fetch %s (%s)", bundle_url, exc)
                continue
            raw_matches.update(JSON_URL_PATTERN.findall(bundle_text))

        candidates = sorted({self._normalize_url(main_url, value) for value in raw_matches if value})
        self.logger.info("📦 Candidate JSON endpoints discovered: %s", len(candidates))
        return candidates

    def _validate_candidates(self, candidates: list[str]) -> tuple[EndpointRecord | None, dict[str, EndpointRecord]]:
        """English: Validate discovered candidates and return individual healthy endpoint matches.
        Español: Valida candidatos descubiertos y devuelve coincidencias sanas por endpoint individual.
        """

        national: EndpointRecord | None = None
        per_department: dict[str, EndpointRecord] = {}

        for candidate in candidates:
            try:
                payload = self._http_get_json(candidate)
            except requests.RequestException as exc:
                self.logger.warning("⚠️ Endpoint unavailable %s (%s)", candidate, exc)
                continue
            except ValueError as exc:
                self.logger.warning("⚠️ Invalid JSON %s (%s)", candidate, exc)
                continue

            if not self._looks_presidential(payload):
                continue

            keys, values = self._collect_schema_tokens(payload)
            level = self._infer_level(candidate, keys, values)
            department = self._infer_department(candidate, values)
            record = EndpointRecord(
                url=candidate,
                level=level,
                department=department,
                last_validated=datetime.now(timezone.utc).isoformat(),
                hash=self._payload_hash(payload),
                validation_status="healthy",
                source="discovered",
            )

            if level in {"NACIONAL", "PRESIDENCIAL"} and national is None:
                national = replace(record, level="NACIONAL", department=None)
                continue

            if department and department in EXPECTED_DEPARTMENTS and department not in per_department:
                per_department[department] = replace(record, level="DEPARTAMENTAL")

        self.logger.info("✅ Individually validated discovered endpoints: national=%s, departmental=%s", bool(national), len(per_department))
        return national, per_department

    def _index_existing_endpoints(
        self,
        raw_endpoints: list[dict[str, Any]],
    ) -> tuple[EndpointRecord | None, dict[str, EndpointRecord]]:
        """English: Index existing config endpoints to enable fallback when one candidate fails.
        Español: Indexa endpoints existentes para habilitar fallback cuando falle un candidato.
        """

        national: EndpointRecord | None = None
        per_department: dict[str, EndpointRecord] = {}
        for item in raw_endpoints:
            record = EndpointRecord(
                url=str(item.get("url", "")),
                level=str(item.get("level", "DEPARTAMENTAL")),
                department=item.get("department"),
                last_validated=str(item.get("last_validated", "")),
                hash=str(item.get("hash", "")),
                validation_status=str(item.get("validation_status", "stale")),
                source=str(item.get("source", "config")),
                last_error=item.get("last_error"),
            )
            if record.level.upper() == "NACIONAL" and national is None:
                national = EndpointRecord(**{**record.__dict__, "level": "NACIONAL", "department": None})
                continue
            if record.department and record.department in EXPECTED_DEPARTMENTS and record.department not in per_department:
                per_department[record.department] = EndpointRecord(**{**record.__dict__, "level": "DEPARTAMENTAL"})
        return national, per_department

    def _build_resilient_endpoint_set(
        self,
        discovered_national: EndpointRecord | None,
        discovered_departments: dict[str, EndpointRecord],
        existing_national: EndpointRecord | None,
        existing_departments: dict[str, EndpointRecord],
    ) -> tuple[list[EndpointRecord], dict[str, Any]]:
        """English: Build resilient endpoint set with per-endpoint fallback instead of global failure.
        Español: Construye set resiliente con fallback por endpoint en vez de fallo global.
        """

        now_iso = datetime.now(timezone.utc).isoformat()
        selected: list[EndpointRecord] = []
        degraded_count = 0

        national = discovered_national
        if national is None and existing_national is not None:
            degraded_count += 1
            national = EndpointRecord(
                url=existing_national.url,
                level="NACIONAL",
                department=None,
                last_validated=existing_national.last_validated or now_iso,
                hash=existing_national.hash,
                validation_status="degraded",
                source="fallback_config",
                last_error="National endpoint missing in current discovery; using previous known endpoint.",
            )
        if national:
            selected.append(national)

        missing_departments: list[str] = []
        for department in EXPECTED_DEPARTMENTS:
            if department in discovered_departments:
                selected.append(discovered_departments[department])
                continue

            fallback = existing_departments.get(department)
            if fallback:
                degraded_count += 1
                selected.append(
                    EndpointRecord(
                        url=fallback.url,
                        level="DEPARTAMENTAL",
                        department=department,
                        last_validated=fallback.last_validated or now_iso,
                        hash=fallback.hash,
                        validation_status="degraded",
                        source="fallback_config",
                        last_error=f"Departmental endpoint {department} missing in current discovery; using previous known endpoint.",
                    )
                )
                continue

            missing_departments.append(department)

        healthy_count = len([item for item in selected if item.validation_status == "healthy"])
        summary = {
            "total_selected": len(selected),
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "missing_departments": missing_departments,
            "national_present": any(item.level == "NACIONAL" for item in selected),
            "updated_at": now_iso,
        }

        if missing_departments:
            self.logger.error("❌ Missing departments without fallback: %s", ", ".join(missing_departments))
        if not summary["national_present"]:
            self.logger.error("❌ No national endpoint available even after fallback")

        self.logger.info(
            "🧭 Resilient selection done: total=%s healthy=%s degraded=%s missing=%s",
            summary["total_selected"],
            summary["healthy_count"],
            summary["degraded_count"],
            len(summary["missing_departments"]),
        )
        return selected, summary

    def _write_config(self, config: dict[str, Any], endpoints: list[EndpointRecord]) -> None:
        """English: Persist healed endpoint map plus forensic config hash.
        Español: Persiste mapa curado de endpoints y hash forense de configuración.
        """

        config["cne"]["presidential_endpoints"] = [record.__dict__ for record in endpoints]
        config["cne"]["config_sha256"] = self._config_hash(config)
        self._persist_full_config(config)
        self.logger.info("💾 Config healed and saved to %s", self.config_path)

    def _persist_full_config(self, config: dict[str, Any]) -> None:
        """English: Persist complete endpoint configuration including healing metadata.
        Español: Persiste la configuración completa de endpoints incluyendo metadatos de curación.
        """

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def _write_hash_history(self, endpoints: list[EndpointRecord], changed: bool, summary: dict[str, Any]) -> Path:
        """English: Save timestamped hash-chain record for endpoint integrity audits.
        Español: Guarda registro con cadena de hash para auditorías de integridad.
        """

        self.hash_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        prior_file = (sorted(self.hash_dir.glob("*.json")) or [None])[-1]

        previous_hash = "GENESIS"
        if prior_file:
            try:
                previous_hash = json.loads(prior_file.read_text(encoding="utf-8")).get("chain_hash", "GENESIS")
            except (json.JSONDecodeError, OSError) as exc:
                self.logger.warning("Failed to read or parse prior hash file %s: %s", prior_file, exc)
                previous_hash = "GENESIS"

        payload = {
            "timestamp": timestamp,
            "environment": self.env_name,
            "changed": changed,
            "endpoints": [record.__dict__ for record in endpoints],
            "validation_summary": summary,
        }
        state_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        chain_hash = hashlib.sha256(f"{previous_hash}:{state_hash}".encode("utf-8")).hexdigest()

        payload["previous_hash"] = previous_hash
        payload["state_hash"] = state_hash
        payload["chain_hash"] = chain_hash

        history_path = self.hash_dir / f"endpoints_{self.env_name}_{timestamp}.json"
        history_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.hash_dir / f"endpoints_{self.env_name}_{timestamp}.sha256").write_text(
            f"{chain_hash}  {history_path.name}\n",
            encoding="utf-8",
        )
        self.logger.info("🔐 Hash-chain record written to %s", history_path)
        return history_path

    def _http_get_text(self, url: str) -> str:
        """English: Fetch URL as text with strict timeout and clear exception context.
        Español: Descarga URL como texto con timeout estricto y contexto claro de excepción.
        """

        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _http_get_json(self, url: str) -> Any:
        """English: Fetch URL as JSON with strict timeout and schema-neutral parsing.
        Español: Descarga URL como JSON con timeout estricto y parseo neutral al esquema.
        """

        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _extract_script_srcs(html: str) -> list[str]:
        """English: Extract script src URLs from HTML when BeautifulSoup is unavailable.
        Español: Extrae URLs src de scripts desde HTML cuando BeautifulSoup no está disponible.
        """

        pattern = re.compile(r"<script[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
        return [match.strip() for match in pattern.findall(html) if match.strip()]

    @staticmethod
    def _normalize_url(base_url: str, candidate: str) -> str:
        """English: Normalize relative/protocol-less URLs into absolute URL form.
        Español: Normaliza URLs relativas/sin protocolo a formato absoluto.
        """

        normalized = candidate.strip().strip('"').strip("'")
        if normalized.startswith("//"):
            normalized = f"https:{normalized}"
        return urljoin(base_url, normalized)

    @staticmethod
    def _payload_hash(payload: Any) -> str:
        """English: Calculate deterministic SHA-256 hash for endpoint payload.
        Español: Calcula hash SHA-256 determinístico para el payload del endpoint.
        """

        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_token(value: str) -> str:
        """English: Normalize accented and case-variant tokens for robust matching.
        Español: Normaliza tokens con acentos y variantes de mayúsculas/minúsculas.
        """

        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"[_\-]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip().upper()

    @staticmethod
    def _collect_schema_tokens(payload: Any) -> tuple[set[str], list[str]]:
        """English: Recursively collect key/value tokens for structure inference.
        Español: Recolecta recursivamente tokens de claves/valores para inferir estructura.
        """

        keys: set[str] = set()
        values: list[str] = []

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    keys.add(CNEEndpointHealer._normalize_token(str(key)).lower())
                    _walk(value)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)
            else:
                values.append(CNEEndpointHealer._normalize_token(str(node)))

        _walk(payload)
        return keys, values

    @staticmethod
    def _looks_presidential(payload: Any) -> bool:
        """English: Validate presidential JSON structure using key overlap threshold.
        Español: Valida estructura presidencial JSON usando umbral de coincidencia de claves.
        """

        keys, values = CNEEndpointHealer._collect_schema_tokens(payload)
        overlap = len(PRESIDENTIAL_HINT_KEYS.intersection(keys))
        values_corpus = " ".join(values)
        has_presidential_hint = any(token.upper() in values_corpus for token in PRESIDENTIAL_HINT_VALUES)
        has_results_shape = any(key in keys for key in {"votos", "candidatos", "total_votos", "porcentaje"})
        return overlap >= 3 and (has_presidential_hint or has_results_shape)

    @staticmethod
    def _infer_level(url: str, keys: set[str], values: list[str]) -> str:
        """English: Infer endpoint level (national/departmental) by URL and JSON tokens.
        Español: Infiere nivel del endpoint (nacional/departamental) por URL y tokens JSON.
        """

        corpus = " ".join([url.upper(), " ".join(values), " ".join(k.upper() for k in keys)])
        if "NACIONAL" in corpus or "PRESIDENCIAL" in corpus:
            return "NACIONAL"
        return "DEPARTAMENTAL"

    @staticmethod
    def _infer_department(url: str, values: list[str]) -> str | None:
        """English: Infer Honduras department from URL or payload scalar values.
        Español: Infiere departamento de Honduras desde URL o valores escalares del payload.
        """

        corpus = f"{CNEEndpointHealer._normalize_token(url)} {' '.join(values)}"
        for department in EXPECTED_DEPARTMENTS:
            if department in corpus:
                return department
        return None

    @staticmethod
    def _endpoint_signature(endpoints: list[dict[str, Any]]) -> str:
        """English: Build deterministic signature for endpoint set comparison.
        Español: Construye firma determinística para comparar el conjunto de endpoints.
        """

        canonical = [
            {
                "url": item.get("url"),
                "level": item.get("level"),
                "department": item.get("department"),
                "hash": item.get("hash"),
            }
            for item in endpoints
        ]
        return hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    @staticmethod
    def _config_hash(config: dict[str, Any]) -> str:
        """English: Calculate integrity hash for persisted endpoint config structure.
        Español: Calcula hash de integridad para la estructura persistida del config.
        """

        target = {
            "cne": {
                "main_url": config.get("cne", {}).get("main_url"),
                "presidential_endpoints": config.get("cne", {}).get("presidential_endpoints", []),
            }
        }
        return hashlib.sha256(yaml.safe_dump(target, sort_keys=True, allow_unicode=True).encode("utf-8")).hexdigest()

    @staticmethod
    def is_production_safe(scan_result: dict[str, Any]) -> bool:
        """English: Determine if proactive scan result is safe for production fetch execution.
        Español: Determina si el resultado proactivo es seguro para ejecutar fetch de producción.
        """

        return scan_result.get("trusted_for_production", False) and not scan_result.get("safe_mode_active", False)


    @staticmethod
    def _resolve_animal_mode(consecutive_failures: int) -> str:
        """English: Map failure streak to Honey-Badger operational mode.
        Español: Mapea racha de fallos al modo operativo Tejón (Honey-Badger).
        """

        if consecutive_failures >= HONEY_BADGER_THRESHOLDS["survival"]:
            return "survival"
        if consecutive_failures >= HONEY_BADGER_THRESHOLDS["caution"]:
            return "caution"
        return "normal"

    @staticmethod
    def _recommended_interval_for_mode(mode: str) -> int:
        """English: Return recommended proactive interval for the selected animal mode.
        Español: Devuelve intervalo proactivo recomendado para el modo animal seleccionado.
        """

        return int(HONEY_BADGER_INTERVALS.get(mode, 30))


    @staticmethod
    def _parse_iso8601(value: Any) -> datetime | None:
        """English: Parse ISO-8601 timestamps from persisted healing metadata.
        Español: Parsea timestamps ISO-8601 desde metadatos persistidos de curación.
        """

        if not value:
            return None
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc)
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized).astimezone(timezone.utc)
            except ValueError:
                return None
        return None

    @staticmethod
    def _is_completeness_ok(result: dict[str, Any]) -> bool:
        """English: Validate completeness: no missing departments and no degraded entries.
        Español: Valida completitud: sin departamentos faltantes y sin entradas degradadas.
        """

        missing_departments = result.get("missing_departments", [])
        degraded_count = int(result.get("degraded_count", 0))
        return not missing_departments and degraded_count == 0


def run_endpoint_healer_for_env(env: str) -> dict[str, Any]:
    """English: Run healer for a single environment file.
    Español: Ejecuta el healer para un archivo de entorno específico.
    """

    config_path = Path("config") / env / "endpoints.yaml"
    healer = CNEEndpointHealer(
        config_path=config_path,
        env_name=env,
        hash_dir=Path("hashes/endpoints"),
    )
    return healer.run()


def run_endpoint_healer() -> list[dict[str, Any]]:
    """English: Run healer for both dev and prod endpoint configurations.
    Español: Ejecuta el healer para configuraciones de endpoints dev y prod.
    """

    results = []
    for env in ("dev", "prod"):
        results.append(run_endpoint_healer_for_env(env))
    return results


if __name__ == "__main__":
    """English: Manual execution entrypoint for local operational testing.
    Español: Punto de entrada manual para pruebas operativas locales.
    """

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    output = run_endpoint_healer()
    print(json.dumps(output, ensure_ascii=False, indent=2))
