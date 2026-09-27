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
