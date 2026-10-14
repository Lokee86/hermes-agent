"""Runtime spawn/Git contracts work when CLI and execution policy are unavailable."""
from tests.runtime.ownership_probe import probe_without_upper_layers


def test_frozen_subprocess_exports_point_to_canonical_owners():
    from hermes_cli import _subprocess_compat as compat
    from runtime import git_subprocess, process_identity, processes, subprocess_compat

    owners = {
        "bounded_probe_run": subprocess_compat.bounded_probe_run,
        "split_command_line": subprocess_compat.split_command_line,
        "windows_hide_flags": subprocess_compat.windows_hide_flags,
        "bounded_git_probe": git_subprocess.bounded_git_probe,
        "harden_git_argv": git_subprocess.harden_git_argv,
        "pid_exists_stdlib": process_identity.pid_exists_stdlib,
        "kill_process_tree": processes.kill_popen_process_tree,
    }
    for name, owner in owners.items():
        assert getattr(compat, name) is owner


def test_bounded_capture_and_git_policy_need_no_upper_layers():
    probe_without_upper_layers("""
        import sys
        from runtime import processes
        from runtime.git_subprocess import harden_git_argv
        from runtime.subprocess_compat import bounded_probe_run

        assert harden_git_argv(['diff']) == ['diff', '--no-ext-diff', '--no-textconv']
        result = bounded_probe_run(
            [sys.executable, '-c', 'print(42)'], timeout=10)
        assert result.returncode == 0
        assert result.stdout.strip() == '42'
    """)
