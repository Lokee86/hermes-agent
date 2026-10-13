"""Compatibility coverage for the retired CLI service-owner facade."""

from gateway import service_definition, service_owner
from hermes_cli import gateway_service_owner


def test_service_owner_facade_routes_to_gateway_owner():
    assert (
        gateway_service_owner.definition_belongs_to_home
        is service_owner.definition_belongs_to_home
    )
    assert gateway_service_owner.pinned_home is service_owner.pinned_home
    assert (
        gateway_service_owner.unit_belongs_to_caller
        is service_owner.systemd_unit_belongs_to_caller
    )


def test_temp_home_guard_facade_routes_to_gateway_definition(monkeypatch, tmp_path):
    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    definition = (
        "[Service]\n"
        f'Environment="HERMES_HOME={tmp_path / "hermes-home"}"\n'
    )

    assert (
        gateway_service_owner.temp_home_in_service_definition(definition)
        == str(tmp_path / "hermes-home")
    )
    assert (
        gateway_service_owner.temp_home_in_service_definition
        is service_definition.temp_home_in_definition
    )

def test_systemd_install_cli_forwards_force_unit_path(monkeypatch):
    from types import SimpleNamespace

    import hermes_cli.gateway as gateway

    calls = []
    starts = []
    monkeypatch.setattr(gateway, "is_wsl", lambda: False)
    monkeypatch.setattr(
        gateway, "_remove_legacy_systemd_units_before_install", lambda **kwargs: None
    )
    monkeypatch.setattr(
        gateway._systemd_lifecycle,
        "install",
        lambda **kwargs: calls.append(kwargs) or False,
    )
    monkeypatch.setattr(
        gateway._systemd_lifecycle,
        "start",
        lambda **kwargs: starts.append(kwargs),
    )
    args = SimpleNamespace(
        start_now=True,
        start_on_login=False,
        force_unit_path=True,
    )

    gateway._install_systemd_from_cli(
        args,
        force=False,
        system=False,
        run_as_user=None,
    )

    assert calls == [
        {
            "force": False,
            "system": False,
            "run_as_user": None,
            "enable_on_startup": False,
            "force_unit_path": True,
        }
    ]
    assert starts == []


def test_launchd_install_cli_forwards_force_unit_path(monkeypatch):
    from types import SimpleNamespace

    import hermes_cli.gateway as gateway

    calls = []
    monkeypatch.setattr(gateway, "is_managed", lambda: False)
    monkeypatch.setattr(gateway, "_guard_named_profile_under_multiplexer", lambda **kwargs: None)
    monkeypatch.setattr(gateway, "_service_mgmt_blocked", lambda: False)
    monkeypatch.setattr(gateway, "_service_backend", lambda: "launchd")
    monkeypatch.setattr(gateway, "_is_service_installed", lambda: False)
    monkeypatch.setattr(
        gateway,
        "launchd_install",
        lambda force, **kwargs: calls.append((force, kwargs)),
    )
    args = SimpleNamespace(
        if_missing=False,
        force=False,
        force_unit_path=True,
        system=False,
        run_as_user=None,
        start_now=False,
    )

    gateway._cmd_install(args)

    assert calls == [
        (
            False,
            {
                "start_now": False,
                "force_unit_path": True,
            },
        )
    ]
