"""Architecture guards for the Phase 5.7 model-selection domain."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SELECTION_FILES = (
    ROOT / "models" / "selection.py",
    ROOT / "models" / "selection_types.py",
    ROOT / "models" / "selection_explicit.py",
    ROOT / "models" / "selection_detection.py",
)
METADATA_ROOT = ROOT / "models" / "metadata"


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


def test_selection_domain_exists_and_has_no_upward_imports():
    assert all(path.exists() for path in SELECTION_FILES)
    forbidden = (
        "agent",
        "hermes_cli",
        "gateway",
        "tui_gateway",
        "acp_adapter",
        "runtime",
    )
    violations = []
    for path in SELECTION_FILES:
        for module in sorted(_imports(path)):
            if any(module == prefix or module.startswith(prefix + ".") for prefix in forbidden):
                violations.append(f"{path.name} -> {module}")
    assert violations == []


def test_selection_uses_existing_identity_metadata_and_route_owners():
    imports = set().union(*(_imports(path) for path in SELECTION_FILES))
    assert "models.identity" in imports
    assert "models.metadata.types" in imports
    assert "providers.identity" in imports
    assert "providers.routing" in imports

    duplicate_owners = {
        "ModelRef",
        "ModelMetadata",
        "InvocationRequest",
        "InvocationRoute",
        "normalize_provider",
        "resolve_invocation_route",
    }
    definitions = set().union(*(_definitions(path) for path in SELECTION_FILES))
    assert definitions.isdisjoint(duplicate_owners)


def test_metadata_domain_does_not_depend_on_selection():
    offenders = [
        str(path.relative_to(ROOT))
        for path in METADATA_ROOT.rglob("*.py")
        if any(module.startswith("models.selection") for module in _imports(path))
    ]
    assert offenders == []


def test_selection_surface_is_pure_and_credential_free():
    imports = set().union(*(_imports(path) for path in SELECTION_FILES))
    forbidden_fragments = (
        "auth",
        "credential",
        "inventory",
        "model_switch",
        "urllib",
        "requests",
        "httpx",
        "openai",
    )
    offenders = [
        module for module in sorted(imports)
        if any(fragment in module.lower() for fragment in forbidden_fragments)
    ]
    assert offenders == []


def test_selection_public_definitions_are_owned_once():
    expected = {
        "CapabilityRequirements",
        "SelectionConstraints",
        "SelectionPolicy",
        "SelectionCandidate",
        "SelectionRequest",
        "CandidateRejection",
        "SelectionReason",
        "ModelSelection",
        "ExplicitAlias",
        "ExplicitDetectionFacts",
        "ExplicitProviderFacts",
        "ExplicitSelectionError",
        "build_selection_candidate",
        "explicit_provider_hint",
        "select_detected_model",
        "select_explicit_model",
        "select_model",
    }
    owners: dict[str, list[str]] = {name: [] for name in expected}
    for path in SELECTION_FILES:
        for name in _definitions(path):
            if name in owners:
                owners[name].append(path.name)
    assert all(len(paths) == 1 for paths in owners.values()), owners

def test_model_switch_consumes_selection_and_old_route_owners_are_deleted():
    path = ROOT / "hermes_cli" / "model_switch.py"
    imports = _imports(path)
    assert "models.selection" in imports

    obsolete = {
        "resolve_alias",
        "_resolve_alias_fallback",
        "_route_explicit_provider",
        "_route_configured_provider",
        "_route_from_model_input",
        "_aggregator_catalog_match",
        "_current_provider_match",
        "_resolve_named_custom_model_id",
    }
    assert _definitions(path).isdisjoint(obsolete)

    calls = {
        node.func.id
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "select_explicit_model" in calls
    assert "normalize_model_id" not in calls
    assert "detect_provider_for_model" not in calls
