"""Ownership policy for gateway service definitions.

Service names can collide across Hermes homes, especially named profiles under
different roots. A definition that already pins HERMES_HOME may only be
rewritten by that home. The force-unit-path install flag is the explicit
cross-home repoint.
"""
from __future__ import annotations

import os
import plistlib
from pathlib import Path
from xml.parsers.expat import ExpatError

from gateway import service_identity, service_process, systemd_identity
from hermes_constants import get_hermes_home


def pinned_home(definition_path: Path) -> str | None:
    """Return the HERMES_HOME pinned by a systemd unit or launchd plist."""
    if definition_path.suffix == ".plist":
        try:
            data = plistlib.loads(definition_path.read_bytes())
        except (
            OSError,
            ValueError,
            TypeError,
            ExpatError,
            plistlib.InvalidFileException,
        ):
            return None
        env = data.get("EnvironmentVariables") if isinstance(data, dict) else None
        value = env.get("HERMES_HOME") if isinstance(env, dict) else None
        return (str(value).strip() or None) if value is not None else None
    return service_identity.hermes_home_pinned_by_unit(definition_path)


def _resolve(raw: str | Path) -> Path | None:
    try:
        return Path(raw).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def systemd_service_home_for_unit(
    unit_path: Path,
    system: bool,
    run_as_user: str | None = None,
) -> Path:
    """Return the home this caller intends to pin into unit_path."""
    if system and run_as_user:
        try:
            home_dir = systemd_identity.system_service_identity(run_as_user)[2]
        except ValueError:
            return get_hermes_home()
        return Path(service_process.hermes_home_for_target_user(home_dir))

    if not system:
        return get_hermes_home()

    if not os.environ.get("HERMES_HOME", "").strip():
        pinned = pinned_home(unit_path) if unit_path.exists() else None
        return Path(pinned).expanduser() if pinned else get_hermes_home()

    user = systemd_identity.read_unit_user(unit_path)
    if not user:
        return get_hermes_home()
    try:
        home_dir = systemd_identity.system_service_identity(user)[2]
    except ValueError:
        return get_hermes_home()
    return Path(service_process.hermes_home_for_target_user(home_dir))


def definition_belongs_to_home(
    definition_path: Path,
    home: Path,
    action: str,
) -> bool:
    """Return False, with guidance, when a definition pins another home."""
    if not definition_path.exists():
        return True
    raw = pinned_home(definition_path)
    if raw is None or _resolve(raw) == _resolve(home):
        return True
    print(
        f"✗ Refusing to {action} {definition_path}: it runs HERMES_HOME={raw}, "
        f"but this process has HERMES_HOME={home}."
    )
    print(
        "  That file is another install's gateway. Use that install, or pass "
        "--force-unit-path to hermes gateway install if you really mean to "
        "repoint it at this home."
    )
    return False


def systemd_unit_belongs_to_caller(
    unit_path: Path,
    system: bool,
    action: str,
    run_as_user: str | None = None,
) -> bool:
    """Apply the ownership rule to an existing systemd unit."""
    return definition_belongs_to_home(
        unit_path,
        systemd_service_home_for_unit(unit_path, system, run_as_user),
        action,
    )
