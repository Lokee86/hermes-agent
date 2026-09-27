"""Narrow temporary bridge from plugin runtime to the legacy config owner.

Configuration ownership is intentionally deferred while #122245 is active.  Plugin runtime
must centralize the temporary dependency here instead of importing :mod:`hermes_cli.config`
throughout the new package.
"""

from __future__ import annotations

from typing import Any, Mapping


def load_plugin_config() -> dict[str, Any]:
    """Load the canonical merged Hermes config for plugin-runtime policy."""
    from hermes_cli.config import load_config

    return load_config()


def read_enabled_plugins() -> set[str] | None:
    """Return the plugins.enabled allow-list; None means missing or malformed."""
    try:
        config = load_plugin_config()
        plugins = config.get("plugins") if isinstance(config, dict) else None
        enabled = plugins.get("enabled") if isinstance(plugins, dict) else None
        return set(enabled) if isinstance(enabled, list) else None
    except Exception:
        return None


def read_disabled_plugins() -> set[str]:
    """Return the plugins.disabled deny-list; failures and malformed values are empty."""
    try:
        config = load_plugin_config()
        plugins = config.get("plugins") if isinstance(config, dict) else None
        disabled = plugins.get("disabled", []) if isinstance(plugins, dict) else []
        return set(disabled) if isinstance(disabled, list) else set()
    except Exception:
        return set()


def read_plugin_load_timeout_seconds() -> Any:
    """Return the raw configured plugin load timeout, or None when absent/unreadable."""
    try:
        from hermes_cli.config import load_config_readonly

        config = load_config_readonly() or {}
        plugins = config.get("plugins") if isinstance(config, dict) else None
        if not isinstance(plugins, dict):
            return None
        return plugins.get("load_timeout_seconds")
    except Exception:
        return None


def read_plugin_settings(plugin_id: str) -> Mapping[str, Any]:
    """Return one plugin's effective settings/config mapping for runtime validation."""
    try:
        config = load_plugin_config()
        plugins = config.get("plugins") if isinstance(config, dict) else None
        entries = plugins.get("entries") if isinstance(plugins, dict) else None
        entry = entries.get(plugin_id) if isinstance(entries, dict) else None
        if not isinstance(entry, Mapping):
            return {}
        raw = entry.get("settings")
        if not isinstance(raw, Mapping):
            raw = entry.get("config")  # migration fallback mirroring PluginContext.get_config
        return raw if isinstance(raw, Mapping) else {}
    except Exception:
        return {}


def save_plugin_config(config: dict[str, Any]) -> None:
    """Persist plugin-owned config changes through the canonical config writer."""
    from hermes_cli.config import save_config

    save_config(config)
