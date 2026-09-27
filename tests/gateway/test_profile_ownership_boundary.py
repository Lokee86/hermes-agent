"""Architecture guard for the Phase 1 profile-domain extraction."""
from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
    refs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            refs.add(node.module)
    return refs


def test_gateway_does_not_depend_on_cli_profiles() -> None:
    offenders: list[tuple[str, str]] = []
    gateway_root = REPO_ROOT / "gateway"
    for path in gateway_root.rglob("*.py"):
        for ref in _imports(path):
            if ref == "hermes_cli.profiles" or ref.startswith("hermes_cli.profiles."):
                offenders.append((str(path.relative_to(gateway_root)), ref))
    assert offenders == []


def test_profiles_domain_does_not_depend_on_cli() -> None:
    offenders: list[tuple[str, str]] = []
    profiles_root = REPO_ROOT / "profiles"
    for path in profiles_root.rglob("*.py"):
        for ref in _imports(path):
            if ref == "hermes_cli" or ref.startswith("hermes_cli."):
                offenders.append((str(path.relative_to(profiles_root)), ref))
    assert offenders == []
