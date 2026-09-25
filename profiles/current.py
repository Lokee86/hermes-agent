"""Active profile identity resolution."""

from __future__ import annotations

from pathlib import Path

from hermes_constants import get_hermes_home, get_hermes_home_override, set_hermes_home_override

from .names import normalize_profile_name
from .paths import active_profile_path, default_hermes_home


def get_active_profile(root: Path | None = None) -> str:
    path = (root or default_hermes_home()) / "active_profile"
    try:
        value = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return "default"
    return normalize_profile_name(value) if value else "default"


def set_active_profile(name: str) -> None:
    active_profile_path().write_text(normalize_profile_name(name) + "\n", encoding="utf-8")


def get_active_profile_name() -> str:
    override = get_hermes_home_override()
    if override is not None:
        return get_active_profile(Path(override))
    home = get_hermes_home()
    return "default" if Path(home).resolve() == default_hermes_home().resolve() else get_active_profile()


def current_profile_name(default: str | None = None) -> str | None:
    try:
        return get_active_profile_name()
    except (OSError, ValueError):
        return default
