"""Prevent reverse CLI dependencies in the canonical auth package."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "auth"
FORBIDDEN = ("hermes_cli", "nous_cli")


def test_auth_has_no_cli_imports():
    assert (AUTH / "__init__.py").is_file()
    violations = []
    for path in sorted(AUTH.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if any(name == prefix or name.startswith(prefix + ".")
                       for prefix in FORBIDDEN):
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")
    assert not violations, "Reverse CLI dependency:\n" + "\n".join(violations)
