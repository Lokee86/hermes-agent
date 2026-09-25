"""Desired profile serving policy for the gateway."""

from __future__ import annotations

from pathlib import Path

from profiles.paths import default_hermes_home
from profiles.registry import iter_named_profile_dirs, parked_marker_path


def profile_is_standalone(home: Path) -> bool:
    """Read the existing standalone setting; config ownership remains with the CLI for now."""
    try:
        from hermes_cli.config import read_user_config_raw
        config = read_user_config_raw(Path(home)) or {}
        gateway = config.get("gateway", {})
        return bool(gateway.get("standalone", False)) if isinstance(gateway, dict) else False
    except (ImportError, OSError, TypeError, ValueError):
        return False


def profiles_to_serve(
    multiplex: bool,
    *,
    include_standalone: bool = False,
    include_parked: bool = False,
) -> list[tuple[str, Path]]:
    default = default_hermes_home()
    if not multiplex:
        return [("default", default)]
    result: list[tuple[str, Path]] = [("default", default)]
    for home in iter_named_profile_dirs():
        if not include_parked and parked_marker_path(home).exists():
            continue
        if not include_standalone and profile_is_standalone(home):
            continue
        result.append((home.name, home))
    return result
