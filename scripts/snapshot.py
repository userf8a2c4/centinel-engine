#!/usr/bin/env python
"""Run collection + hash snapshot in one command.

Ejecuta recolección + snapshot de hash en un solo comando.
"""

from scripts.collector import run_collection
from scripts.hash import run_hash_snapshot


def main() -> None:
    """Execute the audit snapshot pipeline.

    Ejecuta el pipeline de snapshot de auditoría.
    """
    run_collection()
    raise SystemExit(run_hash_snapshot())


if __name__ == "__main__":
    main()
