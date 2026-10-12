"""An existing systemd unit belongs to its pinned Hermes home."""
import pytest
from gateway import systemd_lifecycle as lifecycle


@pytest.mark.parametrize("mode", ["foreign", "unknown", "owned"])
def test_install_existing_unit_respects_home_ownership(monkeypatch, tmp_path, mode):
    from gateway import systemd_identity, systemd_runtime, systemd_unit_state, systemd_linger
    home = tmp_path / "ours"
    home.mkdir()
    unit = tmp_path / "hermes.service"
    original = "[Unit]\nDescription=foreign installation\n"
    unit.write_text(original)
    events = []
    monkeypatch.setattr(lifecycle, "get_hermes_home", lambda: home)
    monkeypatch.setattr(systemd_identity, "unit_path", lambda system=False: unit)
    monkeypatch.setattr(lifecycle.service_identity, "hermes_home_pinned_by_unit",
                        lambda path: str(home if mode == "owned" else tmp_path / "other") if mode != "unknown" else None)
    monkeypatch.setattr(systemd_runtime, "sync_home_from_unit", lambda system: events.append("sync"))
    monkeypatch.setattr(systemd_unit_state, "unit_is_current", lambda system: False)
    monkeypatch.setattr(systemd_unit_state, "refresh_if_needed", lambda system: events.append("refresh"))
    monkeypatch.setattr(lifecycle.service_identity, "service_name", lambda: "hermes.service")
    monkeypatch.setattr(systemd_runtime, "run_systemctl", lambda argv, **kwargs: events.append(tuple(argv)))
    monkeypatch.setattr(systemd_identity, "read_unit_user", lambda path: None)
    monkeypatch.setattr(systemd_linger, "ensure_linger_enabled", lambda: events.append("linger"))
    lifecycle.install(system=False, force=False, enable_on_startup=True)
    assert unit.read_text() == original
    if mode == "owned":
        assert events == ["sync", "refresh", ("enable", "hermes.service"), "linger"]
    else:
        assert events == []


def test_explicit_force_allows_reinstall_over_foreign_unit(monkeypatch, tmp_path):
    from gateway import systemd_identity, systemd_runtime, systemd_unit_state, systemd_linger, systemd_unit_render
    unit = tmp_path / "hermes.service"
    unit.write_text("foreign unit")
    monkeypatch.setattr(systemd_identity, "unit_path", lambda system=False: unit)
    monkeypatch.setattr(systemd_identity, "read_unit_user", lambda path: None)
    monkeypatch.setattr(lifecycle.service_identity, "hermes_home_pinned_by_unit",
                        lambda path: str(tmp_path / "other"))
    monkeypatch.setattr(systemd_unit_render, "generate_systemd_unit", lambda **kwargs: "new unit")
    monkeypatch.setattr(systemd_unit_state, "refuse_temp_home_write", lambda *args: False)
    monkeypatch.setattr(systemd_unit_state, "prepare_installation_launcher", lambda *args: None)
    monkeypatch.setattr(systemd_runtime, "run_systemctl", lambda *args, **kwargs: None)
    monkeypatch.setattr(systemd_linger, "ensure_linger_enabled", lambda: None)
    lifecycle.install(force=True, enable_on_startup=False)
    assert unit.read_text() == "new unit"
