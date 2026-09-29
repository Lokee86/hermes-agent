"""Architecture guards for the Phase 5.7 model-selection domain."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "models" / "selection.py"
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
    assert OWNER.exists()
    forbidden = (
        "agent",
        "hermes_cli",
        "gateway",
        "tui_gateway",
        "acp_adapter",
        "runtime",
    )
    violations = [
        module
        for module in sorted(_imports(OWNER))
        if any(module == prefix or module.startswith(prefix + ".") for prefix in forbidden)
    ]
    assert violations == []


def test_selection_uses_existing_identity_metadata_and_route_owners():
    imports = _imports(OWNER)
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
    assert _definitions(OWNER).isdisjoint(duplicate_owners)


def test_metadata_domain_does_not_depend_on_selection():
    offenders = [
        str(path.relative_to(ROOT))
        for path in METADATA_ROOT.rglob("*.py")
        if "models.selection" in _imports(path)
    ]
    assert offenders == []


def test_selection_surface_is_pure_and_credential_free():
    imports = _imports(OWNER)
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
        "build_selection_candidate",
        "select_model",
    }
    assert expected <= _definitions(OWNER)
