"""Profile polling and role selection contracts through live owners."""
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from gateway.session_group_controls import _profiles
from profiles.metadata import read_profile_meta
from toolsets import profile_role_toolsets


def test_gateway_profile_polls_cache_config_and_invalidate(tmp_path, monkeypatch):
    import hermes_yaml as yaml
    from profiles.reads import read_config_model
    config = tmp_path / "config.yaml"
    config.write_text("model: first\n", encoding="utf-8")
    real_load = yaml.safe_load
    parsed = []
    def load(text, *args, **kwargs):
        parsed.append(text)
        return real_load(text, *args, **kwargs)
    monkeypatch.setattr(yaml, "safe_load", load)
    authority = SimpleNamespace()
    for _ in range(3):
        assert _profiles(authority, None, tmp_path, {"include_sessions": False})["profiles"][0]["model"] == "first"
    assert read_config_model(tmp_path) == ("first", None)
    assert len(parsed) == 1
    config.write_text("model: second-model\n", encoding="utf-8")
    assert _profiles(authority, None, tmp_path, {"include_sessions": False})["profiles"][0]["model"] == "second-model"
    assert len(parsed) == 2


@pytest.mark.parametrize("raw", ["[setup]", "{name: setup}", "123", "null", "unknown"])
def test_malformed_role_is_ignored(tmp_path, raw):
    (tmp_path / "profile.yaml").write_text(f"role: {raw}\n", encoding="utf-8")
    assert read_profile_meta(tmp_path)["role"] is None


def test_setup_role_grants_and_denies_reserved_tools(tmp_path, monkeypatch):
    from model_tools import _select_tool_names
    from tui_gateway import agent_factory
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(agent_factory, "_load_disabled_toolsets", lambda: [])
    (tmp_path / "profile.yaml").write_text("role: setup\n", encoding="utf-8")
    granted, denied = profile_role_toolsets(tmp_path)
    assert "setup" in granted and "setup" not in denied
    assert "setup_choose" in _select_tool_names(["setup"], None, True)
    assert "setup" in agent_factory._with_session_toolsets([], "desktop")
    (tmp_path / "profile.yaml").write_text("role: null\n", encoding="utf-8")
    granted, denied = profile_role_toolsets(tmp_path)
    assert "setup" not in granted and "setup" in denied
    assert "setup_choose" not in _select_tool_names(["setup"], None, True)
    assert "setup" not in agent_factory._with_session_toolsets(["setup"], "desktop")


def test_gateway_skill_count_refresh_does_not_walk_on_request(tmp_path, monkeypatch):
    from profiles import skills as counts
    (tmp_path / "skills" / "one").mkdir(parents=True)
    (tmp_path / "skills" / "one" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    counts._SKILL_COUNT_CACHE.clear()
    counts._SKILL_COUNT_NEXT_CHECK.clear()
    walked = threading.Event()
    real_walk = counts._walk_skill_count
    threads = []
    def walk(path):
        threads.append(threading.current_thread())
        result = real_walk(path)
        walked.set()
        return result
    monkeypatch.setattr(counts, "_walk_skill_count", walk)
    caller = threading.current_thread()
    assert _profiles(SimpleNamespace(), None, tmp_path, {"include_sessions": False})["profiles"][0]["skill_count"] in (0, 1)
    assert walked.wait(5), "poll did not schedule skill refresh"
    threads[0].join(timeout=5)
    assert caller not in threads
    assert _profiles(SimpleNamespace(), None, tmp_path, {"include_sessions": False})["profiles"][0]["skill_count"] == 1


@pytest.mark.asyncio
async def test_runtime_advertises_every_supported_creation_source():
    from gateway.session_controls import AuthorityConnection
    from gateway.session_policy import SURFACES
    async def ping(ref, params):
        return {"pong": True}
    connection = SimpleNamespace(ping=ping, authority=SimpleNamespace(
        instance_id="fixture", profile_id="fixture", epoch=1))
    result = await AuthorityConnection.describe(connection, None, {})
    assert set(result["session_create"]["sources"]) == set(SURFACES)
