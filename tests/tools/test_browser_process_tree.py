"""Browser teardown delegates to the retained runtime owner and kills owned trees."""
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace

import psutil
import pytest

from tools.browser_tool_lifecycle import _kill_process_tree


def test_browser_cleanup_uses_canonical_popen_owner(monkeypatch):
    from runtime import processes

    seen = []
    proc = SimpleNamespace(pid=123)
    monkeypatch.setattr(processes, "kill_popen_process_tree", seen.append)
    _kill_process_tree(proc)
    assert seen == [proc]


def _running(pid):
    try:
        return psutil.Process(pid).status() not in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD)
    except psutil.NoSuchProcess:
        return False


def _exercise_owned_tree(tmp_path, *, own_group):
    receipt = tmp_path / "grandchild.json"
    script = tmp_path / "disposable browser.py"
    script.write_text(
        "import json, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "target = Path(sys.argv[1]); temp = target.with_suffix('.tmp')\n"
        "temp.write_text(json.dumps({'pid': p.pid})); temp.replace(target)\n"
        "time.sleep(60)\n", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(script), str(receipt)], start_new_session=own_group,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    grandchild = None
    try:
        deadline = time.monotonic() + 10
        while not receipt.exists() and time.monotonic() < deadline:
            time.sleep(.03)
        assert receipt.exists(), "child did not publish its owned descendant"
        grandchild = psutil.Process(json.loads(receipt.read_text())["pid"])
        if os.name != "nt":
            assert os.getpgid(proc.pid) == (proc.pid if own_group else os.getpgid(0))
        _kill_process_tree(proc)
        proc.wait(timeout=10)
        deadline = time.monotonic() + 10
        while _running(grandchild.pid) and time.monotonic() < deadline:
            time.sleep(.03)
        assert not _running(grandchild.pid), "owned descendant survived browser teardown"
        assert psutil.Process(os.getpid()).is_running()
    finally:
        if grandchild is not None and grandchild.is_running():
            try:
                grandchild.kill()
            except psutil.NoSuchProcess:
                pass
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)


@pytest.mark.platforms("posix")
@pytest.mark.live_system_guard_bypass
@pytest.mark.parametrize("own_group", [False, True])
def test_posix_browser_tree_kill_spares_callers_group(tmp_path, own_group):
    _exercise_owned_tree(tmp_path, own_group=own_group)


@pytest.mark.platforms("windows")
@pytest.mark.live_system_guard_bypass
def test_windows_browser_cleanup_kills_owned_descendants(tmp_path):
    _exercise_owned_tree(tmp_path, own_group=False)
