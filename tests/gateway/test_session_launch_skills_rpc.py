"""Session launch skills are rendered at most once per durable request identity."""
from types import SimpleNamespace
import pytest


@pytest.mark.asyncio
async def test_launch_skill_render_is_frozen_across_retry(monkeypatch):
    from gateway import session_local, session_local_recovery, session_policy
    from gateway.session_controls import AuthorityConnection
    from gateway.session_contract import SessionRef

    existing = set()
    rendered = []

    monkeypatch.setattr(session_local_recovery, "local_identity", lambda *_: "stable-id")

    def render(params, sid):
        rendered.append((sid, tuple(params["skills"])))
        return "FROZEN PRELOAD"

    def create(authority, actor, params, *, skills_prompt=None):
        if "stable-id" not in existing:
            assert skills_prompt == "FROZEN PRELOAD"
            existing.add("stable-id")
        else:
            assert skills_prompt is None
        return SessionRef("profile", "stable-id")

    monkeypatch.setattr(session_policy, "render_launch_skills", render)
    monkeypatch.setattr(session_local, "create_local_session", create)
    import hermes_state_local
    monkeypatch.setattr(hermes_state_local, "local_receipt", lambda *_: {"policy": "fixture"})
    monkeypatch.setattr(session_policy, "restore_policy", lambda _: object())
    monkeypatch.setattr(session_policy, "accept_launch_hooks", lambda _: None)
    connection = object.__new__(AuthorityConnection)
    connection.authority = SimpleNamespace(
        profile_id="profile",
        db=SimpleNamespace(get_session=lambda sid: {"id": sid} if sid in existing else None))
    connection.actor = SimpleNamespace(subject="owner")

    async def resume(ref, params):
        return {"session_id": ref.session_id}

    connection.resume = resume
    params = {"request_id": "r1", "skills": ["one"]}
    assert await connection.create(None, params.copy()) == {"session_id": "stable-id"}
    assert await connection.create(None, params.copy()) == {"session_id": "stable-id"}
    assert rendered == [("stable-id", ("one",))]
