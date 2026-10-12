"""Failed authority retirement must not drop ownership or block other removals."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from gateway.run_profile_reconcile import GatewayProfileReconcileMixin


@pytest.mark.asyncio
async def test_failed_retirement_leaves_profile_owned(tmp_path, monkeypatch):
    from gateway import run_runtime

    home = tmp_path / "busy"
    runner = GatewayProfileReconcileMixin()
    runner.session_authorities = object()
    runner._served_profile_homes = {"busy": home}
    runner._profile_adapters = {"busy": {"test": object()}}
    calls = []

    async def refuse(_runner, _home):
        calls.append("refused")
        return False

    monkeypatch.setattr(run_runtime, "unserve_profile_runtime", refuse)
    monkeypatch.setattr(run_runtime, "release_profile_home",
                        lambda *_: calls.append("released"))
    assert await runner._unserve_profile("busy", home) is False
    assert calls == ["refused"]
    assert runner._served_profile_homes == {"busy": home}
    assert "busy" in runner._profile_adapters


@pytest.mark.asyncio
async def test_refused_removal_does_not_abort_other_removals(tmp_path, monkeypatch):
    from gateway import profile_serving

    busy, finished = tmp_path / "busy", tmp_path / "finished"
    runner = GatewayProfileReconcileMixin()
    runner._primary_profile_name = "default"
    runner._served_profile_homes = {"busy": busy, "finished": finished}
    runner._served_profile_signatures = {}
    runner._profile_configs = {}
    runner._live_resource_claims = lambda _active: {}
    runner._record_served_profiles = lambda _active, homes: setattr(
        runner, "_served_profile_homes", dict(homes))
    seen = []

    async def remove(name, _home):
        seen.append(name)
        return name != "busy"

    runner._unserve_profile = remove
    monkeypatch.setattr(profile_serving, "profiles_to_serve", lambda **kwargs: [])
    result = await runner._apply_profile_changes(
        {}, [], ["busy", "finished"], [], reason="test")
    assert seen == ["busy", "finished"]
    assert result["removed"] == ["finished"]
    assert runner._served_profile_homes == {"busy": busy}
