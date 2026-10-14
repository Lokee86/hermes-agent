"""Run ownership contracts with upper layers unavailable in a fresh interpreter."""
from pathlib import Path
import subprocess
import sys
import textwrap


def probe_without_upper_layers(body):
    bootstrap = """
import importlib.abc
import sys

blocked = []

class RefuseUpperLayers(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'hermes_cli', 'nous_cli', 'agent', 'gateway'}:
            blocked.append(fullname)
            raise ImportError('upper layer unavailable: ' + fullname)

sys.meta_path.insert(0, RefuseUpperLayers())
"""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(bootstrap) + textwrap.dedent(body) + "\nassert not blocked, blocked"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
