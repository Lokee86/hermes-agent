"""Process identity works without CLI/Gateway imports; frozen exports retain identity."""
from tests.runtime.ownership_probe import probe_without_upper_layers


def test_frozen_process_identity_exports_are_owned_by_runtime():
    from hermes_cli import process_identity as compat
    from runtime import process_identity as owner

    for name in ("REAPABLE_PURPOSES", "ledger_entries", "spawner_is_dead"):
        assert getattr(compat, name) is getattr(owner, name)
    assert not hasattr(compat, "_process_create_time")


def test_spawn_identity_and_liveness_work_without_upper_layers():
    probe_without_upper_layers("""
        import os
        from pathlib import Path
        from runtime import process_identity as identity

        raw = identity.build_spawn_tag('mcp-helper', project_root=Path.cwd())
        tag = identity.parse_spawn_tag(raw)
        assert tag.purpose == 'mcp-helper'
        assert tag.spawner_pid == os.getpid()
        assert identity.pid_exists_stdlib(os.getpid())
        assert identity.start_time_fingerprints_match(1000, 1100)
        assert not identity.start_time_fingerprints_match(1000, 1500)
    """)
