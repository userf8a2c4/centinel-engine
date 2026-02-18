"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_centinel_storage.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_save_snapshot_creates_files

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_centinel_storage.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_save_snapshot_creates_files

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from centinel.storage import save_snapshot


def test_save_snapshot_creates_files(tmp_path):
    """Español: Función test_save_snapshot_creates_files del módulo tests/test_centinel_storage.py.

    English: Function test_save_snapshot_creates_files defined in tests/test_centinel_storage.py.
    """
    content = b"payload"
    metadata = {"source": "test"}
    previous_hash = "abc"

    new_hash = save_snapshot(content, metadata, previous_hash, base_path=tmp_path)

    snapshots = list((tmp_path / "snapshots").rglob("snapshot.raw"))
    assert snapshots, "snapshot.raw not created"

    snapshot_dir = snapshots[0].parent
    assert (snapshot_dir / "snapshot.metadata.json").exists()
    assert (snapshot_dir / "hash.txt").exists()

    chain_path = tmp_path / "hashes" / "chain.json"
    assert chain_path.exists()
    assert new_hash in chain_path.read_text(encoding="utf-8")
