"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_hashchain.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_hash_is_stable
  - test_hash_chain_changes

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_hashchain.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_hash_is_stable
  - test_hash_chain_changes

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from centinel.core.hashchain import compute_hash


def test_hash_is_stable():
    """Español: Función test_hash_is_stable del módulo tests/test_hashchain.py.

    English: Function test_hash_is_stable defined in tests/test_hashchain.py.
    """
    data = '{"a":1,"b":2}'
    h1 = compute_hash(data)
    h2 = compute_hash(data)

    assert h1 == h2


def test_hash_chain_changes():
    """Español: Función test_hash_chain_changes del módulo tests/test_hashchain.py.

    English: Function test_hash_chain_changes defined in tests/test_hashchain.py.
    """
    data = '{"a":1}'
    h1 = compute_hash(data)
    h2 = compute_hash(data, previous_hash=h1)

    assert h1 != h2
