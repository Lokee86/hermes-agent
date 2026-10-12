"""Behavioral contract of the migration domain and its CLI-facing results.

Dependency direction is enforced by the repository's architecture/import policy,
not by inspecting production source in a unit test.
"""
from pathlib import Path

import pytest

from gateway import migration


@pytest.mark.parametrize("succeeded", [True, False])
def test_apply_migration_returns_structured_verdict(monkeypatch, succeeded):
    plan = object()
    calls = []

    def apply(actual, *, served_wait):
        calls.append((actual, served_wait))
        return migration.MigrationResult(succeeded, ("migration outcome",))

    monkeypatch.setattr(migration, "apply_migration_result", apply)
    assert migration.apply_migration(plan, served_wait=3.5) is succeeded
    assert calls == [(plan, 3.5)]


@pytest.mark.parametrize("succeeded", [True, False])
def test_rollback_migration_returns_structured_verdict(monkeypatch, tmp_path: Path, succeeded):
    seen = []

    def rollback(home=None):
        seen.append(home)
        return migration.MigrationResult(succeeded, ("rollback outcome",))

    monkeypatch.setattr(migration, "rollback_migration_result", rollback)
    assert migration.rollback_migration(tmp_path) is succeeded
    assert seen == [tmp_path]


def test_restart_all_uses_canonical_migration_home_scope(monkeypatch, tmp_path: Path):
    from contextlib import contextmanager
    from hermes_cli.gateway_profile_lifecycle import host_scope_for_all_verb

    homes = []

    @contextmanager
    def scoped(home):
        homes.append(home)
        yield

    monkeypatch.setattr(migration, "_home_env", scoped)
    owner = type("Owner", (), {"home": tmp_path})()
    with host_scope_for_all_verb(owner):
        pass
    assert homes == [tmp_path]
