"""A guest kept for connectors only never serves inference through the credential pool.

A guest that carried inference in a build with the free-tier launch gate leaves a ``device_code``
row in ``credential_pool.nous``. In a process without the gate (plain CLI, gateway) the pool must
drop that row instead of handing its welcome-host token to the runtime.
"""

from auth.providers import nous_guest as anon_auth
from tests.hermes_cli.anon_portal import install_portal


def test_guest_pool_row_is_dropped_when_the_free_tier_is_off(monkeypatch, tmp_path):
    from auth.credential_pool import load_pool
    from auth.providers.nous import resolve_nous_runtime_credentials

    from hermes_cli.config_credentials import credential_pool_environment

    install_portal(monkeypatch, tmp_path)
    environment = credential_pool_environment()
    assert anon_auth.is_guest_state(
        anon_auth.ensure_portal_identity(explicit=True, environment=environment)
    )
    resolve_nous_runtime_credentials(environment=environment)  # the guest now carries an inference token
    assert any(e.source == "device_code" for e in load_pool("nous", environment=environment).entries())

    monkeypatch.delenv("HERMES_GUEST_ONBOARDING")
    state = anon_auth.current_nous_state()
    assert anon_auth.is_guest_state(state)
    assert anon_auth.guest_without_free_tier(state, environment=environment)

    assert not any(e.source == "device_code" for e in load_pool("nous", environment=environment).entries())
    assert anon_auth.has_guest()
