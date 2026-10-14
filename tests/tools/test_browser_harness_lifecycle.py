"""Endpoint changes restart every Browser Use daemon through its lifecycle owner."""
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def harness(tmp_path, monkeypatch):
    from tools import browser_tool, browser_use_cli, browser_supervisor

    script = tmp_path / "disposable harness.py"
    script.write_text("""
import json, os, sys, uuid
from pathlib import Path
root = Path(sys.argv[1])
name = os.getenv('BU_NAME', 'default')
latch = root / (name + '.json')
if '--reload' in sys.argv:
    latch.unlink(missing_ok=True)
else:
    sys.stdin.read()
    if not latch.exists():
        latch.write_text(json.dumps({'endpoint': os.getenv('BU_CDP_URL'), 'generation': uuid.uuid4().hex}))
    print(latch.read_text())
""", encoding="utf-8")
    monkeypatch.setattr(browser_use_cli, "_find_cli", lambda: [sys.executable, str(script), str(tmp_path)])
    monkeypatch.setattr(browser_use_cli, "_base_subprocess_env", dict)
    monkeypatch.setattr("hermes_cli.config.read_raw_config", lambda: {"browser": {"backend": "browser-use"}})
    monkeypatch.setattr("tools.browser_tool_cdp._resolve_cdp_override", lambda url: url)
    monkeypatch.setattr(browser_supervisor, "SUPERVISOR_REGISTRY",
                        SimpleNamespace(get_or_start=lambda *a, **kw: None, stop_all=lambda: None))
    monkeypatch.setattr(browser_tool, "_active_sessions", {})
    browser_use_cli._driven_daemons.clear()
    yield browser_use_cli
    browser_use_cli.stop_harness_daemons()


def test_endpoint_swap_creates_fresh_named_and_default_daemons(harness, monkeypatch):
    from tools.browser_tool_lifecycle import cleanup_all_browsers

    def drive(name):
        result = json.loads(harness.browser_exec("print(1)", session=name, task_id="swap"))
        assert result["success"], result
        return json.loads(result["output"])

    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9400")
    before = {name: drive(name) for name in ("", "research")}
    cleanup_all_browsers()
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9401")
    after = {name: drive(name) for name in before}
    for name in before:
        assert before[name]["endpoint"] == "http://127.0.0.1:9400"
        assert after[name]["endpoint"] == "http://127.0.0.1:9401"
        assert before[name]["generation"] != after[name]["generation"]


def test_failed_harness_stop_does_not_abort_other_cleanup(monkeypatch):
    from tools import browser_tool, browser_use_cli
    from tools.browser_tool_lifecycle import cleanup_all_browsers

    monkeypatch.setattr(browser_tool, "_active_sessions", {})
    monkeypatch.setattr(browser_tool, "_command_timeout_resolved", True)
    monkeypatch.setattr(browser_tool, "_cached_command_timeout", 7)

    def fail():
        raise subprocess.SubprocessError("harness unavailable")

    monkeypatch.setattr(browser_use_cli, "stop_harness_daemons", fail)
    cleanup_all_browsers()
    assert browser_tool._command_timeout_resolved is False
    assert browser_tool._cached_command_timeout is None
