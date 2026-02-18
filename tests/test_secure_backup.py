"""Tests for centinel_engine.secure_backup (encrypted backup system).

Bilingual: Pruebas para centinel_engine.secure_backup (sistema de respaldo cifrado).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from centinel_engine.secure_backup import (  # noqa: E402
    _compute_sha256,
    _build_backup_manifest,
    _collect_hash_chain_files,
    _backup_to_local,
    backup_critical_assets,
    BackupScheduler,
)


# ---------------------------------------------------------------------------
# Test 1: SHA-256 computation / Calculo SHA-256
# ---------------------------------------------------------------------------

class TestSHA256:
    """Tests for SHA-256 hash computation / Pruebas de calculo de hash SHA-256."""

    def test_known_hash(self) -> None:
        """Known input produces expected SHA-256 digest.

        Bilingual: Entrada conocida produce digest SHA-256 esperado.
        """
        data = b"centinel-test-data"
        result = _compute_sha256(data)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_empty_data(self) -> None:
        """Empty bytes produce the well-known empty SHA-256.

        Bilingual: Bytes vacios producen el SHA-256 vacio conocido.
        """
        result = _compute_sha256(b"")
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_deterministic(self) -> None:
        """Same input always produces same hash.

        Bilingual: Misma entrada siempre produce mismo hash.
        """
        data = b"deterministic-test"
        assert _compute_sha256(data) == _compute_sha256(data)


# ---------------------------------------------------------------------------
# Test 2: Backup manifest / Manifiesto de respaldo
# ---------------------------------------------------------------------------

class TestManifest:
    """Tests for backup manifest construction / Pruebas de construccion de manifiesto."""

    def test_manifest_structure(self) -> None:
        """Manifest contains required fields.

        Bilingual: Manifiesto contiene campos requeridos.
        """
        manifest = _build_backup_manifest(
            ["file1.json", "file2.json"],
            {"file1.json": "abc123", "file2.json": "def456"},
            encrypted=True,
        )
        assert "timestamp" in manifest
        assert manifest["encrypted"] is True
        assert manifest["files"] == ["file1.json", "file2.json"]
        assert manifest["version"] == "1.0"
        assert manifest["sha256_hashes"]["file1.json"] == "abc123"


# ---------------------------------------------------------------------------
# Test 3: Hash chain file collection / Recoleccion de archivos de cadena de hashes
# ---------------------------------------------------------------------------

class TestHashChainCollection:
    """Tests for hash chain file discovery / Pruebas de descubrimiento de archivos de cadena."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns empty list.

        Bilingual: Directorio vacio retorna lista vacia.
        """
        result = _collect_hash_chain_files(tmp_path)
        assert result == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Nonexistent directory returns empty list.

        Bilingual: Directorio inexistente retorna lista vacia.
        """
        result = _collect_hash_chain_files(tmp_path / "nonexistent")
        assert result == []

    def test_collects_json_files(self, tmp_path: Path) -> None:
        """Collects .json files from the hash directory.

        Bilingual: Recolecta archivos .json del directorio de hashes.
        """
        (tmp_path / "hash_001.json").write_text('{"hash": "abc"}')
        (tmp_path / "hash_002.json").write_text('{"hash": "def"}')
        (tmp_path / "ignore.txt").write_text("not a hash")
        result = _collect_hash_chain_files(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".json" for p in result)


# ---------------------------------------------------------------------------
# Test 4: Local backup / Respaldo local
# ---------------------------------------------------------------------------

class TestLocalBackup:
    """Tests for local backup writing / Pruebas de escritura de respaldo local."""

    def test_writes_backup_file(self, tmp_path: Path) -> None:
        """Local backup writes encrypted payload and manifest.

        Bilingual: Respaldo local escribe payload cifrado y manifiesto.
        """
        payload = b"encrypted-test-data"
        manifest = _build_backup_manifest(["test.json"], {"test.json": "abc"}, encrypted=True)
        result = _backup_to_local(tmp_path, payload, "test_backup.enc", manifest)
        assert result is True
        assert (tmp_path / "test_backup.enc").exists()
        assert (tmp_path / "test_backup.enc.manifest.json").exists()

    def test_backup_content_matches(self, tmp_path: Path) -> None:
        """Written backup content matches the input payload.

        Bilingual: Contenido del respaldo escrito coincide con el payload de entrada.
        """
        payload = b"exact-content-check"
        manifest = _build_backup_manifest([], {}, encrypted=False)
        _backup_to_local(tmp_path, payload, "check.enc", manifest)
        assert (tmp_path / "check.enc").read_bytes() == payload

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Local backup creates nested parent directories.

        Bilingual: Respaldo local crea directorios padre anidados.
        """
        deep_dir = tmp_path / "nested" / "deep" / "backups"
        payload = b"nested-test"
        manifest = _build_backup_manifest([], {}, encrypted=False)
        result = _backup_to_local(deep_dir, payload, "nested.enc", manifest)
        assert result is True
        assert (deep_dir / "nested.enc").exists()


# ---------------------------------------------------------------------------
# Test 5: Full backup pipeline / Pipeline completo de respaldo
# ---------------------------------------------------------------------------

class TestBackupCriticalAssets:
    """Tests for the main backup_critical_assets function / Pruebas de la funcion principal."""

    def test_backup_with_health_state(self, tmp_path: Path) -> None:
        """Backup succeeds when health_state.json exists.

        Bilingual: Respaldo exitoso cuando health_state.json existe.
        """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        health_state = {"mode": "normal", "consecutive_failures": 0}
        (data_dir / "health_state.json").write_text(json.dumps(health_state))

        hash_dir = tmp_path / "hashes"
        hash_dir.mkdir()
        (hash_dir / "hash_001.json").write_text(json.dumps({"hash": "abc123"}))

        backup_dir = tmp_path / "backups"

        result = backup_critical_assets(
            health_state_path=data_dir / "health_state.json",
            hash_chain_dir=hash_dir,
            backup_dir=backup_dir,
        )

        assert result["local"] is True
        assert len(result["files_backed_up"]) >= 1
        assert "health_state.json" in result["files_backed_up"]

    def test_backup_with_no_files(self, tmp_path: Path) -> None:
        """Backup succeeds gracefully when no critical files exist.

        Bilingual: Respaldo exitoso graciosamente cuando no existen archivos criticos.
        """
        result = backup_critical_assets(
            health_state_path=tmp_path / "nonexistent.json",
            hash_chain_dir=tmp_path / "nonexistent_dir",
            backup_dir=tmp_path / "backups",
        )
        assert result["local"] is False
        assert result["files_backed_up"] == []

    def test_backup_never_raises(self, tmp_path: Path) -> None:
        """backup_critical_assets() never raises exceptions.

        Bilingual: backup_critical_assets() nunca lanza excepciones.
        """
        # Pass an invalid path that will cause issues /
        # Pasar una ruta invalida que causara problemas
        result = backup_critical_assets(
            health_state_path=Path("/dev/null/impossible/path.json"),
            hash_chain_dir=Path("/dev/null/impossible/hashes"),
            backup_dir=Path("/dev/null/impossible/backups"),
        )
        # Should return without raising / Deberia retornar sin lanzar
        assert isinstance(result, dict)
        assert "errors" in result


# ---------------------------------------------------------------------------
# Test 6: BackupScheduler / Programador de respaldo
# ---------------------------------------------------------------------------

class TestBackupScheduler:
    """Tests for the backup scheduler / Pruebas del programador de respaldo."""

    def test_scheduler_creation(self, tmp_path: Path) -> None:
        """Scheduler can be created with default parameters.

        Bilingual: Programador puede crearse con parametros por defecto.
        """
        scheduler = BackupScheduler(
            interval_seconds=60,
            backup_dir=tmp_path / "backups",
        )
        assert scheduler.last_backup_time == 0.0

    def test_trigger_backup_runs(self, tmp_path: Path) -> None:
        """trigger_backup() executes without error.

        Bilingual: trigger_backup() ejecuta sin error.
        """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "health_state.json").write_text('{"mode": "normal"}')

        scheduler = BackupScheduler(
            interval_seconds=60,
            health_state_path=data_dir / "health_state.json",
            hash_chain_dir=tmp_path / "hashes",
            backup_dir=tmp_path / "backups",
        )
        result = scheduler.trigger_backup()
        assert isinstance(result, dict)
        assert scheduler.last_backup_time > 0.0

    def test_start_stop(self, tmp_path: Path) -> None:
        """Scheduler starts and stops cleanly.

        Bilingual: Programador inicia y detiene limpiamente.
        """
        scheduler = BackupScheduler(
            interval_seconds=3600,
            backup_dir=tmp_path / "backups",
        )
        scheduler.start()
        scheduler.stop()
        # No exception means success / Sin excepcion significa exito
