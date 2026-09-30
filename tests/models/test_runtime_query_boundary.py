"""Architecture guards for the Phase 5.8.2 runtime-query domains."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOWER_QUERY_FILES = (
    ROOT / "models" / "catalog_static.py",
    ROOT / "models" / "catalog_local.py",
    ROOT / "models" / "catalog_github.py",
    ROOT / "models" / "codex_catalog.py",
    ROOT / "models" / "models_dev_cache.py",
    ROOT / "models" / "metadata" / "fast_mode.py",
    ROOT / "models" / "metadata" / "github.py",
    ROOT / "models" / "metadata" / "local.py",
    ROOT / "providers" / "opencode.py",
    ROOT / "providers" / "github.py",
    ROOT / "providers" / "configured.py",
    ROOT / "providers" / "route_identity.py",
    ROOT / "providers" / "routing.py",
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
        "copilot_default_headers",
    }
    assert definitions.isdisjoint(moved)


def test_primary_agent_runtime_has_no_cli_model_semantic_dependencies():
    paths = (
        ROOT / "agent" / "agent_init.py",
        ROOT / "agent" / "agent_runtime_helpers.py",
        ROOT / "agent" / "client_lifecycle.py",
        ROOT / "agent" / "chat_completion_helpers.py",
        ROOT / "agent" / "fast_mode.py",
        ROOT / "agent" / "reasoning_params.py",
        ROOT / "agent" / "model_metadata.py",
        ROOT / "agent" / "models_dev.py",
        ROOT / "agent" / "opencode_affinity.py",
        *(ROOT / "agent" / "transports").glob("*.py"),
    )
    forbidden = (
        "hermes_cli.models",
        "hermes_cli.model_switch",
        "hermes_cli.model_selection",
        "hermes_cli.models_validate",
        "hermes_cli.model_catalog",
    )
    offenders = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for dependency in forbidden:
            if dependency in source:
                offenders.append(f"{path.relative_to(ROOT)} -> {dependency}")
    assert offenders == []


def test_agent_warning_and_copilot_headers_have_final_owners():
    switch_definitions = _definitions(ROOT / "hermes_cli" / "model_switch.py")
    assert "is_nous_hermes_non_agentic" not in switch_definitions
    assert "_check_hermes_model_warning" not in switch_definitions
    assert "copilot_default_headers" not in _definitions(ROOT / "hermes_cli" / "models.py")
    assert "fetch_github_model_catalog" not in _definitions(ROOT / "hermes_cli" / "models.py")
    assert "get_copilot_model_context" not in _definitions(ROOT / "hermes_cli" / "models.py")
    assert "copilot_request_headers" not in _definitions(ROOT / "hermes_cli" / "copilot_auth.py")
    assert "nous_hermes_non_agentic_warning" in _definitions(ROOT / "agent" / "model_warnings.py")
    assert "copilot_request_headers" in _definitions(ROOT / "providers" / "github.py")
    assert "fetch_github_model_catalog" in _definitions(ROOT / "models" / "catalog_github.py")
    assert "github_model_context_length" in _definitions(ROOT / "models" / "metadata" / "github.py")
    local_defs = _definitions(ROOT / "models" / "metadata" / "local.py")
    assert {"lmstudio_model_reasoning_options", "ollama_model_supports_thinking"} <= local_defs
    old_local_defs = _definitions(ROOT / "hermes_cli" / "models_local.py")
    assert {"lmstudio_model_reasoning_options", "ollama_model_supports_thinking"}.isdisjoint(old_local_defs)


def test_route_identity_and_runtime_kind_have_lower_owners():
    assert "normalize_route_base_url" not in _definitions(ROOT / "hermes_cli" / "route_identity.py")
    assert "is_actual_route" not in _definitions(ROOT / "hermes_cli" / "providers.py")
    assert "_is_external_process_provider" not in _definitions(
        ROOT / "hermes_cli" / "runtime_provider_backends.py"
    )
    assert "normalize_route_base_url" in _definitions(ROOT / "providers" / "route_identity.py")
    assert "is_actual_route" in _definitions(ROOT / "providers" / "route_identity.py")
    assert "is_external_process_provider" in _definitions(ROOT / "providers" / "routing.py")


def test_static_catalogue_old_owner_is_deleted():
    assert not (ROOT / "hermes_cli" / "models_catalog_static.py").exists()


def test_auxiliary_model_resolution_is_not_cli_owned():
    runtime = ROOT / "agent" / "auxiliary_model_resolution.py"
    assert runtime.exists()
    assert not (ROOT / "hermes_cli" / "model_selection_auxiliary.py").exists()
    assert "hermes_cli.model_selection_auxiliary" not in (
        ROOT / "agent" / "auxiliary_client.py"
    ).read_text(encoding="utf-8")


def test_configured_provider_semantics_have_final_owner():
    lower_defs = _definitions(ROOT / "providers" / "configured.py")
    assert {
        "match_configured_provider",
        "resolves_to_custom_provider",
        "expand_direct_api_alias",
    } <= lower_defs

    assert "_resolves_to_custom" not in _definitions(
        ROOT / "hermes_cli" / "runtime_provider.py"
    )
    old_custom_defs = _definitions(ROOT / "hermes_cli" / "runtime_provider_custom.py")
    assert {
        "_shadowed_by_builtin",
        "_match_new_style_provider",
        "_match_legacy_custom_provider",
        "expand_direct_api_alias",
    }.isdisjoint(old_custom_defs)

    paths = (
        ROOT / "agent" / "auxiliary_client.py",
        ROOT / "agent" / "auxiliary_health.py",
        ROOT / "agent" / "chat_completion_helpers.py",
        ROOT / "agent" / "client_lifecycle.py",
        ROOT / "agent" / "opencode_affinity.py",
    )
    forbidden = (
        "runtime_provider import _get_named_custom_provider",
        "runtime_provider_custom import _get_named_custom_provider",
        "runtime_provider_custom import expand_direct_api_alias",
        "_resolves_to_custom",
    )
    offenders = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for dependency in forbidden:
            if dependency in source:
                offenders.append(f"{path.relative_to(ROOT)} -> {dependency}")
    assert offenders == []


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


def test_auxiliary_fallback_routing_has_one_canonical_route_owner():
    fallback = ROOT / "agent" / "fallback_routing.py"
    assert fallback.exists()
    fallback_source = fallback.read_text(encoding="utf-8")
    assert "resolve_invocation_route" in fallback_source
    assert "hermes_cli.runtime_provider" not in fallback_source

    auxiliary = ROOT / "agent" / "auxiliary_client.py"
    tree = _tree(auxiliary)
    complete = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_complete_fallback_destination"
    )
    complete_source = ast.get_source_segment(auxiliary.read_text(encoding="utf-8"), complete) or ""
    assert "resolve_fallback_invocation_route" in complete_source
    assert "hermes_cli.runtime_provider" not in complete_source

    helpers = ROOT / "agent" / "chat_completion_helpers.py"
    helper_defs = _definitions(helpers)
    assert {
        "_fallback_invocation_route",
        "_fallback_api_mode_hint",
        "_fallback_api_mode_resolved",
        "_is_anthropic_wire_url",
    }.isdisjoint(helper_defs)
    assert "agent.fallback_routing" in _imports(helpers)

    health_source = (ROOT / "agent" / "auxiliary_health.py").read_text(encoding="utf-8")
    assert "normalize_provider" in health_source
    assert "_normalize_chain_label" not in health_source