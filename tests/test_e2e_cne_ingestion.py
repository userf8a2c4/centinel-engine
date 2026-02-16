"""Prueba end-to-end: ingesta de JSON real del CNE → DB → API → hashchain.

Simula el flujo completo de producción usando los 3 snapshots reales del CNE
(temprano, medio, final) para verificar que el sistema sobrevive datos en vivo.

End-to-end test: real CNE JSON ingestion → DB → API → hashchain.

Simulates the full production flow using 3 real CNE snapshots (early, mid, final)
to verify the system survives live data.
"""

import json

import pytest

from sentinel.core.hashchain import compute_hash
from sentinel.core.normalize import normalize_snapshot, snapshot_to_canonical_json
from sentinel.core.storage import LocalSnapshotStore
from sentinel.api.main import fetch_latest_snapshot, fetch_snapshot_by_hash, verify_hashchain


# ---------------------------------------------------------------------------
# Real CNE snapshots (verbatim from hnd-electoral-audit-2025/data/)
# ---------------------------------------------------------------------------

SNAPSHOT_DEC03_1625 = {
    "resultados": [
        {"partido": "PARTIDO LIBERAL DE HONDURAS", "candidato": "SALVADOR ALEJANDRO CESAR NASRALLA SALUM", "votos": "1,027,090", "porcentaje": "38.10"},
        {"partido": "PARTIDO NACIONAL DE HONDURAS", "candidato": "NASRY JUAN ASFURA ZABLAH", "votos": "1,013,050", "porcentaje": "37.58"},
        {"partido": "PARTIDO LIBERTAD Y REFUNDACION", "candidato": "RIXI RAMONA MONCADA GODOY", "votos": "485,529", "porcentaje": "18.01"},
        {"partido": "PARTIDO INNOVACION Y UNIDAD SOCIAL DEMOCRATA", "candidato": "JORGE NELSON AVILA GUTIERREZ", "votos": "22,608", "porcentaje": "0.84"},
        {"partido": "PARTIDO DEMOCRATA CRISTIANO DE HONDURAS", "candidato": "MARIO ENRIQUE RIVERA CALLEJAS", "votos": "4,500", "porcentaje": "0.17"},
    ],
    "estadisticas": {
        "totalizacion_actas": {"actas_totales": "19,152", "actas_divulgadas": "15,310"},
        "distribucion_votos": {"validos": "2,552,777", "nulos": "93,520", "blancos": "49,732"},
        "estado_actas_divulgadas": {"actas_correctas": "13,121", "actas_inconsistentes": "2,189"},
    },
}

SNAPSHOT_DEC06_0400 = {
    "resultados": [
        {"partido": "PARTIDO NACIONAL DE HONDURAS", "candidato": "NASRY JUAN ASFURA ZABLAH", "votos": "1,132,321", "porcentaje": "38.01"},
        {"partido": "PARTIDO LIBERAL DE HONDURAS", "candidato": "SALVADOR ALEJANDRO CESAR NASRALLA SALUM", "votos": "1,112,570", "porcentaje": "37.35"},
        {"partido": "PARTIDO LIBERTAD Y REFUNDACION", "candidato": "RIXI RAMONA MONCADA GODOY", "votos": "543,675", "porcentaje": "18.25"},
        {"partido": "PARTIDO INNOVACION Y UNIDAD SOCIAL DEMOCRATA", "candidato": "JORGE NELSON AVILA GUTIERREZ", "votos": "23,398", "porcentaje": "0.79"},
        {"partido": "PARTIDO DEMOCRATA CRISTIANO DE HONDURAS", "candidato": "MARIO ENRIQUE RIVERA CALLEJAS", "votos": "4,882", "porcentaje": "0.16"},
    ],
    "estadisticas": {
        "totalizacion_actas": {"actas_totales": "19,152", "actas_divulgadas": "16,858"},
        "distribucion_votos": {"validos": "2,816,846", "nulos": "103,926", "blancos": "57,866"},
        "estado_actas_divulgadas": {"actas_correctas": "14,451", "actas_inconsistentes": "2,407"},
    },
}

SNAPSHOT_DEC10_1703 = {
    "resultados": [
        {"partido": "PARTIDO NACIONAL DE HONDURAS", "candidato": "NASRY JUAN ASFURA ZABLAH", "votos": "1,298,835", "porcentaje": "38.28"},
        {"partido": "PARTIDO LIBERAL DE HONDURAS", "candidato": "SALVADOR ALEJANDRO CESAR NASRALLA SALUM", "votos": "1,256,428", "porcentaje": "37.03"},
        {"partido": "PARTIDO LIBERTAD Y REFUNDACION", "candidato": "RIXI RAMONA MONCADA GODOY", "votos": "618,448", "porcentaje": "18.23"},
        {"partido": "PARTIDO INNOVACION Y UNIDAD SOCIAL DEMOCRATA", "candidato": "JORGE NELSON AVILA GUTIERREZ", "votos": "25,421", "porcentaje": "0.75"},
        {"partido": "PARTIDO DEMOCRATA CRISTIANO DE HONDURAS", "candidato": "MARIO ENRIQUE RIVERA CALLEJAS", "votos": "5,516", "porcentaje": "0.16"},
    ],
    "estadisticas": {
        "totalizacion_actas": {"actas_totales": "19,167", "actas_divulgadas": "19,052"},
        "distribucion_votos": {"validos": "3,204,648", "nulos": "119,889", "blancos": "68,075"},
        "estado_actas_divulgadas": {"actas_correctas": "16,279", "actas_inconsistentes": "2,773"},
    },
}

TIMELINE = [
    ("2025-12-03T16:25:27Z", SNAPSHOT_DEC03_1625),
    ("2025-12-06T04:00:51Z", SNAPSHOT_DEC06_0400),
    ("2025-12-10T17:03:59Z", SNAPSHOT_DEC10_1703),
]


# ---------------------------------------------------------------------------
# Phase 1: Normalization survives all real snapshots
# ---------------------------------------------------------------------------

class TestNormalizationSurvivesAllSnapshots:
    """Every real CNE snapshot must normalize without returning None."""

    @pytest.mark.parametrize("timestamp,raw", TIMELINE)
    def test_normalize_does_not_return_none(self, timestamp, raw):
        snapshot = normalize_snapshot(
            raw,
            department_name="TODOS",
            timestamp_utc=timestamp,
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is not None, f"normalize_snapshot returned None for {timestamp}"

    @pytest.mark.parametrize("timestamp,raw", TIMELINE)
    def test_canonical_json_roundtrips(self, timestamp, raw):
        snapshot = normalize_snapshot(
            raw, department_name="TODOS", timestamp_utc=timestamp,
            scope="NATIONAL", department_code="00",
        )
        canonical = snapshot_to_canonical_json(snapshot)
        parsed = json.loads(canonical)
        assert isinstance(parsed, dict)
        assert parsed["meta"]["timestamp_utc"] == timestamp


# ---------------------------------------------------------------------------
# Phase 2: Storage → hashchain integrity across 3 snapshots
# ---------------------------------------------------------------------------

class TestStorageHashchainIntegrity:
    """Store 3 real snapshots sequentially and verify the hash chain."""

    def test_full_chain_storage_and_retrieval(self, tmp_path):
        db_path = tmp_path / "snapshots.db"
        store = LocalSnapshotStore(str(db_path))
        hashes = []
        previous_hash = None

        for timestamp, raw in TIMELINE:
            snapshot = normalize_snapshot(
                raw, department_name="TODOS", timestamp_utc=timestamp,
                scope="NATIONAL", department_code="00",
            )
            assert snapshot is not None, f"Failed to normalize {timestamp}"
            h = store.store_snapshot(snapshot, previous_hash=previous_hash)
            hashes.append(h)
            previous_hash = h

        # Verify chain links
        entries = store.get_index_entries("00")
        assert len(entries) == 3
        assert entries[0]["previous_hash"] is None
        assert entries[1]["previous_hash"] == hashes[0]
        assert entries[2]["previous_hash"] == hashes[1]

        store.close()

    def test_export_json_with_real_data(self, tmp_path):
        db_path = tmp_path / "snapshots.db"
        store = LocalSnapshotStore(str(db_path))

        for timestamp, raw in TIMELINE:
            snapshot = normalize_snapshot(
                raw, department_name="TODOS", timestamp_utc=timestamp,
                scope="NATIONAL", department_code="00",
            )
            store.store_snapshot(snapshot)

        export_path = tmp_path / "export.json"
        store.export_department_json("00", str(export_path))
        store.close()

        exported = json.loads(export_path.read_text(encoding="utf-8"))
        assert len(exported) == 3
        for entry in exported:
            assert entry["snapshot"] is not None, "Exported snapshot should not be None"
            assert "meta" in entry["snapshot"]
            assert "candidates" in entry["snapshot"]


# ---------------------------------------------------------------------------
# Phase 3: API endpoints serve real data without crashing
# ---------------------------------------------------------------------------

class TestApiServesRealData:
    """API functions must return structured data for real CNE snapshots."""

    @pytest.fixture()
    def db_connection(self, tmp_path):
        import sqlite3
        db_path = tmp_path / "snapshots.db"
        store = LocalSnapshotStore(str(db_path))
        previous_hash = None

        for timestamp, raw in TIMELINE:
            snapshot = normalize_snapshot(
                raw, department_name="TODOS", timestamp_utc=timestamp,
                scope="NATIONAL", department_code="00",
            )
            h = store.store_snapshot(snapshot, previous_hash=previous_hash)
            previous_hash = h

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()
        store.close()

    def test_fetch_latest_returns_valid_payload(self, db_connection):
        result = fetch_latest_snapshot(db_connection)
        assert result is not None
        assert result["snapshot"] is not None
        assert result["department_code"] == "00"
        assert len(result["snapshot"]["candidates"]) == 5

    def test_fetch_by_hash_returns_valid_payload(self, db_connection):
        latest = fetch_latest_snapshot(db_connection)
        result = fetch_snapshot_by_hash(db_connection, latest["snapshot_id"])
        assert result is not None
        assert result["snapshot"] is not None
        assert result["snapshot"]["meta"]["source"] == "CNE"

    def test_hashchain_verification_passes(self, db_connection):
        latest = fetch_latest_snapshot(db_connection)
        result = verify_hashchain(db_connection, latest["snapshot_id"])
        assert result["exists"] is True
        assert result["valid"] is True, "Hash chain verification failed for real CNE data"


# ---------------------------------------------------------------------------
# Phase 4: Edge cases — malformed variants of real data
# ---------------------------------------------------------------------------

class TestMalformedVariantsOfRealData:
    """System must not crash on corrupted versions of real CNE data."""

    def test_missing_estadisticas(self):
        """CNE could omit estadisticas in a partial response."""
        raw = {"resultados": SNAPSHOT_DEC03_1625["resultados"]}
        snapshot = normalize_snapshot(
            raw, department_name="TODOS", timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL", department_code="00",
        )
        assert snapshot is not None
        assert snapshot.totals.valid_votes == 0  # No stats available

    def test_missing_resultados(self):
        """CNE could send only estadisticas without resultados."""
        raw = {"estadisticas": SNAPSHOT_DEC03_1625["estadisticas"]}
        snapshot = normalize_snapshot(
            raw, department_name="TODOS", timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL", department_code="00",
        )
        assert snapshot is not None
        assert snapshot.totals.valid_votes == 2552777
        # Candidates should be zero-filled placeholders
        assert all(c.votes == 0 for c in snapshot.candidates)

    def test_empty_resultados_array(self):
        """CNE could send an empty resultados array."""
        raw = {
            "resultados": [],
            "estadisticas": SNAPSHOT_DEC03_1625["estadisticas"],
        }
        snapshot = normalize_snapshot(
            raw, department_name="TODOS", timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL", department_code="00",
        )
        assert snapshot is not None

    def test_votos_as_integer_instead_of_string(self):
        """Some CNE endpoints might send votes as integers."""
        raw = {
            "resultados": [
                {"partido": "TEST", "candidato": "TEST", "votos": 999999, "porcentaje": "50.00"},
            ],
            "estadisticas": {
                "distribucion_votos": {"validos": 999999, "nulos": 0, "blancos": 0},
                "totalizacion_actas": {"actas_totales": 100, "actas_divulgadas": 100},
                "estado_actas_divulgadas": {"actas_correctas": 100, "actas_inconsistentes": 0},
            },
        }
        snapshot = normalize_snapshot(
            raw, department_name="TODOS", timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL", department_code="00",
        )
        assert snapshot is not None
        assert snapshot.candidates[0].votes == 999999

    def test_raw_as_json_string(self):
        """Data might arrive as a JSON string, not a dict."""
        raw_str = json.dumps(SNAPSHOT_DEC10_1703)
        snapshot = normalize_snapshot(
            raw_str, department_name="TODOS", timestamp_utc="2025-12-10T17:03:59Z",
            scope="NATIONAL", department_code="00",
        )
        assert snapshot is not None
        assert len(snapshot.candidates) == 5

    def test_raw_as_bytes(self):
        """Data might arrive as bytes from an HTTP response."""
        raw_bytes = json.dumps(SNAPSHOT_DEC10_1703).encode("utf-8")
        snapshot = normalize_snapshot(
            raw_bytes, department_name="TODOS", timestamp_utc="2025-12-10T17:03:59Z",
            scope="NATIONAL", department_code="00",
        )
        assert snapshot is not None

    def test_completely_garbage_json_returns_none(self):
        """Total garbage must return None, not crash."""
        snapshot = normalize_snapshot(
            "NOT JSON AT ALL {{{",
            department_name="TODOS",
            timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is None

    def test_valid_json_but_not_object_returns_none(self):
        """A JSON array instead of object must return None."""
        snapshot = normalize_snapshot(
            [1, 2, 3],
            department_name="TODOS",
            timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is None

    def test_empty_object_returns_none(self):
        """An empty JSON object has no recognizable structure."""
        snapshot = normalize_snapshot(
            {},
            department_name="TODOS",
            timestamp_utc="2025-12-03T16:25:27Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is None


# ---------------------------------------------------------------------------
# Phase 5: All 18 departments + national scope
# ---------------------------------------------------------------------------

# Simulated per-department data (CNE sends same structure, different numbers)
_DEPARTMENT_SNAPSHOT_TEMPLATE = {
    "resultados": [
        {"partido": "PARTIDO NACIONAL DE HONDURAS", "candidato": "NASRY JUAN ASFURA ZABLAH", "votos": "72,157", "porcentaje": "38.28"},
        {"partido": "PARTIDO LIBERAL DE HONDURAS", "candidato": "SALVADOR ALEJANDRO CESAR NASRALLA SALUM", "votos": "69,802", "porcentaje": "37.03"},
        {"partido": "PARTIDO LIBERTAD Y REFUNDACION", "candidato": "RIXI RAMONA MONCADA GODOY", "votos": "34,358", "porcentaje": "18.23"},
    ],
    "estadisticas": {
        "totalizacion_actas": {"actas_totales": "1,065", "actas_divulgadas": "1,058"},
        "distribucion_votos": {"validos": "176,317", "nulos": "6,660", "blancos": "3,782"},
        "estado_actas_divulgadas": {"actas_correctas": "904", "actas_inconsistentes": "154"},
    },
}

ALL_DEPARTMENTS = [
    ("Atlántida", "01"),
    ("Choluteca", "02"),
    ("Colón", "03"),
    ("Comayagua", "04"),
    ("Copán", "05"),
    ("Cortés", "06"),
    ("El Paraíso", "07"),
    ("Francisco Morazán", "08"),
    ("Gracias a Dios", "09"),
    ("Intibucá", "10"),
    ("Islas de la Bahía", "11"),
    ("La Paz", "12"),
    ("Lempira", "13"),
    ("Ocotepeque", "14"),
    ("Olancho", "15"),
    ("Santa Bárbara", "16"),
    ("Valle", "17"),
    ("Yoro", "18"),
]


class TestAllDepartmentsAndNational:
    """Normalization + storage must work for every department and national scope."""

    @pytest.mark.parametrize("dept_name,dept_code", ALL_DEPARTMENTS)
    def test_normalize_per_department(self, dept_name, dept_code):
        """Each of the 18 departments normalizes correctly with scope=DEPARTMENT."""
        snapshot = normalize_snapshot(
            _DEPARTMENT_SNAPSHOT_TEMPLATE,
            department_name=dept_name,
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="DEPARTMENT",
            department_code=dept_code,
        )
        assert snapshot is not None
        assert snapshot.meta.scope == "DEPARTMENT"
        assert snapshot.meta.department_code == dept_code
        assert len(snapshot.candidates) == 3
        assert snapshot.totals.valid_votes == 176317

    def test_normalize_national(self):
        """National scope normalizes with department_code='00'."""
        snapshot = normalize_snapshot(
            SNAPSHOT_DEC10_1703,
            department_name="TODOS",
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="NATIONAL",
            department_code="00",
        )
        assert snapshot is not None
        assert snapshot.meta.scope == "NATIONAL"
        assert snapshot.meta.department_code == "00"

    def test_department_code_resolved_from_name(self):
        """When department_code is not passed, it resolves from department_name."""
        snapshot = normalize_snapshot(
            _DEPARTMENT_SNAPSHOT_TEMPLATE,
            department_name="Francisco Morazán",
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="DEPARTMENT",
        )
        assert snapshot is not None
        assert snapshot.meta.department_code == "08"

    def test_unknown_department_defaults_to_00(self):
        """Unknown department name defaults to code '00'."""
        snapshot = normalize_snapshot(
            _DEPARTMENT_SNAPSHOT_TEMPLATE,
            department_name="Desconocido",
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="DEPARTMENT",
        )
        assert snapshot is not None
        assert snapshot.meta.department_code == "00"

    def test_storage_isolates_department_chains(self, tmp_path):
        """Each department gets its own independent hash chain."""
        db_path = tmp_path / "multi_dept.db"
        store = LocalSnapshotStore(str(db_path))

        # Store one snapshot for Cortés (06) and one for Olancho (15)
        for dept_name, dept_code in [("Cortés", "06"), ("Olancho", "15")]:
            snapshot = normalize_snapshot(
                _DEPARTMENT_SNAPSHOT_TEMPLATE,
                department_name=dept_name,
                timestamp_utc="2025-12-10T17:03:59Z",
                scope="DEPARTMENT",
                department_code=dept_code,
            )
            store.store_snapshot(snapshot)

        # Each department should have exactly 1 entry
        cortes_entries = store.get_index_entries("06")
        olancho_entries = store.get_index_entries("15")
        assert len(cortes_entries) == 1
        assert len(olancho_entries) == 1
        assert cortes_entries[0]["department_code"] == "06"
        assert olancho_entries[0]["department_code"] == "15"

        # Their hashes should be different tables
        assert cortes_entries[0]["table_name"] != olancho_entries[0]["table_name"]

        store.close()

    def test_national_and_departments_coexist(self, tmp_path):
        """National and department snapshots coexist in the same DB."""
        db_path = tmp_path / "mixed.db"
        store = LocalSnapshotStore(str(db_path))

        # Store national
        national = normalize_snapshot(
            SNAPSHOT_DEC10_1703,
            department_name="TODOS",
            timestamp_utc="2025-12-10T17:03:59Z",
            scope="NATIONAL",
            department_code="00",
        )
        store.store_snapshot(national)

        # Store 3 departments
        for dept_name, dept_code in [("Atlántida", "01"), ("Cortés", "06"), ("Yoro", "18")]:
            snapshot = normalize_snapshot(
                _DEPARTMENT_SNAPSHOT_TEMPLATE,
                department_name=dept_name,
                timestamp_utc="2025-12-10T17:03:59Z",
                scope="DEPARTMENT",
                department_code=dept_code,
            )
            store.store_snapshot(snapshot)

        # All 4 entries should exist in the index
        all_entries = store.get_index_entries()
        assert len(all_entries) == 4

        # Each has its own chain
        national_entries = store.get_index_entries("00")
        assert len(national_entries) == 1
        assert national_entries[0]["department_code"] == "00"

        store.close()
