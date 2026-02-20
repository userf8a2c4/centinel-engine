from __future__ import annotations

import socket
import ssl

import pytest

from core.security_utils import (
    OutboundTarget,
    build_strict_tls_context,
    pin_dns_resolution,
    resolve_outbound_target,
    verify_peer_cert_sha256,
)


def test_resolve_outbound_target_rejects_non_public_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_getaddrinfo(host, port, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    target = resolve_outbound_target("https://example.com/hook", enforce_public_ip_resolution=True)
    assert target is None


def test_pin_dns_resolution_blocks_rebinding_to_unpinned_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_getaddrinfo(host, port, *args, **kwargs):
        if host == "api.telegram.org":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", port))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    target = OutboundTarget(
        url="https://api.telegram.org/bot123/sendMessage",
        host="api.telegram.org",
        port=443,
        resolved_ips=frozenset({"149.154.167.220"}),
    )

    with pytest.raises(socket.gaierror):
        with pin_dns_resolution(target):
            pass


def test_pin_dns_resolution_does_not_monkeypatch_global_getaddrinfo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = socket.getaddrinfo

    def _fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("149.154.167.220", port))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    target = OutboundTarget(
        url="https://api.telegram.org/bot123/sendMessage",
        host="api.telegram.org",
        port=443,
        resolved_ips=frozenset({"149.154.167.220"}),
    )

    with pin_dns_resolution(target):
        assert socket.getaddrinfo is _fake_getaddrinfo
    assert socket.getaddrinfo is _fake_getaddrinfo
    assert original is not socket.getaddrinfo


def test_build_strict_tls_context_sets_tls12_minimum() -> None:
    context = build_strict_tls_context()
    assert isinstance(context, ssl.SSLContext)
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_verify_peer_cert_sha256_accepts_exact_match() -> None:
    cert_der = b"fake-cert"
    digest = __import__("hashlib").sha256(cert_der).hexdigest()
    assert verify_peer_cert_sha256(cert_der, digest)
    assert not verify_peer_cert_sha256(cert_der, "00" * 32)
