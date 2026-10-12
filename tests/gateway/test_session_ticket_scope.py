"""Ticket scope is explicit and never elevated by the default client path."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(("scope", "expected"), [
    (None, None),
    ("host", "host"),
])
def test_ticket_scope_is_explicit(monkeypatch, tmp_path, scope, expected):
    from gateway import client, runtime, runtime_bootstrap_windows

    endpoint = SimpleNamespace(profile_id=str(tmp_path), instance_id="instance-1", control_home=None)
    observed = []

    def query(home, request, timeout):
        observed.append(json.loads(request))
        return (json.dumps({"protocol": 1, "id": 1, "ok": True,
                            "result": {"profile_id": endpoint.profile_id,
                                       "instance_id": endpoint.instance_id,
                                       "runtime_protocol": 1, "ticket": "grant"}}) + "\n").encode()

    monkeypatch.setattr(client, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(runtime, "control_home_for", lambda home, endpoint: home)
    monkeypatch.setattr(runtime_bootstrap_windows, "query_runtime_control", query)

    assert client._session_ticket(Path(tmp_path), endpoint, purpose="interactive", scope=scope) == "grant"
    params = observed[0]["params"]
    assert params["purpose"] == "interactive"
    assert params.get("scope") == expected
    assert ("scope" in params) is (expected is not None)
