"""Bare gateway process discovery must prove installation ownership before stop."""

from pathlib import Path

import pytest

from gateway import process_discovery as discovery


def _scan_bare_gateway(
    monkeypatch,
    *,
    current_home: Path,
    owner_home: str | None,
    env_readable: bool,
    owns_bare_service: bool,
) -> list[int]:
    pid = 424242
    monkeypatch.setattr(discovery, "get_hermes_home", lambda: current_home)
    monkeypatch.setattr(discovery._service_identity, "profile_arg", lambda home: "")
    monkeypatch.setattr(
        discovery._service_identity,
        "home_owns_bare_service_name",
        lambda home: owns_bare_service,
    )
    monkeypatch.setattr(
        discovery,
        "_pid_hermes_home",
        lambda candidate: (env_readable, owner_home),
    )
    monkeypatch.setattr(
        discovery,
        "_iter_proc_cmdlines",
        lambda exclude: iter([(pid, "hermes gateway run")]),
    )
    monkeypatch.setattr(discovery, "_get_ancestor_pids", set)
    monkeypatch.setattr(discovery, "is_windows", lambda: False)
    monkeypatch.setattr(discovery.os.path, "isdir", lambda path: path == "/proc")
    return discovery._scan_gateway_pids(set())


def test_bare_scan_rejects_gateway_from_another_root(monkeypatch, tmp_path):
    ours = tmp_path / "ours"
    other = tmp_path / "other"

    assert _scan_bare_gateway(
        monkeypatch,
        current_home=ours,
        owner_home=str(other),
        env_readable=True,
        owns_bare_service=False,
    ) == []


def test_bare_scan_accepts_gateway_with_matching_live_home(monkeypatch, tmp_path):
    ours = tmp_path / "ours"

    assert _scan_bare_gateway(
        monkeypatch,
        current_home=ours,
        owner_home=str(ours),
        env_readable=True,
        owns_bare_service=False,
    ) == [424242]


@pytest.mark.parametrize(
    ("env_readable", "owns_bare_service", "expected"),
    [
        (False, False, []),
        (False, True, [424242]),
        (True, True, []),
    ],
)
def test_bare_scan_unreadable_environment_fallback_is_narrow(
    monkeypatch,
    tmp_path,
    env_readable,
    owns_bare_service,
    expected,
):
    assert _scan_bare_gateway(
        monkeypatch,
        current_home=tmp_path / "ours",
        owner_home=None,
        env_readable=env_readable,
        owns_bare_service=owns_bare_service,
    ) == expected


def test_pid_home_uses_explicit_process_environment(monkeypatch, tmp_path):
    home = tmp_path / "foreign-root"
    monkeypatch.setattr(
        discovery,
        "_pid_environment",
        lambda pid: {"HERMES_HOME": str(home), "HOME": str(tmp_path / "account")},
    )

    assert discovery._pid_hermes_home(99) == (True, str(home))


def test_pid_home_reports_unreadable_environment_separately(monkeypatch):
    monkeypatch.setattr(discovery, "_pid_environment", lambda pid: None)

    assert discovery._pid_hermes_home(99) == (False, None)
