"""Utilidades para trabajar con archivos de snapshots y timestamps."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional

FILENAME_TIMESTAMP_RE = re.compile(
    r"(?P<date>20\d{2}-\d{2}-\d{2})[ _](?P<hour>\d{2})[_:](?P<minute>\d{2})[_:](?P<second>\d{2})"
)


def list_snapshot_files(data_folder: Path, pattern: str) -> list[Path]:
    """Lista archivos de snapshots según un patrón glob."""
    return sorted(data_folder.glob(pattern))


def parse_filename_timestamp(filename: str) -> Optional[datetime]:
    """Extrae el timestamp desde el nombre de archivo (UTC)."""
    match = FILENAME_TIMESTAMP_RE.search(filename)
    if not match:
        return None
    try:
        date_part = match.group("date")
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        second = int(match.group("second"))
        parsed = datetime.fromisoformat(date_part)
        return parsed.replace(
            hour=hour,
            minute=minute,
            second=second,
            microsecond=0,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


def sorted_by_filename_timestamp(files: Iterable[Path]) -> list[Path]:
    """Ordena archivos por timestamp parseado en nombre."""
    def sort_key(path: Path) -> tuple[int, str]:
        ts = parse_filename_timestamp(path.name)
        if not ts:
            return (1, path.name)
        return (0, ts.isoformat())

    return sorted(files, key=sort_key)


def iter_nested_fields(payload: object) -> Iterator[tuple[str, object]]:
    """Itera sobre todas las claves/valores en estructuras anidadas."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key, value
            yield from iter_nested_fields(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from iter_nested_fields(item)


def get_nested_value(payload: dict, path: str) -> object | None:
    """Obtiene un valor por ruta con puntos (ej. resultados.total)."""
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current
