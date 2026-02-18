"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `src/centinel/paths.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - resolve_source_id
  - snapshot_dir_for_source
  - hash_dir_for_source
  - snapshot_filename
  - hash_filename
  - ensure_source_dirs
  - iter_all_source_dirs
  - iter_all_snapshots
  - iter_all_hashes

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `src/centinel/paths.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - resolve_source_id
  - snapshot_dir_for_source
  - hash_dir_for_source
  - snapshot_filename
  - hash_filename
  - ensure_source_dirs
  - iter_all_source_dirs
  - iter_all_snapshots
  - iter_all_hashes

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Paths Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations



from __future__ import annotations

from pathlib import Path
from typing import Any


# Raíces por defecto (relativas al root del proyecto).
# Default roots (relative to project root).
DEFAULT_DATA_ROOT = Path("data")
DEFAULT_HASH_ROOT = Path("hashes")

# Subdirectorio dentro de data/ donde se guardan los snapshots organizados.
# Subdirectory inside data/ where organized snapshots are stored.
SNAPSHOTS_SUBDIR = "snapshots"


def resolve_source_id(source: dict[str, Any]) -> str:
    """Resuelve el identificador canónico de una fuente.

    Resolve the canonical identifier for a source.

    Prioridad: source_id > department_code > "unknown".
    Priority: source_id > department_code > "unknown".
    """
    return source.get("source_id") or source.get("department_code") or "unknown"


def snapshot_dir_for_source(
    source_id: str,
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> Path:
    """Directorio de snapshots para una fuente específica.

    Snapshot directory for a specific source.

    Ejemplo / Example:
        data/snapshots/NACIONAL/
        data/snapshots/01_atlantida/
    """
    return data_root / SNAPSHOTS_SUBDIR / source_id


def hash_dir_for_source(
    source_id: str,
    *,
    hash_root: Path = DEFAULT_HASH_ROOT,
) -> Path:
    """Directorio de hashes para una fuente específica.

    Hash directory for a specific source.

    Ejemplo / Example:
        hashes/NACIONAL/
        hashes/01_atlantida/
    """
    return hash_root / source_id


def snapshot_filename(timestamp: str) -> str:
    """Nombre de archivo para un snapshot (sin source_id, ya está en la ruta).

    Snapshot filename (without source_id, it's already in the path).

    Ejemplo / Example:
        snapshot_2026-01-03_09-43-13.json
    """
    return f"snapshot_{timestamp}.json"


def hash_filename(timestamp: str) -> str:
    """Nombre de archivo para un hash record.

    Hash record filename.

    Ejemplo / Example:
        snapshot_2026-01-03_09-43-13.sha256
    """
    return f"snapshot_{timestamp}.sha256"


def ensure_source_dirs(
    source_id: str,
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    hash_root: Path = DEFAULT_HASH_ROOT,
) -> tuple[Path, Path]:
    """Crea y retorna directorios de snapshot y hash para una fuente.

    Create and return snapshot and hash directories for a source.
    """
    snap_dir = snapshot_dir_for_source(source_id, data_root=data_root)
    h_dir = hash_dir_for_source(source_id, hash_root=hash_root)
    snap_dir.mkdir(parents=True, exist_ok=True)
    h_dir.mkdir(parents=True, exist_ok=True)
    return snap_dir, h_dir


def iter_all_source_dirs(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> list[Path]:
    """Lista todos los subdirectorios de fuentes bajo data/snapshots/.

    List all source subdirectories under data/snapshots/.
    """
    snapshots_base = data_root / SNAPSHOTS_SUBDIR
    if not snapshots_base.exists():
        return []
    return sorted(
        [d for d in snapshots_base.iterdir() if d.is_dir()],
        key=lambda p: p.name,
    )


def iter_all_snapshots(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    pattern: str = "snapshot_*.json",
) -> list[Path]:
    """Lista todos los snapshots de todas las fuentes, ordenados por mtime.

    List all snapshots from all sources, sorted by mtime.
    """
    results: list[Path] = []
    for source_dir in iter_all_source_dirs(data_root=data_root):
        results.extend(source_dir.glob(pattern))
    return sorted(results, key=lambda p: p.stat().st_mtime)


def iter_all_hashes(
    *,
    hash_root: Path = DEFAULT_HASH_ROOT,
    pattern: str = "snapshot_*.sha256",
) -> list[Path]:
    """Lista todos los hashes de todas las fuentes, ordenados por mtime.

    List all hashes from all sources, sorted by mtime.
    """
    results: list[Path] = []
    if not hash_root.exists():
        return results
    for source_dir in sorted(hash_root.iterdir()):
        if source_dir.is_dir():
            results.extend(source_dir.glob(pattern))
    return sorted(results, key=lambda p: p.stat().st_mtime)
