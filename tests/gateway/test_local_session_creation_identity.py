"""Named-chat birth and exact workspace selection through the canonical authority."""
import asyncio
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from gateway.session_controls import AuthorityConnection


async def _authority(tmp_path, monkeypatch):
    from gateway.config import GatewayConfig
    from gateway.session import SessionStore
    from gateway.session_authority import initialize_session_authority
    import gateway.run as run
    monkeypatch.setattr(run, "_load_gateway_config", lambda: {
        "model": {"default": "fixture"}, "platform_toolsets": {"cli": []}})
    monkeypatch.setattr(run, "_resolve_gateway_model", lambda config: "fixture")
    store = SessionStore(tmp_path / "sessions", GatewayConfig())
    runner = run.GatewayRunner.__new__(run.GatewayRunner)
    runner.adapters, runner.session_store, runner._session_db, runner._draining = {}, store, store._db, False
    authority = await initialize_session_authority(runner,
        profile_id=str(Path(store._db.db_path).parent), instance_id="test")
    authority._schedule = lambda ref: None
    return authority


def _connection(authority):
    return AuthorityConnection(authority, SimpleNamespace(write=lambda frame: None), {"user_id": "owner"})


@pytest.mark.asyncio
async def test_named_creators_converge_while_first_launch_hook_is_pending(tmp_path, monkeypatch):
    from gateway import session_policy
    authority = await _authority(tmp_path, monkeypatch)
    first, second = _connection(authority), _connection(authority)
    entered, release = threading.Event(), threading.Event()
    def hooks(policy):
        if not entered.is_set():
            entered.set()
            assert release.wait(10)
    monkeypatch.setattr(session_policy, "accept_launch_hooks", hooks)
    params = {"title": "Shared work", "source": "cli", "cwd": str(tmp_path)}
    task = asyncio.create_task(first.dispatch({"id": 1, "method": "session.create",
        "params": dict(params, request_id="first")}))
    other_task = None
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        other_task = asyncio.create_task(second.dispatch({"id": 2, "method": "session.create",
            "params": dict(params, request_id="second")}))
        other = await asyncio.wait_for(other_task, 10)
        release.set()
        result = await asyncio.wait_for(task, 10)
        assert "result" in result and "result" in other, (result, other)
        assert result["result"]["stored_session_id"] == other["result"]["stored_session_id"]
        with authority.db._read_ctx() as conn:
            assert conn.execute("SELECT COUNT(*) FROM sessions WHERE chat_id LIKE 'local-%'").fetchone()[0] == 1
        assert authority.db.get_session(result["result"]["stored_session_id"])["title_source"] == "user"
    finally:
        release.set()
        await asyncio.gather(task, *([other_task] if other_task else []), return_exceptions=True)
        await first.close()
        await second.close()
        authority.db.close()


@pytest.mark.asyncio
async def test_latest_exact_cwd_finds_saved_chat_beyond_100_newer_descendants(tmp_path, monkeypatch):
    authority = await _authority(tmp_path, monkeypatch)
    connection = _connection(authority)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cwd = str(workspace)
    try:
        created = await connection.dispatch({"id": 1, "method": "session.create",
            "params": {"source": "cli", "cwd": cwd, "request_id": "wanted"}})
        assert "result" in created, created
        wanted = created["result"]["stored_session_id"]
        for i in range(125):
            authority.db.create_session(f"newer-{i}", source="cli",
                cwd=str(workspace / f"child-{i}"), user_id=connection.actor.subject)
        resumed = await connection.dispatch({"id": 2, "method": "session.resume",
            "params": {"latest": True, "cwd": cwd}})
        assert "result" in resumed, resumed
        assert resumed["result"]["stored_session_id"] == wanted
    finally:
        await connection.close()
        authority.db.close()


@pytest.mark.asyncio
async def test_concurrent_skill_preparation_rechecks_title_before_birth(tmp_path, monkeypatch):
    from gateway import session_policy
    authority = await _authority(tmp_path, monkeypatch)
    first, second = _connection(authority), _connection(authority)
    barrier = threading.Barrier(2)
    monkeypatch.setattr(session_policy, "launch_skills", lambda params: True)
    def render(params, sid):
        barrier.wait(timeout=10)
        return "Prepared skill"
    monkeypatch.setattr(session_policy, "render_launch_skills", render)
    params = {"title": "Skill work", "source": "cli", "cwd": str(tmp_path)}
    try:
        results = await asyncio.wait_for(asyncio.gather(
            first.dispatch({"id": 1, "method": "session.create", "params": dict(params, request_id="skill-first")}),
            second.dispatch({"id": 2, "method": "session.create", "params": dict(params, request_id="skill-second")})), 15)
        assert all("result" in result for result in results), results
        assert results[0]["result"]["stored_session_id"] == results[1]["result"]["stored_session_id"]
        with authority.db._read_ctx() as conn:
            assert conn.execute("SELECT COUNT(*) FROM sessions WHERE chat_id LIKE 'local-%'").fetchone()[0] == 1
    finally:
        barrier.abort()
        await first.close()
        await second.close()
        authority.db.close()


@pytest.mark.asyncio
async def test_title_conflict_rolls_back_session_route_and_receipt(tmp_path, monkeypatch):
    from gateway.session_local import create_local_session
    from gateway.session_local_recovery import local_identity
    from hermes_state_runtime import RuntimeStoreError
    from hermes_state_local import POLICY_PREFIX
    authority = await _authority(tmp_path, monkeypatch)
    connection = _connection(authority)
    params = {"source": "cli", "cwd": str(tmp_path)}
    try:
        result = await connection.dispatch({"id": 1, "method": "session.create",
            "params": dict(params, title="Reserved", request_id="winner")})
        assert "result" in result
        loser = local_identity(authority.profile_id, connection.actor.subject, "loser")
        with pytest.raises(RuntimeStoreError, match="admission_conflict"):
            create_local_session(authority, connection.actor,
                dict(params, request_id="loser"), title="Reserved")
        assert authority.db.get_session(loser) is None
        with authority.db._read_ctx() as conn:
            assert conn.execute("SELECT COUNT(*) FROM gateway_routing").fetchone()[0] == 1
            assert conn.execute("SELECT 1 FROM state_meta WHERE key=?", (POLICY_PREFIX + loser,)).fetchone() is None
    finally:
        await connection.close()
        authority.db.close()
