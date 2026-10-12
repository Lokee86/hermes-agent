"""Ink bootstrap must acquire a served secondary's ticket from its multiplexer control home."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import gateway.runtime as gateway_runtime
import hermes_constants


_SCRIPT = Path(__file__).resolve().parents[2] / "ui-tui" / "scripts" / "gateway_bootstrap.py"


def _load_bootstrap():
    spec = importlib.util.spec_from_file_location("ink_gateway_bootstrap_test", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_served_secondary_uses_multiplexer_control_home(monkeypatch, tmp_path):
    module = _load_bootstrap()
    root = tmp_path.resolve()
    secondary = root / "profiles" / "cold"
    secondary.mkdir(parents=True)
    endpoint = SimpleNamespace(
        profile_id=str(secondary.resolve()),
        instance_id="mux-owner",
        api_origin="http://127.0.0.1:1234",
        runtime_protocol=1,
        control_home=str(root),
    )
    receipt = SimpleNamespace(state="ready", endpoint=endpoint, reason_code=None)

    monkeypatch.setattr(hermes_constants, "get_hermes_home", lambda: secondary)
    monkeypatch.setattr(gateway_runtime, "discover_gateway_endpoint", lambda home, timeout=5: receipt)

    seen = {}

    if module.os.name == "nt":
        import gateway.runtime_bootstrap_windows as windows_bootstrap

        def query_runtime_control(home, request, timeout):
            seen["control_home"] = Path(home).resolve()
            seen["request"] = json.loads(request)
            return json.dumps({
                "ok": True,
                "id": 1,
                "result": {
                    "instance_id": endpoint.instance_id,
                    "profile_id": endpoint.profile_id,
                    "ticket": "served-grant",
                },
            }).encode()

        monkeypatch.setattr(windows_bootstrap, "query_runtime_control", query_runtime_control)
    else:
        import gateway.runtime_discovery as discovery

        class FakeStream:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def readline(self, _limit):
                return json.dumps({
                    "ok": True,
                    "id": 1,
                    "result": {
                        "instance_id": endpoint.instance_id,
                        "profile_id": endpoint.profile_id,
                        "ticket": "served-grant",
                    },
                }).encode()

        class FakeSocket:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def sendall(self, request):
                seen["request"] = json.loads(request)

            def makefile(self, _mode):
                return FakeStream()

        def connect_private(home, timeout):
            seen["control_home"] = Path(home).resolve()
            return FakeSocket()

        monkeypatch.setattr(discovery, "connect_private", connect_private)

    result = module.bootstrap(False)

    assert seen["control_home"] == root
    assert seen["request"]["params"] == {
        "profile_id": endpoint.profile_id,
        "instance_id": endpoint.instance_id,
        "purpose": "interactive",
    }
    assert result["profile_id"] == endpoint.profile_id


def test_posix_bootstrap_uses_authenticated_private_connector(monkeypatch, tmp_path):
    import gateway.runtime_discovery as discovery

    module = _load_bootstrap()
    home = tmp_path.resolve()
    endpoint = SimpleNamespace(
        profile_id=str(home), instance_id="owner",
        api_origin="http://127.0.0.1:1234", runtime_protocol=1,
        control_home=None,
    )
    monkeypatch.setattr(module, "os", SimpleNamespace(name="posix", environ=module.os.environ))
    monkeypatch.setattr(hermes_constants, "get_hermes_home", lambda: home)
    monkeypatch.setattr(gateway_runtime, "discover_gateway_endpoint",
                        lambda home, timeout=5: SimpleNamespace(state="ready", endpoint=endpoint))
    calls = []

    class Peer:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            calls.append("closed")
        def sendall(self, request):
            calls.append(json.loads(request))
        def makefile(self, mode):
            assert mode == "rb"
            class Stream:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def readline(self, limit):
                    assert limit == 65537
                    return json.dumps({"ok": True, "id": 1, "result": {
                        "instance_id": endpoint.instance_id,
                        "profile_id": endpoint.profile_id, "ticket": "grant"}}).encode()
            return Stream()

    monkeypatch.setattr(discovery, "connect_private",
                        lambda control, timeout: (calls.append((control, timeout)), Peer())[1])
    result = module.bootstrap(False)
    assert calls[0] == (home, 5)
    assert calls[1]["verb"] == "session-ticket"
    assert calls[-1] == "closed"
    assert result["profile_id"] == str(home)
