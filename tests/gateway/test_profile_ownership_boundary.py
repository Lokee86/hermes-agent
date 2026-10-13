"""Profile domain imports work without loading the CLI lifecycle facade."""
import json
import subprocess
import sys


def test_domain_resolution_does_not_load_cli(tmp_path):
    script = """
import json, sys
from profiles.paths import get_profile_dir
from profiles.registry import profile_exists
from profiles.names import normalize_profile_name
from profiles.metadata import read_profile_meta
home = get_profile_dir('default')
print(json.dumps([normalize_profile_name('default'), profile_exists('default'),
                  read_profile_meta(home)['role'], 'hermes_cli.profiles' in sys.modules]))
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == ["default", True, None, False]
