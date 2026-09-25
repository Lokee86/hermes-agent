"""Temporary strangler seam for CLI commands that have not migrated yet."""

from __future__ import annotations


def dispatch_legacy():
    """Run the existing CLI implementation until command ownership migrates."""
    from hermes_cli.main import main as legacy_main

    return legacy_main()
