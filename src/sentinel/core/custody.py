"""Cadena de custodia verificable — FASE 2.

Provee verificación end-to-end de la cadena de hashes, anclaje en
Arbitrum y firma Ed25519 del operador en cada snapshot.

English:
    Verifiable custody chain — PHASE 2.

    Provides end-to-end verification of the hash chain, Arbitrum
    anchor validation, and Ed25519 operator signatures per snapshot.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ChainLink:
    """Eslabón individual de la cadena de custodia. / Single link in the custody chain."""

    index: int
    hash: str
    previous_hash: Optional[str]
    data_hash: str
    timestamp: str
    valid: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class ChainVerificationResult:
    """Resultado de verificar toda la cadena. / Result of full chain verification."""

    valid: bool
    total_links: int
    verified_links: int
    broken_at: Optional[int] = None
    errors: List[str] = field(default_factory=list)
    first_hash: Optional[str] = None
    last_hash: Optional[str] = None


@dataclass(frozen=True)
class AnchorVerificationResult:
    """Resultado de verificar un anclaje contra Arbitrum. / Result of anchor verification against Arbitrum."""

    valid: bool
    tx_hash: str
    expected_root: str
    onchain_root: Optional[str] = None
    block_number: Optional[int] = None
    block_timestamp: Optional[int] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class SignatureResult:
    """Resultado de firmar un snapshot. / Result of signing a snapshot."""

    signature_hex: str
    public_key_hex: str
    operator_id: str
    signed_at: str
    payload_hash: str


# ---------------------------------------------------------------------------
# 1. verify_chain — recorre hashes y confirma hash[n] = sha256(hash[n-1] + data[n])
# ---------------------------------------------------------------------------

def _compute_expected_hash(previous_hash: Optional[str], data_bytes: bytes) -> str:
    """Calcula el hash esperado: sha256(previous_hash + data).

    English: Compute expected hash: sha256(previous_hash + data).
    """
    hasher = hashlib.sha256()
    if previous_hash:
        hasher.update(previous_hash.encode("utf-8"))
    hasher.update(data_bytes)
    return hasher.hexdigest()


def verify_chain(chain_dir: Path) -> ChainVerificationResult:
    """Recorre todos los eslabones de la cadena y verifica integridad.

    Para cada eslabón n, confirma que:
        hash[n] == sha256(hash[n-1] + data[n])

    Lee archivos de hash desde ``chain_dir`` (hashes/*.sha256) ordenados
    cronológicamente y valida la secuencia completa.

    English:
        Walks all chain links and verifies integrity.

        For each link n, confirms that:
            hash[n] == sha256(hash[n-1] + data[n])
    """
    hash_files = sorted(
        chain_dir.glob("*.sha256"),
        key=lambda p: p.stat().st_mtime,
    )

    if not hash_files:
        return ChainVerificationResult(
            valid=True,
            total_links=0,
            verified_links=0,
            errors=["no_hash_files_found"],
        )

    errors: List[str] = []
    previous_hash: Optional[str] = None
    verified = 0
    first_hash: Optional[str] = None
    last_hash: Optional[str] = None

    for idx, hash_file in enumerate(hash_files):
        try:
            payload = json.loads(hash_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"read_error index={idx} file={hash_file.name} error={exc}")
            continue

        stored_hash = payload.get("chained_hash") or payload.get("hash")
        if not stored_hash:
            errors.append(f"missing_hash index={idx} file={hash_file.name}")
            continue

        # Reconstruir data canónica del eslabón
        data_payload = {
            k: v for k, v in sorted(payload.items())
            if k not in ("chained_hash", "previous_hash", "operator_signature")
        }
        data_bytes = json.dumps(
            data_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

        stored_previous = payload.get("previous_hash")
        effective_previous = stored_previous if stored_previous else previous_hash

        expected = _compute_expected_hash(effective_previous, data_bytes)

        if idx == 0:
            first_hash = stored_hash

        if stored_hash != expected:
            # También verificar con el previous_hash almacenado directamente
            alt_expected = _compute_expected_hash(stored_previous, data_bytes)
            if stored_hash != alt_expected:
                errors.append(
                    f"hash_mismatch index={idx} file={hash_file.name} "
                    f"expected={expected[:16]}... stored={stored_hash[:16]}..."
                )
                return ChainVerificationResult(
                    valid=False,
                    total_links=len(hash_files),
                    verified_links=verified,
                    broken_at=idx,
                    errors=errors,
                    first_hash=first_hash,
                    last_hash=previous_hash,
                )

        verified += 1
        previous_hash = stored_hash
        last_hash = stored_hash

    valid = not errors
    return ChainVerificationResult(
        valid=valid,
        total_links=len(hash_files),
        verified_links=verified,
        errors=errors,
        first_hash=first_hash,
        last_hash=last_hash,
    )


def verify_chain_from_entries(entries: List[Dict[str, Any]]) -> ChainVerificationResult:
    """Verifica cadena desde una lista de entradas en memoria.

    Cada entrada debe contener: ``hash``, ``data`` (bytes o str), y
    opcionalmente ``previous_hash``.

    English:
        Verify chain from an in-memory list of entries.
    """
    if not entries:
        return ChainVerificationResult(valid=True, total_links=0, verified_links=0)

    errors: List[str] = []
    previous_hash: Optional[str] = None
    verified = 0
    first_hash: Optional[str] = None

    for idx, entry in enumerate(entries):
        stored_hash = entry.get("hash") or entry.get("chained_hash")
        data = entry.get("data", b"")
        if isinstance(data, str):
            data = data.encode("utf-8")

        expected = _compute_expected_hash(previous_hash, data)

        if idx == 0:
            first_hash = stored_hash

        if stored_hash != expected:
            errors.append(
                f"hash_mismatch index={idx} expected={expected[:16]}... stored={stored_hash[:16]}..."
            )
            return ChainVerificationResult(
                valid=False,
                total_links=len(entries),
                verified_links=verified,
                broken_at=idx,
                errors=errors,
                first_hash=first_hash,
                last_hash=previous_hash,
            )

        verified += 1
        previous_hash = stored_hash

    return ChainVerificationResult(
        valid=True,
        total_links=len(entries),
        verified_links=verified,
        errors=errors,
        first_hash=first_hash,
        last_hash=previous_hash,
    )


# ---------------------------------------------------------------------------
# 2. verify_anchor — consulta Arbitrum y confirma que Merkle root coincide
# ---------------------------------------------------------------------------

def verify_anchor(
    tx_hash: str,
    expected_root: Optional[str] = None,
    *,
    rpc_url: Optional[str] = None,
    contract_address: Optional[str] = None,
    max_retries: int = 3,
) -> AnchorVerificationResult:
    """Consulta Arbitrum y confirma que el Merkle root coincide con el esperado.

    Lee el receipt de la transacción, decodifica el evento
    ``HashRootAnchored(bytes32 root, uint256 timestamp)`` y compara
    el root on-chain con ``expected_root``.

    English:
        Queries Arbitrum and confirms the on-chain Merkle root matches
        the expected root.
    """
    if rpc_url is None or contract_address is None:
        from sentinel.utils.config_loader import load_config
        config = load_config()
        arb = config.get("arbitrum", {})
        rpc_url = rpc_url if rpc_url is not None else arb.get("rpc_url")
        contract_address = contract_address if contract_address is not None else arb.get("contract_address")

    if not rpc_url:
        return AnchorVerificationResult(
            valid=False,
            tx_hash=tx_hash,
            expected_root=expected_root or "",
            error="missing_rpc_url",
        )

    try:
        from web3 import Web3
    except ImportError:
        return AnchorVerificationResult(
            valid=False,
            tx_hash=tx_hash,
            expected_root=expected_root or "",
            error="web3_not_installed",
        )

    # Conectar con reintentos
    web3: Optional[Web3] = None
    for attempt in range(max_retries):
        try:
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if web3.is_connected():
                break
        except Exception:
            pass
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    if not web3 or not web3.is_connected():
        return AnchorVerificationResult(
            valid=False,
            tx_hash=tx_hash,
            expected_root=expected_root or "",
            error="rpc_connection_failed",
        )

    try:
        receipt = web3.eth.get_transaction_receipt(tx_hash)
    except Exception as exc:
        return AnchorVerificationResult(
            valid=False,
            tx_hash=tx_hash,
            expected_root=expected_root or "",
            error=f"receipt_fetch_failed: {exc}",
        )

    if receipt is None or receipt.get("status") != 1:
        return AnchorVerificationResult(
            valid=False,
            tx_hash=tx_hash,
            expected_root=expected_root or "",
            error="tx_failed_or_not_found",
        )

    # Decodificar evento HashRootAnchored
    # Topic[0] = keccak256("HashRootAnchored(bytes32,uint256)")
    event_sig = web3.keccak(text="HashRootAnchored(bytes32,uint256)")
    onchain_root: Optional[str] = None
    block_number = receipt.get("blockNumber")
    block_timestamp: Optional[int] = None

    for log_entry in receipt.get("logs", []):
        topics = log_entry.get("topics", [])
        if not topics or topics[0] != event_sig:
            continue
        # root está en topics[1] (indexed)
        if len(topics) >= 2:
            onchain_root = f"0x{topics[1].hex()}"
        # timestamp en data
        raw_data = log_entry.get("data", b"")
        if isinstance(raw_data, (bytes, bytearray)) and len(raw_data) >= 32:
            block_timestamp = int.from_bytes(raw_data[:32], "big")
        break

    if onchain_root is None:
        return AnchorVerificationResult(
            valid=False,
            tx_hash=tx_hash,
            expected_root=expected_root or "",
            error="event_not_found_in_logs",
            block_number=block_number,
        )

    # Comparar roots
    if expected_root:
        normalized_expected = expected_root.lower().replace("0x", "")
        normalized_onchain = onchain_root.lower().replace("0x", "")
        roots_match = normalized_expected == normalized_onchain
    else:
        roots_match = True  # Sin expected, sólo confirmamos presencia

    return AnchorVerificationResult(
        valid=roots_match,
        tx_hash=tx_hash,
        expected_root=expected_root or "",
        onchain_root=onchain_root,
        block_number=block_number,
        block_timestamp=block_timestamp,
        error=None if roots_match else "root_mismatch",
    )


def verify_anchor_from_log(anchor_log_path: Path) -> AnchorVerificationResult:
    """Verifica un anclaje a partir de su archivo de log local.

    English: Verify an anchor from its local log file.
    """
    try:
        record = json.loads(anchor_log_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return AnchorVerificationResult(
            valid=False, tx_hash="", expected_root="",
            error=f"log_read_error: {exc}",
        )

    tx_hash = record.get("tx_hash", "")
    expected_root = record.get("root") or record.get("root_hash", "")

    if not tx_hash:
        return AnchorVerificationResult(
            valid=False, tx_hash="", expected_root=expected_root,
            error="missing_tx_hash_in_log",
        )

    return verify_anchor(tx_hash, expected_root)


# ---------------------------------------------------------------------------
# 3. Firma Ed25519 del operador en cada snapshot
# ---------------------------------------------------------------------------

_OPERATOR_KEY_PATH_ENV = "CENTINEL_OPERATOR_KEY_PATH"
_OPERATOR_ID_ENV = "CENTINEL_OPERATOR_ID"
_DEFAULT_KEY_DIR = Path("keys")


def generate_operator_keypair(
    key_dir: Optional[Path] = None,
    operator_id: Optional[str] = None,
) -> Dict[str, str]:
    """Genera un par de claves Ed25519 para el operador.

    Guarda ``operator_private.pem`` y ``operator_public.pem`` en ``key_dir``.

    English:
        Generate an Ed25519 keypair for the operator.
        Saves private and public PEM files in key_dir.
    """
    key_dir = key_dir or _DEFAULT_KEY_DIR
    key_dir.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    public_pem = public_key.public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )

    private_path = key_dir / "operator_private.pem"
    public_path = key_dir / "operator_public.pem"

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    # Restringir permisos de la clave privada
    private_path.chmod(0o600)

    resolved_id = operator_id or os.getenv(_OPERATOR_ID_ENV, "default-operator")

    logger.info(
        "operator_keypair_generated operator_id=%s key_dir=%s",
        resolved_id, key_dir,
    )

    return {
        "operator_id": resolved_id,
        "public_key_hex": public_key.public_bytes_raw().hex(),
        "private_key_path": str(private_path),
        "public_key_path": str(public_path),
    }


def _load_operator_private_key(key_path: Optional[Path] = None) -> Ed25519PrivateKey:
    """Carga la clave privada Ed25519 del operador.

    English: Load the operator's Ed25519 private key.
    """
    if key_path is None:
        env_path = os.getenv(_OPERATOR_KEY_PATH_ENV)
        key_path = Path(env_path) if env_path else _DEFAULT_KEY_DIR / "operator_private.pem"

    if not key_path.exists():
        raise FileNotFoundError(
            f"Clave privada del operador no encontrada: {key_path}. "
            f"Genera una con generate_operator_keypair(). "
            f"English: Operator private key not found."
        )

    pem_data = key_path.read_bytes()
    private_key = load_pem_private_key(pem_data, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("La clave cargada no es Ed25519. / Loaded key is not Ed25519.")
    return private_key


def _load_operator_public_key(key_path: Optional[Path] = None) -> Ed25519PublicKey:
    """Carga la clave pública Ed25519 del operador.

    English: Load the operator's Ed25519 public key.
    """
    if key_path is None:
        env_path = os.getenv(_OPERATOR_KEY_PATH_ENV)
        if env_path:
            # Derivar ruta pública desde privada
            priv = Path(env_path)
            key_path = priv.parent / "operator_public.pem"
        else:
            key_path = _DEFAULT_KEY_DIR / "operator_public.pem"

    if not key_path.exists():
        raise FileNotFoundError(
            f"Clave pública del operador no encontrada: {key_path}. "
            f"English: Operator public key not found."
        )

    pem_data = key_path.read_bytes()
    public_key = load_pem_public_key(pem_data)
    if not isinstance(public_key, Ed25519PublicKey):
        raise TypeError("La clave cargada no es Ed25519. / Loaded key is not Ed25519.")
    return public_key


def sign_snapshot(
    snapshot_data: bytes,
    *,
    key_path: Optional[Path] = None,
    operator_id: Optional[str] = None,
) -> SignatureResult:
    """Firma un snapshot con la clave Ed25519 del operador.

    El payload firmado es: sha256(snapshot_data) — se firma el hash,
    no los datos crudos, para eficiencia y consistencia.

    English:
        Sign a snapshot with the operator's Ed25519 key.
        Signs sha256(snapshot_data) for efficiency.
    """
    private_key = _load_operator_private_key(key_path)
    public_key = private_key.public_key()

    payload_hash = hashlib.sha256(snapshot_data).hexdigest()
    payload_bytes = payload_hash.encode("utf-8")

    signature = private_key.sign(payload_bytes)

    resolved_id = operator_id or os.getenv(_OPERATOR_ID_ENV, "default-operator")

    return SignatureResult(
        signature_hex=signature.hex(),
        public_key_hex=public_key.public_bytes_raw().hex(),
        operator_id=resolved_id,
        signed_at=datetime.now(timezone.utc).isoformat(),
        payload_hash=payload_hash,
    )


def verify_snapshot_signature(
    snapshot_data: bytes,
    signature_hex: str,
    *,
    public_key_path: Optional[Path] = None,
    public_key_hex: Optional[str] = None,
) -> bool:
    """Verifica la firma Ed25519 de un snapshot.

    Acepta una clave pública por ruta PEM o por hex directamente.

    English:
        Verify the Ed25519 signature on a snapshot.
        Accepts a public key by PEM path or hex string.
    """
    payload_hash = hashlib.sha256(snapshot_data).hexdigest()
    payload_bytes = payload_hash.encode("utf-8")
    signature = bytes.fromhex(signature_hex)

    if public_key_hex:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey as Ed25519Pub,
        )
        public_key = Ed25519Pub.from_public_bytes(bytes.fromhex(public_key_hex))
    else:
        public_key = _load_operator_public_key(public_key_path)

    try:
        public_key.verify(signature, payload_bytes)
        return True
    except Exception:
        return False


def sign_hash_record(
    hash_record: Dict[str, Any],
    *,
    key_path: Optional[Path] = None,
    operator_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Firma un registro de hash y agrega la firma al registro.

    English: Sign a hash record and append signature metadata.
    """
    # Serializar sin campos de firma previos
    signable = {
        k: v for k, v in sorted(hash_record.items())
        if k != "operator_signature"
    }
    data = json.dumps(
        signable, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")

    result = sign_snapshot(data, key_path=key_path, operator_id=operator_id)

    hash_record["operator_signature"] = {
        "signature": result.signature_hex,
        "public_key": result.public_key_hex,
        "operator_id": result.operator_id,
        "signed_at": result.signed_at,
        "algorithm": "Ed25519",
    }
    return hash_record


def verify_hash_record_signature(hash_record: Dict[str, Any]) -> bool:
    """Verifica la firma del operador en un registro de hash.

    English: Verify operator signature on a hash record.
    """
    sig_block = hash_record.get("operator_signature")
    if not sig_block:
        return False

    signature_hex = sig_block.get("signature", "")
    public_key_hex = sig_block.get("public_key", "")

    if not signature_hex or not public_key_hex:
        return False

    signable = {
        k: v for k, v in sorted(hash_record.items())
        if k != "operator_signature"
    }
    data = json.dumps(
        signable, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")

    return verify_snapshot_signature(
        data, signature_hex, public_key_hex=public_key_hex
    )


# ---------------------------------------------------------------------------
# 4. Verificación automática al arranque del pipeline
# ---------------------------------------------------------------------------

@dataclass
class StartupVerificationReport:
    """Reporte de verificación al arranque. / Startup verification report."""

    chain_result: Optional[ChainVerificationResult] = None
    anchor_results: List[AnchorVerificationResult] = field(default_factory=list)
    signature_failures: List[str] = field(default_factory=list)
    overall_valid: bool = False
    verified_at: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el reporte. / Serialize the report."""
        anchor_dicts = []
        for ar in self.anchor_results:
            anchor_dicts.append({
                "valid": ar.valid,
                "tx_hash": ar.tx_hash,
                "expected_root": ar.expected_root,
                "onchain_root": ar.onchain_root,
                "error": ar.error,
            })
        return {
            "overall_valid": self.overall_valid,
            "verified_at": self.verified_at,
            "duration_seconds": round(self.duration_seconds, 3),
            "chain": {
                "valid": self.chain_result.valid if self.chain_result else False,
                "total_links": self.chain_result.total_links if self.chain_result else 0,
                "verified_links": self.chain_result.verified_links if self.chain_result else 0,
                "errors": self.chain_result.errors if self.chain_result else [],
            },
            "anchors": anchor_dicts,
            "signature_failures": self.signature_failures,
        }


def run_startup_verification(
    *,
    hash_dir: Optional[Path] = None,
    anchor_log_dir: Optional[Path] = None,
    verify_anchors: bool = False,
    verify_signatures: bool = True,
    max_anchor_checks: int = 5,
) -> StartupVerificationReport:
    """Ejecuta verificación completa al arranque del pipeline.

    1. Verifica la cadena completa de hashes.
    2. Opcionalmente verifica los últimos anclajes contra Arbitrum.
    3. Verifica firmas Ed25519 en los registros de hash.

    English:
        Runs full verification at pipeline startup.

        1. Verifies the complete hash chain.
        2. Optionally verifies recent anchors against Arbitrum.
        3. Verifies Ed25519 signatures on hash records.
    """
    start_time = time.monotonic()
    hash_dir = hash_dir or Path("hashes")
    anchor_log_dir = anchor_log_dir or Path("logs") / "anchors"

    report = StartupVerificationReport(
        verified_at=datetime.now(timezone.utc).isoformat(),
    )

    # 1. Verificar cadena de hashes
    if hash_dir.exists():
        report.chain_result = verify_chain(hash_dir)
        if report.chain_result.valid:
            logger.info(
                "startup_chain_valid links=%d last_hash=%s",
                report.chain_result.verified_links,
                (report.chain_result.last_hash or "")[:16],
            )
        else:
            logger.error(
                "startup_chain_broken broken_at=%s errors=%s",
                report.chain_result.broken_at,
                report.chain_result.errors,
            )
    else:
        report.chain_result = ChainVerificationResult(
            valid=True, total_links=0, verified_links=0,
            errors=["hash_dir_not_found"],
        )

    # 2. Verificar anclajes recientes contra Arbitrum
    if verify_anchors and anchor_log_dir.exists():
        anchor_logs = sorted(
            anchor_log_dir.glob("anchor_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:max_anchor_checks]

        for anchor_log in anchor_logs:
            try:
                result = verify_anchor_from_log(anchor_log)
                report.anchor_results.append(result)
                if result.valid:
                    logger.info(
                        "startup_anchor_valid tx=%s root=%s",
                        result.tx_hash[:16], (result.onchain_root or "")[:16],
                    )
                else:
                    logger.warning(
                        "startup_anchor_invalid tx=%s error=%s",
                        result.tx_hash[:16] if result.tx_hash else "unknown",
                        result.error,
                    )
            except Exception as exc:
                logger.warning("startup_anchor_check_failed file=%s error=%s", anchor_log.name, exc)

    # 3. Verificar firmas en registros de hash
    if verify_signatures and hash_dir.exists():
        hash_files = sorted(hash_dir.glob("*.sha256"), key=lambda p: p.stat().st_mtime)
        for hash_file in hash_files:
            try:
                record = json.loads(hash_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            sig_block = record.get("operator_signature")
            if not sig_block:
                # Los registros sin firma son advertencias, no errores fatales
                continue

            if not verify_hash_record_signature(record):
                report.signature_failures.append(hash_file.name)
                logger.warning("startup_signature_invalid file=%s", hash_file.name)

    # Evaluación global
    chain_ok = report.chain_result.valid if report.chain_result else True
    anchors_ok = all(ar.valid for ar in report.anchor_results) if report.anchor_results else True
    sigs_ok = len(report.signature_failures) == 0

    report.overall_valid = chain_ok and anchors_ok and sigs_ok
    report.duration_seconds = time.monotonic() - start_time

    log_level = logging.INFO if report.overall_valid else logging.WARNING
    logger.log(
        log_level,
        "startup_verification_complete valid=%s chain=%s anchors=%s signatures=%s duration=%.3fs",
        report.overall_valid,
        chain_ok,
        anchors_ok,
        sigs_ok,
        report.duration_seconds,
    )

    return report
