"""ES: Utilidades de verificacion criptografica para el dashboard C.E.N.T.I.N.E.L.

EN: Cryptographic verification helpers for the C.E.N.T.I.N.E.L. dashboard.
"""

from __future__ import annotations

import io
import random
import re
from typing import Literal

try:
    import qrcode
except ImportError:  # pragma: no cover - optional dependency for QR generation
    qrcode = None

VerificationStatus = Literal["verified", "pending", "failed"]


def is_valid_root_hash(root_hash: str) -> bool:
    """ES: Valida formato de hash raiz SHA-256 con o sin prefijo `0x`.

    EN: Validate SHA-256 root hash format with or without `0x` prefix.
    """
    # ES: Permitimos hashes hexadecimales de 64 caracteres con prefijo opcional. /
    # EN: We accept 64-char hexadecimal hashes with optional prefix.
    return bool(re.fullmatch(r"(?:0x)?[0-9a-fA-F]{64}", (root_hash or "").strip()))


def verify_hash_against_arbitrum(root_hash: str) -> tuple[VerificationStatus, str]:
    """ES: Simula verificacion institucional contra Arbitrum L2.

    EN: Simulate institutional verification against Arbitrum L2.
    """
    normalized_hash = (root_hash or "").strip().lower()
    if not is_valid_root_hash(normalized_hash):
        return "failed", "Hash raiz invalido: se esperaba SHA-256 hexadecimal de 64 caracteres."

    # ES: Simulacion determinista para demo offline, estable por hash. /
    # EN: Deterministic simulation for offline demos, stable per hash.
    seeded_rng = random.Random(normalized_hash)
    score = seeded_rng.random()
    if score > 0.72:
        return "verified", "Anclaje confirmado en Arbitrum L2 con trazabilidad completa."
    if score > 0.24:
        return "pending", "Consulta enviada a Arbitrum L2; confirmacion en curso."
    return "failed", "No se encontro coincidencia en Arbitrum L2 para este snapshot."


def build_verification_badge(status: VerificationStatus) -> str:
    """ES: Genera badge HTML institucional para estado de verificacion.

    EN: Build an institutional HTML badge for verification status.
    """
    palette = {
        "verified": ("#0E7A3E", "Verificado / Verified"),
        "pending": ("#B58500", "Pendiente / Pending"),
        "failed": ("#9E1C1C", "Fallido / Failed"),
    }
    color, label = palette[status]
    return (
        f"<span style='display:inline-block;padding:0.4rem 0.75rem;border-radius:999px;"
        f"font-weight:700;font-size:0.9rem;background:{color};color:white;'>{label}</span>"
    )


def generate_hash_qr_bytes(root_hash: str) -> bytes | None:
    """ES: Genera PNG QR para el hash raiz ingresado.

    EN: Generate QR PNG bytes for the provided root hash.
    """
    if qrcode is None:
        return None
    qr_buffer = io.BytesIO()
    qrcode.make((root_hash or "").strip()).save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    return qr_buffer.getvalue()

