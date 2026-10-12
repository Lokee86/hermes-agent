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


@pytest.mark.parametrize("current", [True, False])
@pytest.mark.parametrize("enable_on_startup", [True, False])
def test_install_existing_unit_enable_independent_of_refresh(
    monkeypatch, tmp_path, current, enable_on_startup
):
    from gateway import systemd_identity, systemd_runtime, systemd_unit_state, systemd_linger
    unit = tmp_path / "hermes-gateway.service"
    unit.write_text("[Unit]\nDescription=Hermes\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(systemd_identity, "unit_path", lambda system=False: unit)
    monkeypatch.setattr(systemd_identity, "read_unit_user", lambda path: None)
    monkeypatch.setattr(systemd_runtime, "sync_home_from_unit", lambda system: None)
    monkeypatch.setattr(systemd_lifecycle.service_identity, "service_name", lambda: "hermes-gateway.service")
    monkeypatch.setattr(systemd_unit_state, "unit_is_current", lambda system: current)
    monkeypatch.setattr(systemd_unit_state, "refresh_if_needed", lambda system: calls.append("refresh"))
    monkeypatch.setattr(systemd_runtime, "run_systemctl",
                        lambda argv, **kwargs: calls.append(("systemctl", argv, kwargs)))
    monkeypatch.setattr(systemd_linger, "ensure_linger_enabled", lambda: None)
    systemd_lifecycle.install(system=False, enable_on_startup=enable_on_startup)
    assert calls == (
        ([] if current else ["refresh"]) +
        ([("systemctl", ["enable", "hermes-gateway.service"],
           {"system": False, "check": True, "timeout": 30})] if enable_on_startup else [])
    )
