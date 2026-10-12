"""Worker-owner loopback never uses a proxy from the ambient environment."""
import json
from types import SimpleNamespace

from agent.runtime_session_store import WorkerRPC


def test_worker_rpc_explicitly_bypasses_proxy(monkeypatch, tmp_path):
    import websockets.sync.client as ws_client
    from gateway import runtime, runtime_discovery, client

    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    endpoint = SimpleNamespace(api_origin="http://127.0.0.1:9999", control_home=tmp_path)
    monkeypatch.setattr(runtime, "discover_gateway_endpoint",
                        lambda home, timeout: SimpleNamespace(state="ready", endpoint=endpoint))
    monkeypatch.setattr(runtime, "control_home_for", lambda home, descriptor: home)
    monkeypatch.setattr(runtime_discovery, "query_identify",
                        lambda home, timeout: {"pid": -1})
    monkeypatch.setattr(client, "_session_ticket", lambda *args, **kwargs: "ticket")

    observed = []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def send(self, payload): observed.append(json.loads(payload))
        def recv(self, timeout=None):
            return json.dumps({"id": 1, "result": {"ok": True}})
    def connect(url, **kwargs):
        assert url == "ws://127.0.0.1:9999/api/ws"
        assert kwargs["proxy"] is None
        observed.append(kwargs)
        return Connection()
    monkeypatch.setattr(ws_client, "connect", connect)
    assert WorkerRPC(tmp_path)("worker.persist", sequence=1) == {"ok": True}
    assert observed[1]["method"] == "worker.persist"
