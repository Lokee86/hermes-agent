"""Stable upper-host bindings consumed by the lower plugin runtime.

The plugin runtime owns lifecycle and policy. This adapter binds the small set of
host-owned services it cannot implement itself. All heavy imports stay inside
callbacks so importing config does not pull gateway, catalog, or host-process code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def plugin_isolation_mode() -> str:
    from hermes_cli.plugin_isolation import isolation_mode

    return isolation_mode()


def plugin_host_factory(manager: Any) -> Any:
    from hermes_cli.plugin_host import PluginHost

    return PluginHost(manager)


def platform_actions_factory(plugin_id: str, profile_home: str | Path) -> Any:
    from hermes_cli.platform_actions import PlatformActions

    return PlatformActions(plugin_id, profile_home=profile_home)


def installed_plugin_removal(name: str, plugin_dir: str | Path | None) -> Any:
    from hermes_cli.plugins_cmd_catalog import installed_plugin_removal as _lookup

    return _lookup(name, plugin_dir)


def bind_plugin_runtime_host_adapter() -> None:
    from plugin_runtime.host_bindings import bind_plugin_host

    bind_plugin_host(
        plugin_isolation_mode=plugin_isolation_mode,
        plugin_host_factory=plugin_host_factory,
        platform_actions_factory=platform_actions_factory,
        installed_plugin_removal=installed_plugin_removal,
    )


__all__ = [
    "bind_plugin_runtime_host_adapter",
    "installed_plugin_removal",
    "platform_actions_factory",
    "plugin_host_factory",
    "plugin_isolation_mode",
]
