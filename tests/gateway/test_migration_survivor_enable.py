"""Resumed migration must enable its surviving systemd unit before convergence."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from gateway import migration


@pytest.mark.parametrize("enable_succeeds", [True, False])
def test_resumed_migration_requires_survivor_boot_enablement(monkeypatch, tmp_path, enable_succeeds):
    manifest = tmp_path / "gateway_migration.json"
    manifest.write_text("{}")
    home = tmp_path.resolve()
    plan = SimpleNamespace(
        already_multiplexed=False,
        manifest={"version": 1},
        default_home=home,
        default=SimpleNamespace(service=("systemd", False)),
        expected_served_names={"default"},
        notices=[],
    )
    calls = []
    monkeypatch.setattr(migration, "_resume_target", lambda plan: (("systemd", False), None))
    monkeypatch.setattr(migration, "_resume_findings", lambda *args: [])
    monkeypatch.setattr(migration, "_write_multiplex_flag", lambda *args: calls.append("flag"))
    monkeypatch.setattr(migration, "_remove_secondary_gateways", lambda plan: [])
    monkeypatch.setattr(migration, "_restart_default", lambda *args, **kwargs: "restarted")
    monkeypatch.setattr(migration, "_wait_for_served", lambda *args: ["default"])
    monkeypatch.setattr(migration, "_manifest_path", lambda home: manifest)

    def service(kind, system, operation, selected_home, **kwargs):
        calls.append((kind, system, operation, selected_home))
        if not enable_succeeds:
            raise RuntimeError("enable refused")

    monkeypatch.setattr(migration, "_service_op", service)
    result = migration.apply_migration_result(plan, served_wait=0)
    assert result.succeeded is enable_succeeds
    assert ("systemd", False, "enable", home) in calls
    assert manifest.exists() is not enable_succeeds
    if not enable_succeeds:
        assert "manifest retained" in " ".join(result.lines)


def test_resumed_migration_without_systemd_survivor_needs_no_enable(monkeypatch, tmp_path):
    manifest = tmp_path / "gateway_migration.json"
    manifest.write_text("{}")
    plan = SimpleNamespace(
        already_multiplexed=False, manifest={"version": 1}, default_home=tmp_path,
        default=SimpleNamespace(service=("launchd", False)), expected_served_names={"default"},
        notices=[],
    )
    monkeypatch.setattr(migration, "_resume_target", lambda plan: (("launchd", False), None))
    monkeypatch.setattr(migration, "_resume_findings", lambda *args: [])
    monkeypatch.setattr(migration, "_write_multiplex_flag", lambda *args: None)
    monkeypatch.setattr(migration, "_remove_secondary_gateways", lambda plan: [])
    monkeypatch.setattr(migration, "_restart_default", lambda *args, **kwargs: "restarted")
    monkeypatch.setattr(migration, "_wait_for_served", lambda *args: ["default"])
    monkeypatch.setattr(migration, "_manifest_path", lambda home: manifest)
    monkeypatch.setattr(migration, "_service_op",
                        lambda *args, **kwargs: pytest.fail("non-systemd must not be enabled"))
    assert migration.apply_migration_result(plan, served_wait=0).succeeded
    assert not manifest.exists()
