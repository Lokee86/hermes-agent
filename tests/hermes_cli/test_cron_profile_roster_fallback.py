"""Cron dashboard fallback uses an actual profile-discovery dependency."""


def test_cron_roster_forced_fallback(monkeypatch):
    from hermes_cli import profiles as profiles_mod
    from hermes_cli import web_server_cron as cron
    from hermes_cli import web_server_profiles as profile_helpers

    def fail_discovery(**_kwargs):
        raise RuntimeError("forced discovery failure")

    observed = {}

    def fallback(module):
        observed["profiles_module"] = module
        return [{"name": "default"}, {"name": "secondary"}]

    monkeypatch.setattr(cron.profile_serving, "profiles_to_serve", fail_discovery)
    monkeypatch.setattr(profile_helpers, "_fallback_profile_dicts", fallback)

    assert cron._cron_profile_dicts() == [
        {"name": "default"}, {"name": "secondary"}]
    assert observed["profiles_module"] is profiles_mod
