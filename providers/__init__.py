"""Canonical provider domain API.

Provider identity is defined by :class:`ProviderProfile`. The registry is the
single authority for effective provider declarations; discovery mechanics are
internal to the package.

Provider profiles may be supplied by bundled plugins, the currently bound
HERMES_HOME, pip entry points, or the documented legacy single-file plugin
boundary. Consumers should use this package API rather than registry state.
"""

from __future__ import annotations

from providers.base import ProviderProfile
from providers.registry import (
    get_provider_profile,
    list_providers,
    provider_source,
    register_provider,
    routed_model_rejects_vision_tool_messages,
)
from providers.identity import (
    ResolvedProvider,
    custom_provider_aliases,
    custom_provider_slug,
    get_provider_label,
    is_aggregator,
    is_routing_aggregator,
    normalize_provider,
)

# Load the internal discovery module so registry calls and package submodule
# identity are stable; discovery itself remains lazy and performs no scan here.
from providers import discovery as _discovery  # noqa: E402,F401


__all__ = [
    "ProviderProfile",
    "ResolvedProvider",
    "register_provider",
    "get_provider_profile",
    "list_providers",
    "provider_source",
    "routed_model_rejects_vision_tool_messages",
    "normalize_provider",
    "get_provider_label",
    "is_aggregator",
    "is_routing_aggregator",
    "custom_provider_slug",
    "custom_provider_aliases",
]


# ---- BEGIN PLUGIN-COMPAT (revert-scheduled; see COMPAT_MANIFEST.md) ----
# Names external plugins imported from this module before the Sep 2026 decomposition.
# Internal code MUST NOT use these (scripts/check_compat_pointers.py fails CI if it does).
# The whole block is removed by reverting the commit that added it.

_PLUGIN_COMPAT_LAZY = {
    "OMIT_TEMPERATURE": ("providers.base", "OMIT_TEMPERATURE"),
}


def __getattr__(name):  # PEP 562 - lazy so no import cycles
    target = _PLUGIN_COMPAT_LAZY.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    from hermes_cli.plugin_compat import warn_once

    warn_once(__name__, name, *target)
    return getattr(importlib.import_module(target[0]), target[1])
# ---- END PLUGIN-COMPAT ----
