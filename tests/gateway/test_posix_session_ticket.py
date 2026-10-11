"""POSIX session-ticket transport regression for the Gateway client."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gateway.client import GatewayClientError, _session_ticket


pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX private socket path")


class FakePeer:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = []
        self.timeouts = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def sendall(self, data):
        self.sent.append(data)

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def recv(self, size):
        assert size == 4096
        return self.chunks.pop(0)


def _response():
    return (json.dumps({
        "ok": True, "protocol": 1, "id": 1,
        "result": {
            "profile_id": "primary", "instance_id": "runtime-1",
            "runtime_protocol": 1, "ticket": "ticket-secret",
        },
    }).encode() + b"\n")


def _endpoint():
    return SimpleNamespace(profile_id="primary", instance_id="runtime-1")


def test_posix_session_ticket_uses_private_connection_and_exchanges_request(tmp_path):
    peer = FakePeer([_response()[:12], _response()[12:]])
    endpoint = _endpoint()
    with (
        patch("gateway.runtime.control_home_for", return_value=tmp_path) as control_home,
        patch("gateway.runtime_discovery.connect_private", return_value=peer) as connect,
    ):
        ticket = _session_ticket(Path(tmp_path), endpoint, purpose="interactive")
    assert ticket == "ticket-secret"
    control_home.assert_called_once_with(Path(tmp_path), endpoint)
    connect.assert_called_once_with(tmp_path, 5)
    assert peer.closed
    assert peer.timeouts and all(0 < t <= 5 for t in peer.timeouts)
    assert json.loads(peer.sent[0]) == {
        "protocol": 1, "id": 1, "verb": "session-ticket",
        "params": {"profile_id": "primary", "instance_id": "runtime-1", "purpose": "interactive"},
    }


def test_posix_session_ticket_preserves_deadline_timeout(tmp_path):
    peer = FakePeer([b"partial"])
    with (
        patch("gateway.runtime.control_home_for", return_value=tmp_path),
        patch("gateway.runtime_discovery.connect_private", return_value=peer) as connect,
        patch("gateway.client.time.monotonic", side_effect=[100.0, 105.0]),
    ):
        with pytest.raises(GatewayClientError, match="Gateway bootstrap timed out"):
            _session_ticket(tmp_path, _endpoint())
    connect.assert_called_once_with(tmp_path, 5)
    assert peer.closed
