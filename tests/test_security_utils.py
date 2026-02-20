from __future__ import annotations

import socket

import pytest

from core.security_utils import OutboundTarget, pin_dns_resolution, resolve_outbound_target


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

    with pin_dns_resolution(target):
        with pytest.raises(socket.gaierror):
            socket.getaddrinfo("api.telegram.org", 443)
        other = socket.getaddrinfo("example.com", 443)
        assert other[0][4][0] == "93.184.216.34"
