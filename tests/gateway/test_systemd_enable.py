"""Canonical systemd enable operation used by migration."""
import pytest
from gateway import systemd_lifecycle


@pytest.mark.parametrize("system", [False, True])
def test_enable_routes_via_canonical_systemd_owner(monkeypatch, system):
    events = []
    monkeypatch.setattr(systemd_lifecycle, "prepare_action",
                        lambda action, requested: events.append(("prepare", action, requested)) or requested)
    monkeypatch.setattr(systemd_lifecycle.service_identity, "service_name", lambda: "hermes-gateway.service")
    monkeypatch.setattr(systemd_lifecycle.systemd_runtime, "run_systemctl",
                        lambda argv, **kwargs: events.append(("systemctl", argv, kwargs)))
    systemd_lifecycle.service_call("enable", system)
    assert events == [
        ("prepare", "enable", system),
        ("systemctl", ["enable", "hermes-gateway.service"],
         {"system": system, "check": True, "timeout": 30}),
    ]


def test_enable_requires_installed_unit(monkeypatch):
    def missing(action, system):
        assert action == "enable"
        raise SystemExit(1)
    monkeypatch.setattr(systemd_lifecycle, "prepare_action", missing)
    monkeypatch.setattr(systemd_lifecycle.systemd_runtime, "run_systemctl",
                        lambda *args, **kwargs: pytest.fail("must not enable missing unit"))
    with pytest.raises(SystemExit):
        systemd_lifecycle.service_call("enable")
