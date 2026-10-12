"""Hosted POSIX owner RPC uses the canonical authenticated control connector."""
import json
from types import SimpleNamespace


def test_hosted_posix_owner_request_uses_canonical_private_connector(monkeypatch, tmp_path):
    from gateway import session_hosted_transport as transport
    from gateway import runtime, runtime_discovery, control_socket

    home = tmp_path.resolve()
    endpoint = SimpleNamespace(profile_id=str(home), control_home=None)
    monkeypatch.setattr(transport, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(runtime, "discover_gateway_endpoint", lambda home, timeout:
                        SimpleNamespace(state="ready", endpoint=endpoint))
    monkeypatch.setattr(runtime, "control_home_for", lambda home, endpoint: home)
    observed = []

    class Peer:
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            observed.append("closed")
        def sendall(self, data):
            observed.append(json.loads(data))
        def settimeout(self, timeout):
            assert timeout > 0
        def recv(self, size):
            return (json.dumps({"ok": True, "protocol": 1, "id": 1,
                                "result": {"accepted": True}}) + "\n").encode()

    def connect(home_arg, timeout):
        observed.append(("connect", home_arg))
        return Peer()

    monkeypatch.setattr(runtime_discovery, "connect_private", connect)
    monkeypatch.setattr(control_socket, "_read_response_line", lambda read, deadline: read())
    result = transport.owner_request(home, "hosted-attest", {"selector": "demo"})
    assert result == {"accepted": True}
    assert observed[0] == ("connect", home)
    assert observed[1]["verb"] == "hosted-attest"
    assert observed[-1] == "closed"
