"""Ownership guards for the Gateway migration / CLI boundary."""
from __future__ import annotations

import ast
from pathlib import Path

import gateway.migration as migration


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_gateway_python_never_imports_its_cli_gateway_facade() -> None:
    gateway_root = Path(migration.__file__).parent
    offenders: list[tuple[str, str]] = []
    for path in gateway_root.rglob("*.py"):
        for name in _imports(path):
            if name == "hermes_cli.gateway" or name.startswith("hermes_cli.gateway."):
                offenders.append((str(path.relative_to(gateway_root)), name))
    assert offenders == []


def test_migration_does_not_import_cli_profile_lifecycle() -> None:
    path = Path(migration.__file__)
    assert "hermes_cli.profiles" not in _imports(path)


def test_migration_domain_does_not_render_terminal_output() -> None:
    path = Path(migration.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    print_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"
    ]
    assert print_calls == []
