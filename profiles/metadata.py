"""Profile metadata value helpers."""

from __future__ import annotations

import json
from pathlib import Path


def read_profile_meta(profile_dir: Path) -> dict:
    path = Path(profile_dir) / "profile.yaml"
    try:
        import yaml
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def format_profile_label(name: str, display_name: str | None) -> str:
    return display_name.strip() if display_name and display_name.strip() else name


def has_bundled_skills_opt_out(profile_dir: Path) -> bool:
    return (Path(profile_dir) / ".no-bundled-skills").exists()
