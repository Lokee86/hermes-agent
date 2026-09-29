"""Managed-runtime invariants for Gateway service process selection."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from gateway import service_process


def test_python_path_prefers_pm_store_interpreter(tmp_path, monkeypatch):
    selected = tmp_path / "store" / "python-gen" / ("python.exe" if sys.platform == "win32" else "bin/python3")
    selected.parent.mkdir(parents=True)
    selected.write_text("", encoding="utf-8")
    monkeypatch.setattr(service_process, "PROJECT_ROOT", tmp_path / "repo")
    monkeypatch.setattr("hermes_cli._launchers.resolve_store_python", lambda root: selected)

    assert service_process.python_path() == str(selected)


def test_python_path_falls_back_to_external_interpreter(tmp_path, monkeypatch):
    monkeypatch.setattr(service_process, "PROJECT_ROOT", tmp_path / "repo")
    monkeypatch.setattr("hermes_cli._launchers.resolve_store_python", lambda root: None)

    assert service_process.python_path() == sys.executable


def test_service_path_dirs_never_persist_python_environment(tmp_path, monkeypatch):
    project = tmp_path / "repo"
    (project / "venv" / "bin").mkdir(parents=True)
    (project / "node_modules" / ".bin").mkdir(parents=True)
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "ambient-venv"))
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "selected-generation"))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "base-python"))

    dirs = service_process.service_path_dirs(project)

    assert str(project / "venv" / "bin") not in dirs
    assert str(tmp_path / "selected-generation" / "bin") not in dirs
    assert str(project / "node_modules" / ".bin") in dirs


def test_append_node_dir_prefers_pm_facts_over_ambient_path(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    store = home / "tools"
    node_dir = store / "node-v22"
    npm_dir = store / "npm-v10" / "bin"
    node_dir.mkdir(parents=True)
    npm_dir.mkdir(parents=True)
    (store / "facts.json").write_text(
        json.dumps({
            "schema": 1,
            "packages": {
                "node": {"entry": "node-v22", "env": {"PATH": ["{{store}}/node-v22"]}},
                "npm": {"entry": "npm-v10", "env": {"PATH": ["{{store}}/npm-v10/bin"]}},
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(service_process.shutil, "which", lambda name: "/ambient/bin/node")
    entries: list[str] = []

    service_process.append_node_dir(entries, home)

    assert [Path(entry) for entry in entries] == [node_dir, npm_dir]
    assert all(Path(entry) != Path("/ambient/bin") for entry in entries)


def test_service_process_exposes_no_venv_selection_bridge():
    assert not hasattr(service_process, "detect_venv_dir")
    assert not hasattr(service_process, "service_venv_dir")



def test_systemd_unit_does_not_persist_virtual_env(tmp_path, monkeypatch):
    from gateway import systemd_unit_render

    monkeypatch.setattr(service_process, "python_path", lambda: "/store/python/bin/python3")
    monkeypatch.setattr(service_process, "stable_working_dir", lambda: str(tmp_path))
    monkeypatch.setattr(service_process, "service_path_dirs", lambda: [])
    monkeypatch.setattr(service_process, "append_node_dir", lambda entries, hermes_root=None: None)
    monkeypatch.setattr(service_process, "build_user_local_paths", lambda home, entries: [])
    monkeypatch.setattr(service_process, "build_wsl_interop_paths", lambda entries: [])
    monkeypatch.setattr(systemd_unit_render, "get_hermes_home", lambda: tmp_path)
    monkeypatch.setattr(systemd_unit_render.service_identity, "profile_arg", lambda *a, **k: "")
    monkeypatch.setattr(systemd_unit_render, "ld_library_path_line", lambda *a, **k: "")
    monkeypatch.setattr(systemd_unit_render, "systemd_watchdog_seconds", lambda home=None: 0)
    monkeypatch.setattr(systemd_unit_render, "get_restart_drain_timeout", lambda: 0.0)
    monkeypatch.setattr(systemd_unit_render, "get_cron_drain_timeout", lambda: 0.0)

    unit = systemd_unit_render.generate_systemd_unit(system=False)

    assert "VIRTUAL_ENV" not in unit
