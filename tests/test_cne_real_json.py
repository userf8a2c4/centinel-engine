"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_cne_real_json.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - TestSafeIntCommaStrings
  - TestSanitizeRealCnePayload
  - TestNormalizeRealCneData

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_cne_real_json.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - TestSafeIntCommaStrings
  - TestSanitizeRealCnePayload
  - TestNormalizeRealCneData

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

import json

import pytest

from centinel.core.normalize import (
    PresidentialActa,
    _safe_int,
    _sanitize_raw_payload,
    normalize_snapshot,
    snapshot_to_canonical_json,
)

# ---------------------------------------------------------------------------
# Fixture: CNE JSON structure (names are neutral placeholders — system is candidate-agnostic)
# ---------------------------------------------------------------------------

REAL_CNE_SNAPSHOT_EARLY = {
    "resultados": [
        {
            "partido": "PARTIDO ALPHA",
            "candidato": "CANDIDATO ALPHA",
            "votos": "1,027,090",
            "porcentaje": "38.10",
        },
        {
            "partido": "PARTIDO BETA",
            "candidato": "CANDIDATO BETA",
            "votos": "1,013,050",
            "porcentaje": "37.58",
        },
        {
            "partido": "PARTIDO GAMMA",
            "candidato": "CANDIDATO GAMMA",
            "votos": "485,529",
            "porcentaje": "18.01",
        },
        {
            "partido": "PARTIDO DELTA",
            "candidato": "CANDIDATO DELTA",
            "votos": "22,608",
            "porcentaje": "0.84",
        },
        {
            "partido": "PARTIDO EPSILON",
            "candidato": "CANDIDATO EPSILON",
            "votos": "4,500",
            "porcentaje": "0.17",
        },
    ],
    "estadisticas": {
        "totalizacion_actas": {
            "actas_totales": "19,152",
            "actas_divulgadas": "15,310",
        },
        "distribucion_votos": {
            "validos": "2,552,777",
            "nulos": "93,520",
            "blancos": "49,732",
        },
        "estado_actas_divulgadas": {
            "actas_correctas": "13,121",
            "actas_inconsistentes": "2,189",
        },
    },
}

REAL_CNE_SNAPSHOT_FINAL = {
    "resultados": [
        {
            "partido": "PARTIDO BETA",
            "candidato": "CANDIDATO BETA",
            "votos": "1,298,835",
            "porcentaje": "38.28",
        },
        {
            "partido": "PARTIDO ALPHA",
            "candidato": "CANDIDATO ALPHA",
            "votos": "1,256,428",
            "porcentaje": "37.03",
        },
        {
            "partido": "PARTIDO GAMMA",
            "candidato": "CANDIDATO GAMMA",
            "votos": "618,448",
            "porcentaje": "18.23",
        },
        {
            "partido": "PARTIDO DELTA",
            "candidato": "CANDIDATO DELTA",
            "votos": "25,421",
            "porcentaje": "0.75",
        },
        {
            "partido": "PARTIDO EPSILON",
            "candidato": "CANDIDATO EPSILON",
            "votos": "5,516",
            "porcentaje": "0.16",
        },
    ],
    "estadisticas": {
        "totalizacion_actas": {
            "actas_totales": "19,167",
            "actas_divulgadas": "19,052",
        },
        "distribucion_votos": {
            "validos": "3,204,648",
            "nulos": "119,889",
            "blancos": "68,075",
        },
        "estado_actas_divulgadas": {
            "actas_correctas": "16,279",
            "actas_inconsistentes": "2,773",
        },
    },
}


# ---------------------------------------------------------------------------
# _safe_int: comma-separated string numbers
# ---------------------------------------------------------------------------


class TestSafeIntCommaStrings:
    """Verify _safe_int handles CNE-style comma-separated vote strings."""

    def test_comma_separated_string(self):
        assert _safe_int("1,027,090") == 1027090

    def test_plain_string(self):
        assert _safe_int("485529") == 485529

    def test_string_with_decimals(self):
        assert _safe_int("38.10") == 38

    def test_none(self):
        assert _safe_int(None) == 0


# ---------------------------------------------------------------------------
# _sanitize_raw_payload: real CNE structure
# ---------------------------------------------------------------------------


class TestSanitizeRealCnePayload:
    """Verify sanitization passes real CNE JSON without rejection."""

    def test_early_snapshot_is_valid_json_object(self):
        result = _sanitize_raw_payload(REAL_CNE_SNAPSHOT_EARLY)
        assert isinstance(result, dict)
        assert "resultados" in result
        assert "estadisticas" in result

    def test_final_snapshot_is_valid_json_object(self):
        result = _sanitize_raw_payload(REAL_CNE_SNAPSHOT_FINAL)
        assert isinstance(result, dict)

    def test_as_json_string(self):
        raw_str = json.dumps(REAL_CNE_SNAPSHOT_EARLY)
        result = _sanitize_raw_payload(raw_str)
        assert isinstance(result, dict)
        assert "resultados" in result


# ---------------------------------------------------------------------------
# normalize_snapshot: real CNE data end-to-end
# ---------------------------------------------------------------------------


class TestNormalizeRealCneData:
    """End-to-end normalization of real CNE JSON into canonical Snapshot."""

    def test_early_snapshot_normalizes_successfully(self):
        """Real CNE JSON from 2025-12-03 16:25 must not return None."""
        snapshot = normalize_snapshot(
            REAL_CNE_SNAPSHOT_EARLY,
            department_name="TODOS",
            timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is not None, (
            "normalize_snapshot returned None for real CNE data — "
            "the system would silently discard valid election results!"
        )

    def test_final_snapshot_normalizes_successfully(self):
        """Real CNE JSON from 2025-12-10 17:03 must not return None."""
        snapshot = normalize_snapshot(
            REAL_CNE_SNAPSHOT_FINAL,
            department_name="TODOS",
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is not None, (
            "normalize_snapshot returned None for real CNE data — "
            "the system would silently discard valid election results!"
        )

    def test_candidates_extracted_from_resultados(self):
        """Candidates must be parsed from the 'resultados' array."""
        snapshot = normalize_snapshot(
            REAL_CNE_SNAPSHOT_EARLY,
            department_name="TODOS",
            timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is not None
        assert len(snapshot.candidates) == 5
        # Verify vote parsing handles comma strings
        first = snapshot.candidates[0]
        assert first.votes == 1027090
        assert first.name == "CANDIDATO ALPHA"
        assert first.party == "PARTIDO ALPHA"

    def test_statistics_extracted_from_estadisticas(self):
        """Totals must be extracted from nested estadisticas paths."""
        snapshot = normalize_snapshot(
            REAL_CNE_SNAPSHOT_EARLY,
            department_name="TODOS",
            timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is not None
        assert snapshot.totals.valid_votes == 2552777
        assert snapshot.totals.null_votes == 93520
        assert snapshot.totals.blank_votes == 49732
        # total_votes should be auto-calculated from components
        assert snapshot.totals.total_votes == 2552777 + 93520 + 49732

    def test_canonical_json_is_deterministic(self):
        """Two normalizations of the same input must produce identical JSON."""
        snap1 = normalize_snapshot(
            REAL_CNE_SNAPSHOT_FINAL,
            department_name="TODOS",
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="NATIONAL",
            department_code="00",
        )
        snap2 = normalize_snapshot(
            REAL_CNE_SNAPSHOT_FINAL,
            department_name="TODOS",
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snap1 is not None and snap2 is not None
        json1 = snapshot_to_canonical_json(snap1)
        json2 = snapshot_to_canonical_json(snap2)
        assert json1 == json2

    def test_canonical_json_is_valid(self):
        """Canonical JSON must be parseable."""
        snapshot = normalize_snapshot(
            REAL_CNE_SNAPSHOT_FINAL,
            department_name="TODOS",
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is not None
        canonical = snapshot_to_canonical_json(snapshot)
        parsed = json.loads(canonical)
        assert "meta" in parsed
        assert "candidates" in parsed
        assert len(parsed["candidates"]) == 5
