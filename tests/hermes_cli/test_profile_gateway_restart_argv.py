"""Profile restart uses a single canonical runtime launcher."""
import pytest
from hermes_cli import gateway


@pytest.mark.parametrize("profile,tail", [
    ("default", ["gateway", "run", "--replace"]),
    ("coder", ["--profile", "coder", "gateway", "run", "--replace"]),
])
def test_profile_restart_argv_has_only_one_python_launcher(profile, tail):
    argv = gateway._gateway_run_args_for_profile(profile)
    assert argv[1:3] == ["-I", "-c"]
    assert argv[4:] == tail
    assert "hermes_cli.main" not in argv[4:]
    assert "-m" not in argv[4:]
