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


def test_runtime_has_no_retired_pool_or_grant_imports():
    retired = {
        "agent.credential_sources", "agent.anthropic_credentials",
        "hermes_cli.auth_qwen",
        "agent.credential_pool", "agent.credential_pool_admin",
        "agent.credential_pool_model_cooldowns", "agent.credential_pool_plugin",
        "hermes_cli.auth_oauth_grants",
    }
    paths = list(ROOT.glob("*.py"))
    for directory in ("auth", "agent", "gateway", "hermes_cli", "tui_gateway",
                      "tools", "plugins", "cron", "acp_adapter"):
        paths.extend((ROOT / directory).rglob("*.py"))
    violations = []
    for path in sorted(paths):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
                if node.module in {"agent", "hermes_cli"}:
                    names.extend(node.module + "." + alias.name for alias in node.names)
            for name in names:
                if name in retired:
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")
    assert not violations, "Retired authentication dependency:\n" + "\n".join(violations)
