"""Host-side adapter for plugin-runtime process isolation.

The lower plugin runtime owns loading policy and asks for two narrow host operations:
resolve the configured isolation mode and construct this profile's PluginHost. Imports stay
lazy so config initialization does not pull host-process machinery into ordinary startup.
"""

from __future__ import annotations

from typing import Any


def plugin_isolation_mode() -> str:
    from hermes_cli.plugin_isolation import isolation_mode

    return isolation_mode()


def plugin_host_factory(manager: Any) -> Any:
    from hermes_cli.plugin_host import PluginHost

    return PluginHost(manager)


def bind_plugin_runtime_host_adapter() -> None:
    from plugin_runtime.host_bindings import bind_plugin_host

    bind_plugin_host(
        plugin_isolation_mode=plugin_isolation_mode,
        plugin_host_factory=plugin_host_factory,
    )


__all__ = [
    "bind_plugin_runtime_host_adapter",
    "plugin_host_factory",
    "plugin_isolation_mode",
]
