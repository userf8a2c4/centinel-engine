"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `tests/test_arbitrum_privacy.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - test_obfuscate_identifier_short_values_passthrough
  - test_obfuscate_identifier_long_values_redacted

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `tests/test_arbitrum_privacy.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - test_obfuscate_identifier_short_values_passthrough
  - test_obfuscate_identifier_long_values_redacted

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

from anchor.arbitrum_anchor import _obfuscate_identifier


def test_obfuscate_identifier_short_values_passthrough() -> None:
    assert _obfuscate_identifier("abc123") == "abc123"


def test_obfuscate_identifier_long_values_redacted() -> None:
    value = "0x1234567890abcdef"
    masked = _obfuscate_identifier(value)
    assert masked.startswith("0x1234")
    assert masked.endswith("cdef")
    assert "…" in masked
