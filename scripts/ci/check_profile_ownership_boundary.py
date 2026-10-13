#!/usr/bin/env python3
"""Enforce canonical profile-domain ownership after the CLI extraction."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

MOVED_PROFILE_EXPORTS = frozenset("""
PROFILE_ROLES SETUP_ROLE current_profile_name drop_profile_role format_profile_label
get_active_profile get_active_profile_name get_profile_dir list_profile_names normalize_profile_name
parked_marker_path profile_exists profile_is_parked profile_is_standalone profile_matches_home
profile_root_for_env_home profiles_to_serve read_profile_meta resolve_profile_env set_active_profile
validate_alias_name validate_profile_name write_profile_meta _get_default_hermes_home _get_profiles_root
""".split())

_RUNTIME_ROOTS = ("agent", "gateway", "tui_gateway", "acp_adapter", "cron", "tools", "plugins")


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _parse(path: Path, source: str | None = None) -> ast.AST:
    return ast.parse(_read_source(path) if source is None else source, filename=str(path))


def _imports(path: Path, source: str | None = None) -> set[str]:
    refs: set[str] = set()
    for node in ast.walk(_parse(path, source)):
        if isinstance(node, ast.Import):
            refs.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            refs.add(node.module)
            refs.update(f"{node.module}.{alias.name}" for alias in node.names)
    return refs


def _is_cli_profiles_ref(ref: str) -> bool:
    return ref == "hermes_cli.profiles" or ref.startswith("hermes_cli.profiles.")


def _import_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                bindings[local] = alias.name if alias.asname else local
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    bindings[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return bindings


def _canonical_name(node: ast.AST, bindings: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return bindings.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _canonical_name(node.value, bindings)
        return f"{parent}.{node.attr}" if parent else None
    return None


def _moved_profile_facade_refs(path: Path) -> list[tuple[int, str]]:
    source = _read_source(path)
    if "hermes_cli" not in source or "profiles" not in source:
        return []
    tree = _parse(path, source)
    bindings = _import_bindings(tree)
    offenders: set[tuple[int, str]] = set()
    prefix = "hermes_cli.profiles."
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "hermes_cli.profiles":
            for alias in node.names:
                if alias.name in MOVED_PROFILE_EXPORTS:
                    offenders.add((node.lineno, alias.name))
            continue
        if isinstance(node, ast.Attribute):
            canonical = _canonical_name(node, bindings)
            if canonical and canonical.startswith(prefix):
                name = canonical[len(prefix):].split(".", 1)[0]
                if name in MOVED_PROFILE_EXPORTS:
                    offenders.add((node.lineno, name))
        if isinstance(node, ast.Call):
            if (
                len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "hermes_cli.profiles"
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in MOVED_PROFILE_EXPORTS
            ):
                offenders.add((node.lineno, str(node.args[1].value)))
            if (
                _canonical_name(node.func, bindings) == "getattr"
                and len(node.args) >= 2
                and _canonical_name(node.args[0], bindings) == "hermes_cli.profiles"
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in MOVED_PROFILE_EXPORTS
            ):
                offenders.add((node.lineno, str(node.args[1].value)))
    return sorted(offenders)


def _profile_facade_aliases(tree: ast.AST) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update(
                alias.asname or "hermes_cli.profiles"
                for alias in node.names
                if alias.name == "hermes_cli.profiles"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "hermes_cli":
            aliases.update(
                alias.asname or "profiles"
                for alias in node.names
                if alias.name == "profiles"
            )
    return aliases


def _is_facade_target(node: ast.AST, aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in aliases
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "profiles"
        and isinstance(node.value, ast.Name)
        and node.value.id == "hermes_cli"
        and "hermes_cli.profiles" in aliases
    )


def _patched_facade_names(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    if "hermes_cli" not in source or "profiles" not in source:
        return []
    tree = ast.parse(source, filename=str(path))
    aliases = _profile_facade_aliases(tree)
    bindings = _import_bindings(tree)
    offenders: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "setattr" and len(node.args) >= 2:
            target, name = node.args[:2]
            if (
                _is_facade_target(target, aliases)
                and isinstance(name, ast.Constant)
                and name.value in MOVED_PROFILE_EXPORTS
            ):
                offenders.add((node.lineno, str(name.value)))
                continue
            if (
                isinstance(target, ast.Constant)
                and isinstance(target.value, str)
                and target.value.startswith("hermes_cli.profiles.")
            ):
                patched = target.value.rsplit(".", 1)[-1]
                if patched in MOVED_PROFILE_EXPORTS:
                    offenders.add((node.lineno, patched))
                    continue
        if (
            _canonical_name(func, bindings) == "unittest.mock.patch.object"
            and len(node.args) >= 2
            and _is_facade_target(node.args[0], aliases)
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value in MOVED_PROFILE_EXPORTS
        ):
            offenders.add((node.lineno, str(node.args[1].value)))
            continue
        if (
            _canonical_name(func, bindings) == "unittest.mock.patch"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.startswith("hermes_cli.profiles.")
        ):
            patched = node.args[0].value.rsplit(".", 1)[-1]
            if patched in MOVED_PROFILE_EXPORTS:
                offenders.add((node.lineno, patched))
    return sorted(offenders)


def find_profile_ownership_violations(root: Path) -> list[str]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"repository root is not a directory: {root}")
    violations: list[str] = []

    gateway_root = root / "gateway"
    if gateway_root.is_dir():
        for path in gateway_root.rglob("*.py"):
            source = _read_source(path)
            if "hermes_cli" not in source:
                continue
            for ref in _imports(path, source):
                if _is_cli_profiles_ref(ref):
                    violations.append(
                        f"{path.relative_to(root).as_posix()}: imports retired CLI profile owner {ref}"
                    )

    profiles_root = root / "profiles"
    if profiles_root.is_dir():
        for path in profiles_root.rglob("*.py"):
            source = _read_source(path)
            if "hermes_cli" not in source:
                continue
            for ref in _imports(path, source):
                if ref == "hermes_cli" or ref.startswith("hermes_cli."):
                    violations.append(
                        f"{path.relative_to(root).as_posix()}: profile domain depends on CLI {ref}"
                    )

    for root_name in _RUNTIME_ROOTS:
        runtime_root = root / root_name
        if not runtime_root.is_dir():
            continue
        for path in runtime_root.rglob("*.py"):
            for line, name in _moved_profile_facade_refs(path):
                violations.append(
                    f"{path.relative_to(root).as_posix()}:{line}: moved profile symbol "
                    f"{name} is read through hermes_cli.profiles"
                )

    for path in root.glob("*.py"):
        for line, name in _moved_profile_facade_refs(path):
            violations.append(
                f"{path.relative_to(root).as_posix()}:{line}: moved profile symbol "
                f"{name} is read through hermes_cli.profiles"
            )

    tests_root = root / "tests"
    if tests_root.is_dir():
        for path in tests_root.rglob("*.py"):
            for line, name in _patched_facade_names(path):
                violations.append(
                    f"{path.relative_to(root).as_posix()}:{line}: test patches moved profile "
                    f"symbol {name} through hermes_cli.profiles"
                )

    return sorted(set(violations))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enforce canonical profile-domain import and patch ownership."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        violations = find_profile_ownership_violations(args.root)
    except (ValueError, SyntaxError) as exc:
        parser.error(str(exc))
    if not violations:
        print("Profile ownership boundary is clean.")
        return 0
    print("::error::profile ownership boundary violations detected")
    for violation in violations:
        print(f"  {violation}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
