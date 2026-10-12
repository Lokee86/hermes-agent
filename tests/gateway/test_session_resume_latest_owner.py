"""P2 routes latest-session resume through its existing workspace-aware owner resolver."""
from types import SimpleNamespace

import pytest

from gateway.session_contract import SessionRef
from gateway.session_controls import AuthorityConnection


@pytest.mark.asyncio
async def test_latest_resume_uses_owner_resolver(monkeypatch):
    from gateway import session_local_title
    calls = []

    def resolve(authority, actor, family, workspace=None):
        calls.append((family, workspace))
        return SessionRef('home', 'owned')

    monkeypatch.setattr(session_local_title, 'resolve_latest_session', resolve)
    connection = object.__new__(AuthorityConnection)
    connection.actor = SimpleNamespace()
    connection.authority = SimpleNamespace(
        db=SimpleNamespace(get_session=lambda _: None),
        authorize=lambda *args: None)
    class Selected(Exception):
        pass
    async def attach(actor, ref):
        assert ref.session_id == 'owned'
        raise Selected
    connection.authority.attach = attach
    with pytest.raises(Selected):
        await connection.resume(SessionRef('home', ''), {
            'latest': 'cli', 'workspace': '/workspace'})
    assert calls == [('cli', '/workspace')]
