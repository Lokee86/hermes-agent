"""Stdio and resource-limit primitives accept policy rather than loading upper layers."""
from tests.runtime.ownership_probe import probe_without_upper_layers


def test_resource_limit_compatibility_delegates_loaded_policy(monkeypatch):
    from hermes_cli import resource_limits as compat
    from runtime import resource_limits as owner

    policy = {"runtime": {"nofile_soft_limit": 1234}}
    seen = []
    monkeypatch.setattr(owner, "configured_nofile_soft_limit",
                        lambda config: seen.append(config) or 1234)
    assert compat.configured_nofile_soft_limit(policy) == 1234
    assert seen == [policy]


def test_runtime_stdio_and_resource_policy_need_no_upper_layers():
    probe_without_upper_layers("""
        import sys
        from runtime import resource_limits, stdio

        assert stdio.is_windows() == (sys.platform == 'win32')
        stdio.configure_windows_stdio()
        assert resource_limits.configured_nofile_soft_limit(
            {'runtime': {'nofile_soft_limit': 1234}}) == 1234
        assert resource_limits.configured_nofile_soft_limit(
            {'runtime': {'nofile_soft_limit': False}}) is None
        assert resource_limits.apply_nofile_soft_limit(
            {'runtime': {'nofile_soft_limit': False}}) is False
    """)
