"""Pure profile naming and validation primitives."""

from __future__ import annotations

import re

from hermes_constants import PROFILE_ID_RE

PROFILE_ID_PATTERN = PROFILE_ID_RE
RESERVED_NAMES = frozenset({"hermes", "default", "test", "tmp", "root", "sudo"})
HERMES_SUBCOMMANDS = frozenset({
    "chat", "model", "gateway", "setup", "whatsapp", "login", "logout", "status", "cron",
    "doctor", "dump", "config", "pairing", "skills", "tools", "mcp", "sessions", "insights",
    "version", "update", "uninstall", "profile", "plugins", "honcho", "acp",
})
PROFILE_NAME_RULE = (
    "Use lowercase letters, numbers, '-' or '_', starting with a letter or number, up to 64 characters"
)


def normalize_profile_name(name: str) -> str:
    if not isinstance(name, str):
        name = str(name)
    stripped = name.strip()
    if not stripped:
        raise ValueError("profile name cannot be empty")
    if stripped.casefold() == "default":
        return "default"
    return stripped.lower()


def _suggest_profile_name(name: str) -> str:
    candidate = re.sub(r"[^a-z0-9_-]+", "-", name.strip().lower()).strip("-_")[:64]
    return candidate if PROFILE_ID_RE.match(candidate) else "my-work"


def invalid_profile_name_error(name: str) -> ValueError:
    return ValueError(
        f"{name!r} is not a valid profile name. {PROFILE_NAME_RULE} (for example: "
        f"{_suggest_profile_name(name)}). Then run `hermes profile create {_suggest_profile_name(name)}`."
    )


def validate_profile_name(name: str) -> None:
    if name == "default":
        return
    if not PROFILE_ID_RE.match(name):
        raise invalid_profile_name_error(name)
    if name in RESERVED_NAMES:
        raise ValueError(f"Profile name {name!r} is reserved — pick a different name.")


def validate_alias_name(name: str) -> None:
    if not PROFILE_ID_RE.match(name):
        raise ValueError(f"Invalid alias name {name!r}. {PROFILE_NAME_RULE}.")


def canonical_profile_name(name: str) -> str:
    canon = normalize_profile_name(name)
    validate_profile_name(canon)
    return canon
