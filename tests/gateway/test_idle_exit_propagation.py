"""Step 23: idle-exit survives runtime ensure through unmanaged startup."""
from pathlib import Path

import pytest


@pytest.mark.parametrize("idle_exit", [False, True])
def test_ensure_propagates_idle_exit_to_unmanaged_spawn(tmp_path, monkeypatch, idle_exit):
    from gateway import runtime, runtime_multiplex, runtime_service, runtime_start

    calls = []
    checks = iter(["absent", "absent", "ready"])
    monkeypatch.setattr(runtime, "_update_fenced", lambda homes: False)
    monkeypatch.setattr(runtime, "_multiplexer_starting", lambda home: False)
    monkeypatch.setattr(runtime, "discover_gateway_endpoint",
                        lambda home, timeout: runtime.GatewayDiscovery(next(checks)))
    monkeypatch.setattr(runtime_multiplex, "multiplexer_serves_home", lambda home: None)
    monkeypatch.setattr(runtime_multiplex, "implied_host_root", lambda home: None)
    monkeypatch.setattr(runtime_service, "discover_existing_gateway_service", lambda target, deadline: None)
    monkeypatch.setattr(runtime_start, "spawn_unmanaged_gateway",
                        lambda home, *, deadline, idle_exit: calls.append((home, idle_exit)))
    result = runtime.ensure_gateway_runtime(tmp_path, timeout=5, idle_exit=idle_exit)
    assert result.state == "ready"
    assert calls == [(Path(tmp_path).resolve(), idle_exit)]


@pytest.mark.parametrize("idle_exit", [False, True])
def test_unmanaged_spawn_passes_cli_switch(tmp_path, monkeypatch, idle_exit):
    import subprocess
    from gateway import runtime_start
    from hermes_cli import _subprocess_compat

    seen = []
    monkeypatch.setattr(runtime_start, "remaining", lambda deadline: 1)
    monkeypatch.setattr(runtime_start, "windows_detach_popen_kwargs", lambda: {})
    monkeypatch.setattr(runtime_start.sys, "platform", "linux")
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kwargs: seen.append(args))
    runtime_start.spawn_unmanaged_gateway(tmp_path, deadline=100, idle_exit=idle_exit)
    assert len(seen) == 1
    assert ("--idle-exit" in seen[0]) is idle_exit
