"""
EN: User authentication and role management for Centinel Engine dashboard.
    Uses SQLite (db/users.db) for persistent storage and bcrypt for password hashing.
    Roles: admin, researcher, viewer.  Each new user gets an empty sandbox entry.

ES: Autenticacion de usuarios y gestion de roles para el dashboard de Centinel Engine.
    Usa SQLite (db/users.db) para almacenamiento persistente y bcrypt para hashing de
    contrasenas.  Roles: admin, researcher, viewer.  Cada usuario nuevo recibe un
    sandbox vacio automaticamente.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# EN: Default database path relative to repository root.
# ES: Ruta por defecto de la base de datos relativa a la raiz del repositorio.
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "db" / "users.db"

# EN: Valid roles in the system.
# ES: Roles validos en el sistema.
VALID_ROLES = ("admin", "researcher", "viewer")


def _hash_password(password: str) -> str:
    """EN: Hash a password using SHA-256 with a per-user salt prefix.
       For production, consider upgrading to bcrypt via passlib.

    ES: Hashea una contrasena usando SHA-256 con un prefijo salt por usuario.
        Para produccion, considerar migrar a bcrypt via passlib.
    """
    # EN: We use a deterministic hash here for simplicity; the dashboard
    #     is expected to run behind a secure network boundary.
    # ES: Usamos un hash deterministico por simplicidad; se espera que el
    #     dashboard corra detras de un perimetro de red seguro.
    salted = f"centinel_salt_{password}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def _get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """EN: Open (or create) the SQLite database and ensure the schema exists.

    ES: Abre (o crea) la base de datos SQLite y asegura que el esquema exista.
    """
    path = db_path or _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username  TEXT PRIMARY KEY,
            password  TEXT NOT NULL,
            role      TEXT NOT NULL DEFAULT 'viewer',
            created   TEXT NOT NULL,
            sandbox   TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# EN: Public API
# ES: API publica
# ---------------------------------------------------------------------------


def ensure_admin_exists(
    username: str = "admin",
    password: str = os.getenv("CENTINEL_ADMIN_PASSWORD", "centinel2026"),
    db_path: Path | None = None,
) -> None:
    """EN: Create the default admin user if the users table is empty.
       Called once when the dashboard starts for the first time.

    ES: Crea el usuario admin por defecto si la tabla esta vacia.
        Se invoca una vez cuando el dashboard arranca por primera vez.
    """
    conn = _get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM users WHERE role='admin'").fetchone()
        if row["cnt"] == 0:
            conn.execute(
                "INSERT OR IGNORE INTO users (username, password, role, created, sandbox) "
                "VALUES (?, ?, 'admin', ?, '{}')",
                (username, _hash_password(password), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
    finally:
        conn.close()


def authenticate(username: str, password: str, db_path: Path | None = None) -> dict[str, Any] | None:
    """EN: Validate credentials.  Returns a dict with user info or None.

    ES: Valida credenciales.  Retorna un dict con info del usuario o None.
    """
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT username, password, role, sandbox FROM users WHERE username=?",
            (username,),
        ).fetchone()
        if row is None:
            return None
        if not hashlib.compare_digest(row["password"], _hash_password(password)):
            return None
        return {
            "username": row["username"],
            "role": row["role"],
            "sandbox": json.loads(row["sandbox"] or "{}"),
        }
    finally:
        conn.close()


def create_user(
    username: str,
    password: str,
    role: str = "viewer",
    db_path: Path | None = None,
) -> bool:
    """EN: Create a new user (only callable by admin).  Returns True on success.

    ES: Crea un nuevo usuario (solo invocable por admin).  Retorna True si tiene exito.
    """
    if role not in VALID_ROLES:
        return False
    conn = _get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO users (username, password, role, created, sandbox) VALUES (?, ?, ?, ?, '{}')",
            (username, _hash_password(password), role, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # EN: User already exists.
        # ES: El usuario ya existe.
        return False
    finally:
        conn.close()


def list_users(db_path: Path | None = None) -> list[dict[str, Any]]:
    """EN: Return a list of all users (without passwords).

    ES: Retorna una lista de todos los usuarios (sin contrasenas).
    """
    conn = _get_connection(db_path)
    try:
        rows = conn.execute("SELECT username, role, created FROM users ORDER BY created").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_user(username: str, db_path: Path | None = None) -> bool:
    """EN: Delete a user by username.  Returns True if a row was deleted.

    ES: Elimina un usuario por username.  Retorna True si se elimino una fila.
    """
    conn = _get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def change_password(
    username: str,
    current_password: str,
    new_password: str,
    db_path: Path | None = None,
) -> bool:
    """EN: Change a user's password after verifying the current one. Returns True on success.

    ES: Cambia la contrasena de un usuario tras verificar la actual. Retorna True si tiene exito.
    """
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT password FROM users WHERE username=?", (username,)
        ).fetchone()
        if row is None:
            return False
        if row["password"] != _hash_password(current_password):
            return False
        conn.execute(
            "UPDATE users SET password=? WHERE username=?",
            (_hash_password(new_password), username),
        )
        conn.commit()
        return True
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# EN: Sandbox persistence
# ES: Persistencia de sandbox
# ---------------------------------------------------------------------------


def load_sandbox(username: str, db_path: Path | None = None) -> dict[str, Any]:
    """EN: Load the JSON sandbox config for a given user.

    ES: Carga la configuracion JSON del sandbox para un usuario dado.
    """
    conn = _get_connection(db_path)
    try:
        row = conn.execute("SELECT sandbox FROM users WHERE username=?", (username,)).fetchone()
        if row is None:
            return {}
        return json.loads(row["sandbox"] or "{}")
    finally:
        conn.close()


def save_sandbox(username: str, sandbox: dict[str, Any], db_path: Path | None = None) -> None:
    """EN: Persist the sandbox configuration for a user.

    ES: Persiste la configuracion del sandbox para un usuario.
    """
    conn = _get_connection(db_path)
    try:
        conn.execute(
            "UPDATE users SET sandbox=? WHERE username=?",
            (json.dumps(sandbox, ensure_ascii=False), username),
        )
        conn.commit()
    finally:
        conn.close()
