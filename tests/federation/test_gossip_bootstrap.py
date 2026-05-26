"""Coverage for gossip bootstrap helpers — guards against silent regressions
in mDNS discovery (e.g. autofix #533 broke this without test coverage).
"""

from __future__ import annotations

import socket

import pytest

from centinel.federation import gossip


def test_bootstrap_from_mdns_returns_list_with_default_env(monkeypatch):
    """Default env (no CENTINEL_MDNS_IFACE) must not raise and must return a list."""
    monkeypatch.delenv("CENTINEL_MDNS_IFACE", raising=False)
    result = gossip._bootstrap_from_mdns()
    assert isinstance(result, list)


def test_bootstrap_from_mdns_accepts_wildcard_iface(monkeypatch):
    """CENTINEL_MDNS_IFACE=0.0.0.0 must NOT raise — the autofix that rejected
    this default broke mDNS for every deployment that set the obvious value."""
    monkeypatch.setenv("CENTINEL_MDNS_IFACE", "0.0.0.0")
    result = gossip._bootstrap_from_mdns()
    assert isinstance(result, list)


def test_bootstrap_from_mdns_accepts_empty_iface(monkeypatch):
    """Empty CENTINEL_MDNS_IFACE must fall back to a working default, not raise."""
    monkeypatch.setenv("CENTINEL_MDNS_IFACE", "")
    result = gossip._bootstrap_from_mdns()
    assert isinstance(result, list)


def test_bootstrap_from_mdns_binds_to_configured_iface(monkeypatch):
    """Verify the configured interface is actually passed to sock.bind."""
    monkeypatch.setenv("CENTINEL_MDNS_IFACE", "127.0.0.1")

    captured = {}

    real_socket = socket.socket

    class _FakeSocket:
        def __init__(self, *a, **kw):
            self._real = real_socket(*a, **kw)

        def settimeout(self, t):
            self._real.settimeout(t)

        def setsockopt(self, *a, **kw):
            try:
                self._real.setsockopt(*a, **kw)
            except OSError:
                pass

        def bind(self, addr):
            captured["bind"] = addr
            self._real.bind(addr)

        def sendto(self, *a, **kw):
            return 0

        def recvfrom(self, n):
            raise socket.timeout()

        def close(self):
            self._real.close()

    monkeypatch.setattr(gossip.socket, "socket", _FakeSocket)
    gossip._bootstrap_from_mdns()
    assert captured.get("bind") == ("127.0.0.1", gossip._MDNS_PORT)
