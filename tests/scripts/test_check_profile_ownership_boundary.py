"""Behavioral tests for the profile ownership architecture gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "check_profile_ownership_boundary.py"
SPEC = importlib.util.spec_from_file_location("profile_ownership_gate", SCRIPT)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_clean_canonical_profile_ownership_passes(tmp_path):
    _write(tmp_path, "gateway/sample.py", "from profiles.registry import profile_exists\n")
    _write(tmp_path, "profiles/registry.py", "def profile_exists(name): return bool(name)\n")
    _write(
        tmp_path,
        "tests/gateway/test_sample.py",
        "from unittest.mock import patch\n"
        "patch('profiles.registry.profile_exists', return_value=True)\n",
    )
    assert gate.find_profile_ownership_violations(tmp_path) == []


def test_gateway_cli_profile_import_is_rejected(tmp_path):
    _write(tmp_path, "gateway/sample.py", "from hermes_cli.profiles import get_profile_dir\n")
    violations = gate.find_profile_ownership_violations(tmp_path)
    assert any("retired CLI profile owner" in item for item in violations)


def test_profile_domain_cli_dependency_is_rejected(tmp_path):
    _write(tmp_path, "profiles/registry.py", "from hermes_cli import config\n")
    violations = gate.find_profile_ownership_violations(tmp_path)
    assert any("profile domain depends on CLI" in item for item in violations)


def test_runtime_moved_symbol_facade_use_is_rejected(tmp_path):
    _write(
        tmp_path,
        "agent/sample.py",
        "from hermes_cli import profiles as hp\n"
        "value = hp.profile_exists('work')\n",
    )
    violations = gate.find_profile_ownership_violations(tmp_path)
    assert any("profile_exists is read through hermes_cli.profiles" in item for item in violations)


def test_test_patch_of_moved_facade_symbol_is_rejected(tmp_path):
    _write(
        tmp_path,
        "tests/gateway/test_sample.py",
        "from unittest.mock import patch\n"
        "patch('hermes_cli.profiles.profiles_to_serve', return_value=[])\n",
    )
    violations = gate.find_profile_ownership_violations(tmp_path)
    assert any("profiles_to_serve through hermes_cli.profiles" in item for item in violations)
