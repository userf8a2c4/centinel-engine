"""Induced-outage diagnosis — tell "they are down" from "they cut us".

A corrupt authority that cannot rig the numbers can still try to make
the witness blind: blackhole the route, poison DNS, inject TCP resets,
or MITM the TLS so the observer simply "fails to connect" during the
contested count. A naive scraper records that as an ordinary upstream
failure and the manipulation leaves no trace.

This module runs a bounded, side-effect-free diagnosis when a fetch
fails and classifies *why*. The classification is conservative: it
never asserts fraud, it records SIGNALS (resolved IPs, the TLS
fingerprint actually presented vs. the pinned one, the exact failure
mode) into the same tamper-evident, signed, append-only stream as the
evidence itself. An auditor then sees, in the immutable log: "at
21:34 the TLS fingerprint to the target changed and DNS began
returning a new address" — that is what turns a silent cut into
published evidence of interference.

Design constraints:
- Country-agnostic: no hardcoded authority/host. The target comes from
  the URL already being fetched; expectations come from config. The
  same code defends an election in any country.
- Endurance-safe: every probe has a hard, short timeout and a capped
  attempt count, so the diagnosis can never wedge a capture loop that
  must run for a month.
- SSRF-safe: it probes ONLY the exact host:port parsed from the URL
  the system was already contacting. It never follows redirects and
  never contacts an attacker-influenced address.
- Zero new dependencies: stdlib socket/ssl only. Hashing/custody logic
  is reused, never reimplemented or weakened.

Bilingüe: diagnóstico de corte inducido. Distingue "la autoridad está
caída" de "alguien nos está cortando", y deja la señal firmada e
inmutable. Agnóstico de país: sirve para cualquier elección.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

_LOGGER = logging.getLogger("centinel.connectivity")

_DEFAULT_LOG_DIR = Path("data") / "transparency"
_LOG_FILENAME = "degradation_log.jsonl"

_DEFAULT_PROBE_TIMEOUT = 5.0
_MAX_PROBE_TIMEOUT = 15.0

# Conservative taxonomy. *_suspected names are signals, not verdicts.
UPSTREAM_UNAVAILABLE = "upstream_unavailable"
DNS_ANOMALY_SUSPECTED = "dns_anomaly_suspected"
TLS_PINNING_FAILURE = "tls_pinning_failure"
TLS_ANOMALY_SUSPECTED = "tls_anomaly_suspected"
CONNECTION_RESET_SUSPECTED = "connection_reset_suspected"
ROUTE_BLACKHOLE_SUSPECTED = "route_blackhole_suspected"
INDETERMINATE = "indeterminate"

# Which classifications are signals of *targeted interference* (vs. the
# authority's own inoperancy). Auditors filter on this flag.
_INTERFERENCE = frozenset(
    {
        DNS_ANOMALY_SUSPECTED,
        TLS_PINNING_FAILURE,
        TLS_ANOMALY_SUSPECTED,
        CONNECTION_RESET_SUSPECTED,
        ROUTE_BLACKHOLE_SUSPECTED,
    }
)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_probe_timeout() -> float:
    raw = os.getenv("CENTINEL_CONNECTIVITY_PROBE_TIMEOUT", "").strip()
    if not raw:
        return _DEFAULT_PROBE_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_PROBE_TIMEOUT
    if value <= 0:
        return _DEFAULT_PROBE_TIMEOUT
    return min(value, _MAX_PROBE_TIMEOUT)


def _expected_cert_sha256() -> Optional[str]:
    """Pinned cert fingerprint. Generic var preferred; legacy honored.

    Non-regression: existing deployments set CENTINEL_CNE_CERT_SHA256.
    A new country sets the country-agnostic CENTINEL_PINNED_CERT_SHA256.
    Both work; the explicit generic one wins if both are present.
    """
    for var in ("CENTINEL_PINNED_CERT_SHA256", "CENTINEL_CNE_CERT_SHA256"):
        val = os.getenv(var, "").strip().lower().replace(":", "")
        if val:
            return val
    return None


def _expected_ips() -> List[str]:
    raw = os.getenv("CENTINEL_EXPECTED_RESOLVED_IPS", "").strip()
    if not raw:
        return []
    return [ip.strip() for ip in raw.split(",") if ip.strip()]


def _probe_dns(host: str, timeout: float) -> Dict[str, Any]:
    """Resolve the host. Pure lookup, no connection."""
    socket.setdefaulttimeout(timeout)
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        ips = sorted({info[4][0] for info in infos})
        return {"resolved": True, "ips": ips}
    except socket.gaierror as exc:
        return {"resolved": False, "error": f"gaierror:{exc}"}
    except (socket.timeout, OSError) as exc:
        return {"resolved": False, "error": f"{type(exc).__name__}:{exc}"}
    finally:
        socket.setdefaulttimeout(None)


def _probe_tcp_tls(host: str, port: int, use_tls: bool, timeout: float) -> Dict[str, Any]:
    """One bounded TCP (and optional TLS) attempt to the exact target.

    Returns the failure mode and, on a successful TLS handshake, the
    peer certificate SHA-256 so it can be compared to the pin.
    """
    out: Dict[str, Any] = {"tcp_connected": False}
    sock = None
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        out["tcp_connected"] = True
    except socket.timeout:
        out["tcp_error"] = "timeout"
        return out
    except ConnectionResetError:
        out["tcp_error"] = "reset"
        return out
    except ConnectionRefusedError:
        out["tcp_error"] = "refused"
        return out
    except OSError as exc:
        out["tcp_error"] = f"{type(exc).__name__}:{exc}"
        return out

    try:
        if not use_tls:
            return out
        # verify_mode disabled ON PURPOSE: we are not trusting the
        # connection, we are *fingerprinting whatever is presented* to
        # detect a MITM. The pin comparison is the real check.
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        sock.settimeout(timeout)
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
            if der:
                out["peer_cert_sha256"] = _sha256_hex(der)
            out["tls_handshake"] = True
    except ssl.SSLError as exc:
        out["tls_error"] = f"SSLError:{exc}"
    except socket.timeout:
        out["tls_error"] = "timeout"
    except OSError as exc:
        out["tls_error"] = f"{type(exc).__name__}:{exc}"
    finally:
        try:
            if sock is not None:
                sock.close()
        except OSError:
            pass
    return out


def diagnose_connectivity(
    url: str,
    *,
    exception_text: str = "",
    exception_type: str = "",
    probe_timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """Classify why a fetch to `url` failed. Never raises.

    Bounded and side-effect-free: at most one DNS lookup and one
    TCP/TLS attempt to the exact host already being fetched, each with
    a hard short timeout.
    """
    diagnosed_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    timeout = probe_timeout if probe_timeout is not None else _resolve_probe_timeout()
    verdict: Dict[str, Any] = {
        "version": 1,
        "diagnosed_at_utc": diagnosed_at,
        "target_url_host": None,
        "classification": INDETERMINATE,
        "is_interference_signal": False,
        "confidence": "low",
        "probe_timeout_seconds": timeout,
        "exception_type": exception_type,
        "exception_excerpt": (exception_text or "")[:300],
        "signals": {},
        "explanation": "",
    }
    try:
        parts = urlsplit(url)
        host = parts.hostname
        if not host:
            verdict["explanation"] = "unparseable_target_url"
            return verdict
        use_tls = (parts.scheme or "https").lower() == "https"
        port = parts.port or (443 if use_tls else 80)
        verdict["target_url_host"] = host

        dns = _probe_dns(host, timeout)
        verdict["signals"]["dns"] = dns
        expected_ips = _expected_ips()

        if not dns.get("resolved"):
            verdict["classification"] = DNS_ANOMALY_SUSPECTED
            verdict["confidence"] = "medium"
            verdict["explanation"] = (
                "Hostname did not resolve. If it resolved before during "
                "this count, this is a DNS-tampering signal, not the "
                "authority being down."
            )
            verdict["is_interference_signal"] = True
            return verdict

        observed_ips = dns.get("ips", [])
        if expected_ips and not (set(observed_ips) & set(expected_ips)):
            verdict["classification"] = DNS_ANOMALY_SUSPECTED
            verdict["confidence"] = "high"
            verdict["signals"]["expected_ips"] = expected_ips
            verdict["explanation"] = (
                "DNS now returns addresses disjoint from the pinned "
                "expected set — a strong DNS-redirection signal."
            )
            verdict["is_interference_signal"] = True
            return verdict

        probe = _probe_tcp_tls(host, port, use_tls, timeout)
        verdict["signals"]["tcp_tls"] = probe

        if not probe.get("tcp_connected"):
            err = probe.get("tcp_error", "")
            if err == "reset":
                verdict["classification"] = CONNECTION_RESET_SUSPECTED
                verdict["confidence"] = "medium"
                verdict["explanation"] = (
                    "TCP reset while DNS resolves normally — possible "
                    "targeted reset injection rather than a dead server."
                )
            elif err == "timeout":
                verdict["classification"] = ROUTE_BLACKHOLE_SUSPECTED
                verdict["confidence"] = "medium"
                verdict["explanation"] = (
                    "DNS resolves but no TCP handshake completes — "
                    "possible route blackhole, or the authority is hard "
                    "down. Compare against independent mirrors."
                )
            elif err == "refused":
                verdict["classification"] = UPSTREAM_UNAVAILABLE
                verdict["confidence"] = "medium"
                verdict["explanation"] = (
                    "Connection refused: the host is reachable but the "
                    "service is not listening — typically the authority's "
                    "own inoperancy."
                )
            else:
                verdict["classification"] = INDETERMINATE
                verdict["explanation"] = f"tcp_failure:{err}"
            verdict["is_interference_signal"] = verdict["classification"] in _INTERFERENCE
            return verdict

        if use_tls:
            pin = _expected_cert_sha256()
            seen = probe.get("peer_cert_sha256")
            if pin and seen and seen != pin:
                verdict["classification"] = TLS_PINNING_FAILURE
                verdict["confidence"] = "high"
                verdict["signals"]["expected_cert_sha256"] = pin
                verdict["explanation"] = (
                    "The TLS certificate presented does not match the "
                    "pinned fingerprint — a man-in-the-middle signal. "
                    "The numbers cannot be trusted over this path."
                )
                verdict["is_interference_signal"] = True
                return verdict
            if probe.get("tls_error"):
                verdict["classification"] = TLS_ANOMALY_SUSPECTED
                verdict["confidence"] = "medium"
                verdict["explanation"] = (
                    "TLS handshake failed though TCP connected — "
                    "possible interception or forced downgrade."
                )
                verdict["is_interference_signal"] = True
                return verdict

        # Reached the service and TLS (if any) looked consistent: the
        # original failure was most likely upstream/application-level.
        verdict["classification"] = UPSTREAM_UNAVAILABLE
        verdict["confidence"] = "medium"
        verdict["explanation"] = (
            "Network path and TLS to the target look intact; the failure "
            "is most likely the authority's own server/application — "
            "their inoperancy, not a cut. Recorded for the timeline."
        )
        return verdict
    except Exception as exc:  # noqa: BLE001 - diagnosis must never raise
        _LOGGER.warning("connectivity_diagnosis_failed error=%s", exc)
        verdict["explanation"] = f"diagnosis_internal_error:{type(exc).__name__}"
        return verdict


def _maybe_sign(event: Dict[str, Any]) -> Dict[str, Any]:
    """Attach an operator signature if a key is configured.

    Same graceful pattern as transparency.py: the log's forensic value
    comes from being append-only and externally timestamped, so an
    absent key degrades to an unsigned (still immutable) record rather
    than dropping the evidence.
    """
    # BaseException (not just Exception) on purpose: signing is OPTIONAL
    # enrichment whose failure must degrade to an unsigned-but-immutable
    # record. In a hostile environment the crypto dependency itself can be
    # absent, corrupt, or sabotaged — its native backend can raise a
    # panic that is NOT an Exception subclass. The witness must keep
    # recording the interference signal regardless; an unsigned line in
    # the append-only, externally-timestamped log is still evidence.
    try:
        from .custody import sign_hash_record

        signable = {k: v for k, v in event.items() if k != "operator_signature"}
        digest = _sha256_hex(
            json.dumps(signable, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        signed = sign_hash_record({"degradation_event_digest": digest})
        event["operator_signature"] = signed.get("operator_signature")
    except FileNotFoundError:
        event["operator_signature"] = None
    except BaseException as exc:  # noqa: BLE001 - see rationale above
        _LOGGER.warning(
            "degradation_event_sign_failed type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        event["operator_signature"] = None
    return event


def record_degradation_event(
    verdict: Dict[str, Any],
    *,
    source_id: str = "",
    reason: str = "",
    log_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Sign and append a degradation event to the append-only log.

    Durability mirrors transparency.py exactly: write + fsync the file
    handle, then fsync the parent directory, so the line survives an
    induced crash. Append-only by contract — prior lines are never
    rewritten. Best-effort: never raises into the capture loop.
    """
    target_dir = log_dir or _DEFAULT_LOG_DIR
    event = {
        "version": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "source_id": source_id,
        "capture_failure_reason": reason,
        "verdict": verdict,
    }
    event = _maybe_sign(event)
    event["event_digest"] = _sha256_hex(
        json.dumps(
            {k: v for k, v in event.items() if k != "event_digest"},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        log_path = target_dir / _LOG_FILENAME
        line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        dir_fd = os.open(str(target_dir), os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        _LOGGER.warning(
            "degradation_event_recorded class=%s interference=%s source=%s",
            verdict.get("classification"),
            verdict.get("is_interference_signal"),
            source_id,
        )
    except Exception as exc:  # noqa: BLE001 - logging must not break capture
        _LOGGER.warning("degradation_event_persist_failed error=%s", exc)
    return event


def read_degradation_log(log_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read all degradation events from the append-only log."""
    target_dir = log_dir or _DEFAULT_LOG_DIR
    log_path = target_dir / _LOG_FILENAME
    if not log_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for raw in log_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            _LOGGER.warning("degradation_log_corrupt_line skipped")
    return out


def diagnose_and_record(
    url: str,
    *,
    source_id: str = "",
    reason: str = "",
    exception_text: str = "",
    exception_type: str = "",
    log_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Convenience: diagnose then record. Never raises into the caller."""
    try:
        verdict = diagnose_connectivity(
            url,
            exception_text=exception_text,
            exception_type=exception_type,
        )
        return record_degradation_event(
            verdict, source_id=source_id, reason=reason, log_dir=log_dir
        )
    except BaseException as exc:  # noqa: BLE001
        # Absolute guarantee: this helper can NEVER break the capture
        # loop that must run for a month, even if a sabotaged native
        # dependency raises a non-Exception panic.
        _LOGGER.warning(
            "diagnose_and_record_failed type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return {}
