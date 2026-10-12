"""A named launch-home owner is not a satellite for lifecycle commands."""
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("command", ["restart", "stop"])
def test_named_owner_keeps_its_own_lifecycle(monkeypatch, tmp_path, command):
    from hermes_cli import gateway_profile_lifecycle as lifecycle
    from hermes_cli import gateway as gw
    from gateway import host_topology
    from gateway import profile_serving

    home = tmp_path / "profiles" / "coder"
    home.mkdir(parents=True)
    monkeypatch.setattr(gw, "_current_profile_name", lambda: "coder")
    monkeypatch.setattr(lifecycle, "get_hermes_home", lambda: home)
    monkeypatch.setattr(host_topology, "host_multiplexer_serving",
                        lambda name: SimpleNamespace(home=home, profiles=("default", "coder")))
    monkeypatch.setattr(lifecycle, "profile_is_standalone",
                        lambda selected: pytest.fail("owner must be handled before satellite policy"))
    assert lifecycle.profile_lifecycle(command, SimpleNamespace(all=False, force=False)) is False


def test_satellite_does_not_get_owner_permission(monkeypatch, tmp_path):
    from hermes_cli import gateway_profile_lifecycle as lifecycle
    from hermes_cli import gateway as gw
    from gateway import host_topology
    from gateway import profile_serving

    own = tmp_path / "profiles" / "coder"
    owner = tmp_path / "profiles" / "host"
    own.mkdir(parents=True)
    owner.mkdir()
    monkeypatch.setattr(gw, "_current_profile_name", lambda: "coder")
    monkeypatch.setattr(lifecycle, "get_hermes_home", lambda: own)
    monkeypatch.setattr(host_topology, "host_multiplexer_serving",
                        lambda name: SimpleNamespace(home=owner, profiles=("coder", "host")))
    monkeypatch.setattr(lifecycle, "profile_is_standalone",
                        lambda selected: (_ for _ in ()).throw(RuntimeError("satellite path reached")))
    with pytest.raises(RuntimeError, match="satellite path reached"):
        lifecycle.profile_lifecycle("restart", SimpleNamespace(all=False, force=False))
