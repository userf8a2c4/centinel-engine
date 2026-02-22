from pathlib import Path

from centinel_engine.cne_endpoint_healer import CNEEndpointHealer


def _build_healer(tmp_path: Path) -> CNEEndpointHealer:
    return CNEEndpointHealer(
        config_path=tmp_path / "endpoints.yaml",
        env_name="test",
        hash_dir=tmp_path / "hashes",
    )


def test_validate_candidates_produces_national_and_departmental_records(tmp_path):
    healer = _build_healer(tmp_path)

    payloads = {
        "https://resultados.cne.hn/presidencial_nacional.json": {
            "nivel": "presidencial",
            "tipo": "nacional",
            "votos": 100,
            "candidatos": [{"nombre": "A", "porcentaje": 50.0}],
        },
        "https://resultados.cne.hn/departamentos/atlantida_presidencial.json": {
            "nivel": "presidencial",
            "departamento": "ATLANTIDA",
            "votos": 20,
            "candidatos": [{"nombre": "B", "porcentaje": 45.0}],
        },
    }

    healer._http_get_json = payloads.__getitem__  # type: ignore[method-assign]

    national, departments = healer._validate_candidates(list(payloads.keys()))

    assert national is not None
    assert national.level == "NACIONAL"
    assert national.department is None

    assert "ATLANTIDA" in departments
    assert departments["ATLANTIDA"].level == "DEPARTAMENTAL"
    assert departments["ATLANTIDA"].department == "ATLANTIDA"


def test_build_resilient_endpoint_set_falls_back_to_existing_endpoints(tmp_path):
    healer = _build_healer(tmp_path)

    existing_national, existing_departments = healer._index_existing_endpoints(
        [
            {
                "url": "https://old.cne.hn/presidencial_nacional.json",
                "level": "NACIONAL",
                "department": None,
                "last_validated": "2026-02-01T00:00:00+00:00",
                "hash": "abc123",
            },
            {
                "url": "https://old.cne.hn/atlantida.json",
                "level": "DEPARTAMENTAL",
                "department": "ATLANTIDA",
                "last_validated": "2026-02-01T00:00:00+00:00",
                "hash": "def456",
            },
        ]
    )

    selected, summary = healer._build_resilient_endpoint_set(
        discovered_national=None,
        discovered_departments={},
        existing_national=existing_national,
        existing_departments=existing_departments,
    )

    assert any(item.level == "NACIONAL" and item.validation_status == "degraded" for item in selected)
    assert any(item.department == "ATLANTIDA" and item.validation_status == "degraded" for item in selected)
    assert summary["degraded_count"] >= 2


def test_extract_script_srcs_fallback_parser_reads_relative_and_absolute_sources(tmp_path):
    healer = _build_healer(tmp_path)

    html = '<html><head><script src="runtime.js"></script><script src="https://cdn.example.com/main.js"></script></head></html>'

    srcs = healer._extract_script_srcs(html)

    assert srcs == ["runtime.js", "https://cdn.example.com/main.js"]


def test_infer_department_matches_urls_with_underscores_and_hyphens(tmp_path):
    healer = _build_healer(tmp_path)

    assert healer._infer_department("https://x/francisco_morazan-presidencial.json", []) == "FRANCISCO MORAZAN"


def test_resolve_animal_mode_thresholds(tmp_path):
    healer = _build_healer(tmp_path)

    assert healer._resolve_animal_mode(0) == "normal"
    assert healer._resolve_animal_mode(2) == "caution"
    assert healer._resolve_animal_mode(5) == "survival"


def test_recommended_interval_for_animal_mode(tmp_path):
    healer = _build_healer(tmp_path)

    assert healer._recommended_interval_for_mode("normal") == 30
    assert healer._recommended_interval_for_mode("caution") == 20
    assert healer._recommended_interval_for_mode("survival") == 10
