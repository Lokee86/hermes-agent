"""Profile home and directory resolution."""

from __future__ import annotations

from pathlib import Path

from hermes_constants import get_default_hermes_root, get_hermes_home

from .names import PROFILE_ID_RE, invalid_profile_name_error, normalize_profile_name


def default_hermes_home() -> Path:
    return get_default_hermes_root()


def profiles_root() -> Path:
    return default_hermes_home() / "profiles"


def active_profile_path() -> Path:
    return default_hermes_home() / "active_profile"


def profile_dir(name: str) -> Path:
    canon = normalize_profile_name(name)
    if canon == "default":
        return default_hermes_home()
    if not PROFILE_ID_RE.match(canon):
        raise invalid_profile_name_error(canon)
    return profiles_root() / canon


def profile_matches_home(name: str, home: Path | None = None) -> bool:
    try:
        target = profile_dir(name)
        if home is None:
            home = get_hermes_home()
        return target.expanduser().resolve(strict=False) == Path(home).expanduser().resolve(strict=False)
    except Exception:
        return False


def profile_root_for_env_home(env_home: str, default_root: Path) -> Path:
    candidate = Path(env_home).expanduser().resolve(strict=False)
    default_root = Path(default_root).expanduser().resolve(strict=False)
    if candidate == default_root:
        return default_root
    try:
        candidate.relative_to(default_root / "profiles")
    except ValueError:
        return default_root
    return candidate


def resolve_profile_env(profile_name: str) -> str:
    return str(profile_dir(profile_name))
