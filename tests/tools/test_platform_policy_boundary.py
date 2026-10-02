"""Ownership gates for runtime capability selection."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RETIRED_NAMES = {
    "_get_platform_tools", "get_platform_tools",
    "_get_plugin_toolset_keys", "get_plugin_toolset_keys",
    "_configurable_keys", "configurable_toolset_keys",
    "_platform_default_toolset", "platform_default_toolset",
    "_coerce_platform_toolsets_value", "coerce_platform_toolsets_value",
    "enabled_mcp_server_names", "_DEFAULT_OFF_TOOLSETS",
    "_RECENTLY_SHIPPED_TOOLSETS", "_warned_invalid_platform_toolsets",
    "_homeassistant_credentials_present", "_xai_credentials_present",
    "_enable_recently_shipped_toolsets", "_configurable_subset_of",
    "_default_off_toolsets", "_platform_default_keys", "_explicit_toolsets",
    "_composite_toolsets", "_enabled_plugin_toolsets", "_context_engine_active",
    "_prune_toolsets_stripped_by_disabled", "_recover_platform_native_toolsets",
    "_merge_mcp_servers", "_warn_all_invalid_platform_toolsets",
    "_TOOLSET_PLATFORM_RESTRICTIONS", "_toolset_allowed_for_platform",
}


def test_cli_presentation_does_not_own_runtime_policy():
    source = (ROOT / "hermes_cli/tools_config.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    definitions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert not definitions & RETIRED_NAMES
    assert not (ROOT / "hermes_cli/toolset_scope.py").exists()


def test_first_party_consumers_use_canonical_policy_and_scope():
    roots = ("agent", "hermes_cli", "gateway", "tui_gateway", "acp_adapter",
             "tools", "cron", "commands", "plugin_runtime", "plugins")
    paths = list(ROOT.glob("*.py"))
    for directory in roots:
        paths.extend((ROOT / directory).rglob("*.py"))
    violations = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        if "tools_config" not in source and "toolset_scope" not in source:
            continue
        tree = ast.parse(source)
        aliases = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "hermes_cli.toolset_scope":
                    violations.append((path, node.lineno, "retired scope import"))
                if node.module == "hermes_cli.tools_config":
                    forbidden = {alias.name for alias in node.names} & RETIRED_NAMES
                    if forbidden:
                        violations.append((path, node.lineno, sorted(forbidden)))
                if node.module == "hermes_cli" or (node.level and path.parent == ROOT / "hermes_cli"):
                    aliases.update(alias.asname or alias.name for alias in node.names
                                   if alias.name == "tools_config")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "hermes_cli.tools_config":
                        aliases.add(alias.asname or "hermes_cli.tools_config")
                    if alias.name == "hermes_cli.toolset_scope":
                        violations.append((path, node.lineno, "retired scope import"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in RETIRED_NAMES:
                if ast.unparse(node.value) in aliases:
                    violations.append((path, node.lineno, node.attr))
            if isinstance(node, ast.Call):
                strings = {arg.value for arg in node.args
                           if isinstance(arg, ast.Constant) and isinstance(arg.value, str)}
                if "hermes_cli.tools_config" in strings and strings & RETIRED_NAMES:
                    violations.append((path, node.lineno, "dynamic policy read through CLI"))
    assert not violations, "\n".join(str(item) for item in violations)
