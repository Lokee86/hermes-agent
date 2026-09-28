"""Guard canonical patch seams for the extracted profile domain."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MOVED_FACADE_EXPORTS = {
    "PROFILE_ROLES",
    "SETUP_ROLE",
    "current_profile_name",
    "drop_profile_role",
    "format_profile_label",
    "get_active_profile",
    "get_active_profile_name",
    "get_profile_dir",
    "list_profile_names",
    "normalize_profile_name",
    "parked_marker_path",
    "profile_exists",
    "profile_is_parked",
    "profile_is_standalone",
    "profile_matches_home",
    "profile_root_for_env_home",
    "profiles_to_serve",
    "read_profile_meta",
    "resolve_profile_env",
    "set_active_profile",
    "validate_alias_name",
    "validate_profile_name",
    "write_profile_meta",
    "_get_default_hermes_home",
    "_get_profiles_root",
}


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
    if "hermes_cli" not in source or "profiles" not in source or (
        "monkeypatch" not in source and "patch(" not in source and "patch.object" not in source
    ):
        return []
    tree = ast.parse(source, filename=str(path))
    aliases = _profile_facade_aliases(tree)
    offenders: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func

        if (
            isinstance(func, ast.Attribute)
            and func.attr == "setattr"
            and len(node.args) >= 2
        ):
            target, name = node.args[:2]
            if (
                _is_facade_target(target, aliases)
                and isinstance(name, ast.Constant)
                and name.value in MOVED_FACADE_EXPORTS
            ):
                offenders.append((node.lineno, str(name.value)))
                continue
            if (
                isinstance(target, ast.Constant)
                and isinstance(target.value, str)
                and target.value.startswith("hermes_cli.profiles.")
            ):
                patched = target.value.rsplit(".", 1)[-1]
                if patched in MOVED_FACADE_EXPORTS:
                    offenders.append((node.lineno, patched))
                    continue

        if (
            isinstance(func, ast.Attribute)
            and func.attr == "object"
            and isinstance(func.value, ast.Name)
            and func.value.id == "patch"
            and len(node.args) >= 2
            and _is_facade_target(node.args[0], aliases)
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value in MOVED_FACADE_EXPORTS
        ):
            offenders.append((node.lineno, str(node.args[1].value)))
            continue

        if (
            isinstance(func, ast.Name)
            and func.id == "patch"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.startswith("hermes_cli.profiles.")
        ):
            patched = node.args[0].value.rsplit(".", 1)[-1]
            if patched in MOVED_FACADE_EXPORTS:
                offenders.append((node.lineno, patched))

    return offenders


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "from hermes_cli import profiles\n"
            "monkeypatch.setattr(profiles, 'profile_exists', lambda _: True)\n",
            "profile_exists",
        ),
        (
            "import hermes_cli.profiles\n"
            "monkeypatch.setattr(hermes_cli.profiles, 'get_profile_dir', fake)\n",
            "get_profile_dir",
        ),
        (
            "monkeypatch.setattr('hermes_cli.profiles.get_active_profile_name', fake)\n",
            "get_active_profile_name",
        ),
        (
            "from unittest.mock import patch\n"
            "patch('hermes_cli.profiles.profiles_to_serve', return_value=[])\n",
            "profiles_to_serve",
        ),
    ],
)
def test_patch_collector_detects_facade_behavior_seams(
    tmp_path: Path,
    source: str,
    expected: str,
) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(source, encoding="utf-8")
    assert _patched_facade_names(probe) == [(2 if "\n" in source.rstrip("\n") else 1, expected)]


def test_patch_collector_allows_canonical_owner(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(
        "monkeypatch.setattr('profiles.registry.profile_exists', lambda _: True)\n",
        encoding="utf-8",
    )
    assert _patched_facade_names(probe) == []


def test_profile_tests_patch_canonical_owners_not_facade_aliases() -> None:
    offenders: list[tuple[str, int, str]] = []
    tests_root = REPO_ROOT / "tests"
    for path in tests_root.rglob("*.py"):
        if path == Path(__file__).resolve():
            continue
        for line, name in _patched_facade_names(path):
            offenders.append((str(path.relative_to(tests_root)), line, name))

    assert offenders == []
