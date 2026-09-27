"""Structural coverage for the Phase 4 plugin-runtime config bridge."""

from __future__ import annotations


def test_bridge_late_binds_canonical_config_reader(monkeypatch):
    from hermes_cli import config as config_mod
    from plugin_runtime.config_bridge import load_plugin_config

    expected = {"plugins": {"enabled": ["fixture"]}}
    monkeypatch.setattr(config_mod, "load_config", lambda: expected)

    assert load_plugin_config() is expected


def test_bridge_late_binds_canonical_config_writer(monkeypatch):
    from hermes_cli import config as config_mod
    from plugin_runtime.config_bridge import save_plugin_config

    seen = []
    monkeypatch.setattr(config_mod, "save_config", seen.append)
    payload = {"plugins": {"entries": {"fixture": {"enabled": True}}}}

    save_plugin_config(payload)

    assert seen == [payload]


def test_bridge_reads_plugin_activation_lists(monkeypatch):
    from hermes_cli import config as config_mod
    from plugin_runtime.config_bridge import read_disabled_plugins, read_enabled_plugins

    monkeypatch.setattr(
        config_mod,
        "load_config",
        lambda: {"plugins": {"enabled": ["alpha"], "disabled": ["beta"]}},
    )

    assert read_enabled_plugins() == {"alpha"}
    assert read_disabled_plugins() == {"beta"}


def test_bridge_activation_reads_preserve_fail_closed_semantics(monkeypatch):
    from hermes_cli import config as config_mod
    from plugin_runtime.config_bridge import read_disabled_plugins, read_enabled_plugins

    monkeypatch.setattr(
        config_mod,
        "load_config",
        lambda: {"plugins": {"enabled": "alpha", "disabled": None}},
    )
    assert read_enabled_plugins() is None
    assert read_disabled_plugins() == set()

    def _broken():
        raise RuntimeError("fixture")

    monkeypatch.setattr(config_mod, "load_config", _broken)
    assert read_enabled_plugins() is None
    assert read_disabled_plugins() == set()
