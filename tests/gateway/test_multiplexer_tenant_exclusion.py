"""A same-named profile in a different Hermes installation is not served here."""
from pathlib import Path
from types import SimpleNamespace


def test_foreign_host_is_excluded_before_control_connection(monkeypatch, tmp_path):
    from gateway import host_attach, host_rendezvous
    import hermes_constants

    local = tmp_path / "local"
    foreign = tmp_path / "foreign"
    local.mkdir()
    foreign.mkdir()
    record = SimpleNamespace(pid=123, home=str(foreign), profiles=("default", "coder"))
    monkeypatch.setattr(host_rendezvous, "read_record", lambda role: record)
    monkeypatch.setattr(host_rendezvous, "liveness_is_proven", lambda record: True)
    monkeypatch.setattr(hermes_constants, "get_hermes_home", lambda: local)
    monkeypatch.setattr(host_attach, "_identify", lambda home: (_ for _ in ()).throw(
        AssertionError("foreign owner's private socket must not be contacted")))
    assert host_attach._probe_host_gateway(0) is None


def test_cached_foreign_gateway_never_counts_as_serving_local_profile(monkeypatch, tmp_path):
    from gateway import host_attach
    import hermes_constants

    local, foreign = tmp_path / "local", tmp_path / "foreign"
    local.mkdir()
    foreign.mkdir()
    monkeypatch.setattr(hermes_constants, "get_hermes_home", lambda: local)
    gateway = host_attach.HostGateway(123, foreign, ("default", "coder"))
    monkeypatch.setattr(host_attach, "host_gateway", lambda **kwargs: gateway)
    assert host_attach.host_gateway_serving("coder") is None
    assert host_attach.host_gateway_serving("default") is None
    monkeypatch.setattr(hermes_constants, "get_hermes_home", lambda: foreign)
    assert host_attach.host_gateway_serving("coder") is gateway
