from __future__ import annotations

import ipaddress
import socket
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


def is_safe_outbound_url(
    url: str,
    *,
    allowed_domains: set[str] | None = None,
    require_https: bool = True,
    enforce_public_ip_resolution: bool = False,
) -> bool:
    """Validate outbound URL with scheme, credentials, allowlist and IP checks."""
    parsed = urlparse(url)
    scheme_ok = parsed.scheme == "https" if require_https else parsed.scheme in {"http", "https"}
    if not scheme_ok:
        return False
    if not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    if not _host_in_allowlist(parsed.hostname, allowed_domains):
        return False

    if not enforce_public_ip_resolution:
        return True

    host = parsed.hostname
    try:
        addresses = {
            sockaddr[0]
            for _, _, _, _, sockaddr in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        }
    except OSError:
        return False
    return bool(addresses) and all(_is_public_ip(addr) for addr in addresses)
