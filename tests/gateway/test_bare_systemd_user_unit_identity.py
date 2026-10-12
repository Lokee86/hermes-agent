"""Bare systemd units must be recognized for non-root Linux accounts."""
from pathlib import Path
from gateway import service_identity


def test_nonroot_bare_user_unit_pins_service_identity(monkeypatch, tmp_path):
    from gateway import systemd_identity
    account = tmp_path / "account"
    account.mkdir()
    profile = tmp_path / "external-profile"
    profile.mkdir()
    unit = account / "hermes-gateway.service"
    unit.write_text(f'[Service]\nEnvironment="HERMES_HOME={profile}"\n')
    monkeypatch.setattr(service_identity.sys, "platform", "linux")
    monkeypatch.setattr(service_identity.os, "geteuid", lambda: 1001, raising=False)
    monkeypatch.setattr(systemd_identity, "user_unit_dir", lambda: account)
    monkeypatch.setattr(service_identity, "get_hermes_home", lambda: profile)
    monkeypatch.setattr(service_identity, "_native_service_homes", lambda: set())
    assert service_identity._bare_unit_pinned_home() == profile
    assert service_identity.service_suffix() == ""
    assert service_identity.service_name() == "hermes-gateway"


def test_nonroot_does_not_read_system_unit(monkeypatch, tmp_path):
    from gateway import systemd_identity
    account = tmp_path / "account"
    account.mkdir()
    monkeypatch.setattr(service_identity.sys, "platform", "linux")
    monkeypatch.setattr(service_identity.os, "geteuid", lambda: 1001, raising=False)
    monkeypatch.setattr(systemd_identity, "user_unit_dir", lambda: account)
    monkeypatch.setattr(service_identity, "SYSTEM_UNIT_DIR", tmp_path / "system")
    (tmp_path / "system").mkdir()
    (tmp_path / "system" / "hermes-gateway.service").write_text(
        '[Service]\nEnvironment="HERMES_HOME=/some/other/home"\n')
    assert service_identity._bare_unit_pinned_home() is None


def test_root_reads_bare_system_unit(monkeypatch, tmp_path):
    monkeypatch.setattr(service_identity.sys, "platform", "linux")
    monkeypatch.setattr(service_identity.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(service_identity, "SYSTEM_UNIT_DIR", tmp_path)
    (tmp_path / "hermes-gateway.service").write_text(
        '[Service]\nEnvironment="HERMES_HOME=/srv/hermes"\n')
    assert service_identity._bare_unit_pinned_home() == Path("/srv/hermes").resolve()
