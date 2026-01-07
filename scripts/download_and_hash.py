from datetime import datetime
from pathlib import Path

from sentinel.core.hashchain import compute_hash
from sentinel.core.normalyze import normalize_snapshot, snapshot_to_canonical_json

# Directorios
canonical_dir = Path("data")
hash_dir = Path("hashes")

canonical_dir.mkdir(exist_ok=True)
hash_dir.mkdir(exist_ok=True)


def get_previous_hash(department_code: str) -> str | None:
    """
    Busca el archivo de hash más reciente para un departamento.
    """

    hash_files = sorted(
        hash_dir.glob(f"{department_code}_*.sha256"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if hash_files:
        return hash_files[0].read_text(encoding="utf-8").strip()
    return None


def orchestrate_snapshot(
    raw: dict,
    department_name: str,
    timestamp_utc: str,
    year: int = 2025,
) -> dict:
    """
    Normaliza, serializa y encadena el hash del snapshot.
    """

    snapshot = normalize_snapshot(raw, department_name, timestamp_utc, year=year)
    canonical_json = snapshot_to_canonical_json(snapshot)
    department_code = snapshot.meta.department_code
    previous_hash = get_previous_hash(department_code)
    hash_value = compute_hash(canonical_json, previous_hash)

    timestamp_label = timestamp_utc.replace(":", "-").replace("Z", "")
    json_path = canonical_dir / f"{department_code}_{timestamp_label}.canonical.json"
    hash_path = hash_dir / f"{department_code}_{timestamp_label}.sha256"

    json_path.write_text(canonical_json, encoding="utf-8")
    hash_path.write_text(hash_value, encoding="utf-8")

    return {
        "department_code": department_code,
        "canonical_path": json_path,
        "hash_path": hash_path,
        "previous_hash": previous_hash,
        "hash": hash_value,
    }

# Simulación (luego será el CNE – ajusta para requests.get(url))
sample_data = {
    "registered_voters": 1000,
    "total_votes": 800,
    "valid_votes": 760,
    "null_votes": 30,
    "blank_votes": 10,
    "candidates": {
        "1": 320,
        "2": 240,
        "3": 200,
    },
}

timestamp_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
result = orchestrate_snapshot(sample_data, "Francisco Morazán", timestamp_utc)

print("Snapshot y hash chained creados:", timestamp_utc)
print("Departamento:", result["department_code"])
print("Hash previo usado:", result["previous_hash"] or "Ninguno (primer run)")
print("Nuevo hash:", result["hash"])
