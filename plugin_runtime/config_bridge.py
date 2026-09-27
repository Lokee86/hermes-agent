"""Narrow temporary bridge from plugin runtime to the legacy config owner.

Configuration ownership is intentionally deferred while #122245 is active.  Plugin runtime
must centralize the temporary dependency here instead of importing :mod:`hermes_cli.config`
throughout the new package.
"""

from __future__ import annotations

from typing import Any


def load_plugin_config() -> dict[str, Any]:
    """Load the canonical merged Hermes config for plugin-runtime policy."""
    from hermes_cli.config import load_config

    return load_config()


def save_plugin_config(config: dict[str, Any]) -> None:
    """Persist plugin-owned config changes through the canonical config writer."""
    from hermes_cli.config import save_config

    save_config(config)
