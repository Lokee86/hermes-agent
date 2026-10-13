"""A launchd definition pinned to another install must never be rewritten or reloaded."""
import plistlib

import pytest

from gateway import launchd_service as launchd


@pytest.mark.parametrize("foreign", [True, False])
def test_refresh_refuses_foreign_plist_before_any_effect(monkeypatch, tmp_path, foreign):
    home = tmp_path / "ours"
    home.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    plist = tmp_path / "gateway.plist"
    pinned = other if foreign else home
    original = plistlib.dumps(
        {
            "Label": "ai.hermes.gateway",
            "EnvironmentVariables": {"HERMES_HOME": str(pinned)},
        }
    )
    plist.write_bytes(original)
    events = []
    monkeypatch.setattr(launchd, "get_hermes_home", lambda: home)
    monkeypatch.setattr(launchd, "get_launchd_plist_path", lambda: plist)
    monkeypatch.setattr(launchd, "launchd_plist_is_current", lambda: False)
    monkeypatch.setattr(
        launchd, "generate_launchd_plist", lambda: "<plist>replacement</plist>"
    )
    monkeypatch.setattr(
        launchd.service_process,
        "prepare_installation_launcher",
        lambda **kw: events.append("launcher"),
    )
    monkeypatch.setattr(
        launchd, "_launchd_domain", lambda: events.append("reload") or "gui/1"
    )
    monkeypatch.setattr(launchd, "refuse_temp_home_write", lambda *a: False)
    if foreign:
        assert launchd.refresh_launchd_plist_if_needed() is False
        assert plist.read_bytes() == original
        assert events == []
    else:
        assert launchd._launchd_plist_owned_by_current_home(plist)


@pytest.mark.parametrize(
    "invalid", [b"garbage", plistlib.dumps({"Label": "gateway"})]
)
def test_malformed_plist_cannot_be_claimed(monkeypatch, tmp_path, invalid):
    path = tmp_path / "gateway.plist"
    path.write_bytes(invalid)
    monkeypatch.setattr(launchd, "get_hermes_home", lambda: tmp_path)
    assert not launchd._launchd_plist_owned_by_current_home(path)


def _foreign_install(monkeypatch, tmp_path):
    home = tmp_path / "ours"
    other = tmp_path / "other"
    home.mkdir()
    other.mkdir()
    plist = tmp_path / "gateway.plist"
    original = plistlib.dumps(
        {"EnvironmentVariables": {"HERMES_HOME": str(other)}}
    )
    plist.write_bytes(original)
    monkeypatch.setattr(launchd, "get_hermes_home", lambda: home)
    monkeypatch.setattr(launchd, "get_launchd_plist_path", lambda: plist)
    monkeypatch.setattr(launchd, "get_launchd_label", lambda: "ai.hermes.gateway")
    monkeypatch.setattr(
        launchd, "_launchctl_label_supervising_process", lambda label: False
    )
    monkeypatch.setattr(launchd, "launchd_plist_is_current", lambda: True)
    return plist, original


def test_install_foreign_plist_refuses_even_when_current(monkeypatch, tmp_path):
    plist, original = _foreign_install(monkeypatch, tmp_path)

    launchd.launchd_install(force=False, start_now=False)

    assert plist.read_bytes() == original


def test_force_reinstall_does_not_repoint_foreign_plist(monkeypatch, tmp_path):
    plist, original = _foreign_install(monkeypatch, tmp_path)

    launchd.launchd_install(force=True, start_now=False)

    assert plist.read_bytes() == original


def test_force_unit_path_allows_explicit_launchd_repoint(monkeypatch, tmp_path):
    plist, _original = _foreign_install(monkeypatch, tmp_path)
    calls = []
    replacement = "<plist>replacement</plist>"
    monkeypatch.setattr(launchd, "generate_launchd_plist", lambda: replacement)
    monkeypatch.setattr(launchd, "refuse_temp_home_write", lambda *a: False)
    monkeypatch.setattr(
        launchd.service_process, "prepare_installation_launcher", lambda **kw: None
    )
    monkeypatch.setattr(launchd, "_launchd_domain", lambda: "gui/1")
    monkeypatch.setattr(
        launchd.subprocess,
        "run",
        lambda argv, **kwargs: calls.append(tuple(argv)),
    )

    launchd.launchd_install(
        force=False,
        start_now=False,
        force_unit_path=True,
    )

    assert plist.read_text(encoding="utf-8") == replacement
    assert calls and calls[-1][0:2] == ("launchctl", "bootout")
