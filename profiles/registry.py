"""Profile existence and live-directory registry."""

from __future__ import annotations

from pathlib import Path

from hermes_constants import named_profile_has_identity, named_profile_is_deleted, named_profile_is_live

from .names import PROFILE_ID_RE, normalize_profile_name
from .paths import profile_dir, profiles_root


def iter_named_profile_dirs(*, live_only: bool = True) -> list[Path]:
    root = profiles_root()
    if not root.is_dir():
        return []
    return [
        entry for entry in sorted(root.iterdir())
        if entry.is_dir() and entry.name != "default" and PROFILE_ID_RE.match(entry.name)
        and named_profile_has_identity(entry)
        and not (live_only and named_profile_is_deleted(entry))
    ]


def list_profile_names() -> list[str]:
    names = ["default"]
    try:
        names.extend(entry.name for entry in iter_named_profile_dirs())
    except OSError:
        pass
    return names


def profile_exists(name: str) -> bool:
    try:
        canon = normalize_profile_name(name)
        path = profile_dir(canon)
    except ValueError:
        return False
    return canon == "default" or named_profile_is_live(path)


def profile_is_parked(home: Path) -> bool:
    return (Path(home) / "gateway.parked").exists()


def parked_marker_path(home: Path) -> Path:
    return Path(home) / "gateway.parked"
