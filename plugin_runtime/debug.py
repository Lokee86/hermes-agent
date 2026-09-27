"""Shared plugin-runtime debug state."""

from __future__ import annotations

from utils import env_var_enabled

_PLUGINS_DEBUG = env_var_enabled("HERMES_PLUGINS_DEBUG")


def plugin_debug_enabled() -> bool:
    """Return the process-local plugin debug flag."""
    return _PLUGINS_DEBUG


def refresh_plugin_debug() -> bool:
    """Refresh the plugin debug flag from the environment and return it."""
    global _PLUGINS_DEBUG
    _PLUGINS_DEBUG = env_var_enabled("HERMES_PLUGINS_DEBUG")
    return _PLUGINS_DEBUG
