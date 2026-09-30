"""Architecture guards for the Phase 5.8.2 runtime-query domains."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOWER_QUERY_FILES = (
    ROOT / "models" / "catalog_static.py",
    ROOT / "models" / "catalog_local.py",
    ROOT / "models" / "codex_catalog.py",
    ROOT / "models" / "models_dev_cache.py",
    ROOT / "models" / "metadata" / "fast_mode.py",
    ROOT / "models" / "metadata" / "github.py",
    ROOT / "providers" / "opencode.py",
)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _definitions(path: Path) -> set[str]:
    return {
        node.name
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def test_runtime_query_domains_exist_and_do_not_import_upward():
    assert all(path.exists() for path in LOWER_QUERY_FILES)
    forbidden = (
        "agent",
        "hermes_cli",
        "gateway",
        "tui_gateway",
        "acp_adapter",
        "plugins",
    )
    violations = []
    for path in LOWER_QUERY_FILES:
        for module in sorted(_imports(path)):
            if any(module == prefix or module.startswith(prefix + ".") for prefix in forbidden):
                violations.append(f"{path.relative_to(ROOT)} -> {module}")
    assert violations == []


def test_cli_models_no_longer_owns_moved_runtime_queries():
    definitions = _definitions(ROOT / "hermes_cli" / "models.py")
    moved = {
        "opencode_provider_family",
        "normalize_opencode_model_id",
        "normalize_opencode_base_url",
        "clamp_reasoning_effort_to_supported",
        "clamp_github_reasoning_effort",
        "model_supports_fast_mode",
        "resolve_fast_mode_overrides",
        "github_model_reasoning_efforts",
    }
    assert definitions.isdisjoint(moved)


def test_static_catalogue_old_owner_is_deleted():
    assert not (ROOT / "hermes_cli" / "models_catalog_static.py").exists()


def test_models_dev_persistence_is_lower_owned():
    definitions = _definitions(ROOT / "agent" / "models_dev.py")
    obsolete = {
        "_get_cache_path",
        "_get_etag_path",
        "_load_disk_cache",
        "_load_etag",
        "_save_disk_cache",
        "_save_etag",
        "_clear_etag",
        "_quarantine_corrupt_cache",
    }
    assert definitions.isdisjoint(obsolete)


def test_provider_grouping_is_application_owned():
    presentation = ROOT / "hermes_cli" / "provider_groups.py"
    assert presentation.exists()
    assert {"PROVIDER_GROUPS", "group_providers", "provider_group_for_slug"} <= (
        _definitions(presentation)
        | {
            target.id
            for node in _tree(presentation).body
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if isinstance(target, ast.Name)
        }
    )
    static_source = (ROOT / "models" / "catalog_static.py").read_text(encoding="utf-8")
    assert "PROVIDER_GROUPS" not in static_source
    assert "group_providers" not in static_source


def test_production_code_has_no_old_static_catalogue_imports():
    offenders = []
    for root_name in ("agent", "gateway", "tui_gateway", "acp_adapter", "hermes_cli", "plugins"):
        for path in (ROOT / root_name).rglob("*.py"):
            if "hermes_cli.models_catalog_static" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
