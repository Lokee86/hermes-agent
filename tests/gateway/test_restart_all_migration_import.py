"""Restart-all resolves its host scope through the canonical migration owner."""
from contextlib import contextmanager
from pathlib import Path

def test_restart_all_uses_canonical_migration_scope(monkeypatch, tmp_path):
    from gateway import migration
    from hermes_cli import gateway as cli_gateway

    scope_calls = []
    @contextmanager
    def scoped(home):
        scope_calls.append(("enter", home))
        yield
        scope_calls.append(("leave", home))

    owner = type("Owner", (), {"home": tmp_path})()
    monkeypatch.setattr(migration, "_home_env", scoped)
    monkeypatch.setattr(cli_gateway, "_host_multiplexer_for_all_verb", lambda: owner)
    monkeypatch.setattr(cli_gateway, "_host_multiplexer_is_ours", lambda _owner: True)
    monkeypatch.setattr(cli_gateway, "_restart_all_as_host",
                        lambda got_owner, system: scope_calls.append(("restart", got_owner, system)))

    cli_gateway._restart_all(False)
    assert scope_calls == [("enter", tmp_path), ("restart", owner, False), ("leave", tmp_path)]
