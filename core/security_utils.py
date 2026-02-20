from __future__ import annotations

import ipaddress
import ssl
import socket
import threading
import hashlib
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlparse

SENSITIVE_HEADER_KEYS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
    "x-csrf-token",
}

_DNS_PIN_LOCK = threading.Lock()


@dataclass(frozen=True)
class OutboundTarget:
    """Validated outbound target with pinned resolved IPs."""

    url: str
    host: str
    port: int
    resolved_ips: frozenset[str]


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return headers with sensitive values redacted."""
    sanitized: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADER_KEYS:
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    return sanitized


def _host_in_allowlist(host: str, allowed_domains: set[str] | None) -> bool:
    if not allowed_domains:
        return True
    normalized = host.lower().rstrip(".")
    for allowed in allowed_domains:
        base = allowed.lower().rstrip(".")
        if normalized == base or normalized.endswith(f".{base}"):
            return True
    return False


def _is_public_ip(ip_value: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_value)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
        or ip.is_link_local
    )


def _resolve_public_ips(host: str, port: int) -> set[str]:
    try:
        addresses = {
            sockaddr[0]
            for _, _, _, _, sockaddr in socket.getaddrinfo(host, port)
            if sockaddr and sockaddr[0]
        }
    except OSError:
        return set()
    return {addr for addr in addresses if _is_public_ip(addr)}


def resolve_outbound_target(
    url: str,
    *,
    allowed_domains: set[str] | None = None,
    require_https: bool = True,
    enforce_public_ip_resolution: bool = False,
) -> OutboundTarget | None:
    """Validate URL and optionally resolve a pinned public-IP target."""
    parsed = urlparse(url)
    scheme_ok = parsed.scheme == "https" if require_https else parsed.scheme in {"http", "https"}
    if not scheme_ok:
        return None
    if not parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None
    if not _host_in_allowlist(parsed.hostname, allowed_domains):
        return None

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not enforce_public_ip_resolution:
        return OutboundTarget(url=url, host=parsed.hostname, port=port, resolved_ips=frozenset())

    public_ips = _resolve_public_ips(parsed.hostname, port)
    if not public_ips:
        return None
    return OutboundTarget(url=url, host=parsed.hostname, port=port, resolved_ips=frozenset(public_ips))


def is_safe_outbound_url(
    url: str,
    *,
    allowed_domains: set[str] | None = None,
    require_https: bool = True,
    enforce_public_ip_resolution: bool = False,
) -> bool:
    """Validate outbound URL with scheme, credentials, allowlist and optional IP checks."""
    return (
        resolve_outbound_target(
            url,
            allowed_domains=allowed_domains,
            require_https=require_https,
            enforce_public_ip_resolution=enforce_public_ip_resolution,
        )
        is not None
    )


def build_strict_tls_context() -> ssl.SSLContext:
    """Create a strict TLS client context with modern defaults."""
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def verify_peer_cert_sha256(cert_der: bytes, expected_fingerprint: str | None) -> bool:
    """Validate peer cert against an optional SHA-256 fingerprint."""
    if not expected_fingerprint:
        return True
    normalized = expected_fingerprint.lower().replace(":", "").strip()
    if not normalized:
        return True
    digest = hashlib.sha256(cert_der).hexdigest()
    return digest == normalized


@contextmanager
def pin_dns_resolution(target: OutboundTarget):
    """Temporarily pin DNS resolution for target host to previously validated IPs.

    This narrows DNS rebinding windows by ensuring request-time resolution for the
    target hostname can only return the approved public IP set.
    """
    if not target.resolved_ips:
        yield
        return

    original_getaddrinfo = socket.getaddrinfo

    def _guarded_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        results = original_getaddrinfo(host, port, family, type, proto, flags)
        normalized_host = str(host).lower().rstrip(".")
        target_host = target.host.lower().rstrip(".")
        if normalized_host != target_host:
            return results
        filtered = [
            item
            for item in results
            if item[4]
            and item[4][0]
            and item[4][0] in target.resolved_ips
            and _is_public_ip(item[4][0])
        ]
        if not filtered:
            raise socket.gaierror(f"Pinned DNS resolution blocked host={host}")
        return filtered

    with _DNS_PIN_LOCK:
        socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]
        try:
            yield
        finally:
            socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
