"""Latest-session selection stays in the profile owner and respects workspace and actor."""
from types import SimpleNamespace

import pytest

from gateway.session_contract import SessionRef
from gateway.session_controls import AuthorityConnection


@pytest.mark.asyncio
async def test_latest_chooses_authorized_same_workspace_candidate(monkeypatch):
    from gateway import session_local_migration
    from hermes_state_runtime import RuntimeStoreError

    rows = [
        {'id': 'foreign', 'cwd': '/project'},
        {'id': 'elsewhere', 'cwd': '/other'},
        {'id': 'owned', 'cwd': '/project'},
    ]
    requested = []
    def select(**kwargs):
        requested.append(kwargs)
        return rows
    def resolve(_authority, _actor, sid):
        if sid == 'foreign':
            raise RuntimeStoreError('permission_denied')
        return SessionRef('home', sid)
    monkeypatch.setattr(session_local_migration, 'resolve_local_target', resolve)
    connection = object.__new__(AuthorityConnection)
    connection.authority = SimpleNamespace(db=SimpleNamespace(list_sessions_rich=select, get_session=lambda _: None),
                                            authorize=lambda *args: None)
    connection.actor = object()
    class Chosen(Exception):
        pass
    async def attach(_actor, ref):
        assert ref.session_id == 'owned'
        raise Chosen
    connection.authority.attach = attach
    with pytest.raises(Chosen):
        await connection.resume(SessionRef('home', ''), {'latest': True, 'cwd': '/project'})
    assert requested[0]['sources'] == ['cli', 'tui', 'gui', 'oneshot']
    assert requested[0]['order_by_last_active'] is True


@pytest.mark.asyncio
async def test_latest_fails_closed_when_no_authorized_match(monkeypatch):
    from gateway import session_local_migration
    from hermes_state_runtime import RuntimeStoreError

    monkeypatch.setattr(session_local_migration, 'resolve_local_target',
                        lambda *_: (_ for _ in ()).throw(RuntimeStoreError('permission_denied')))
    connection = object.__new__(AuthorityConnection)
    connection.authority = SimpleNamespace(
        db=SimpleNamespace(list_sessions_rich=lambda **_: [{'id': 'foreign', 'cwd': '/project'}]))
    connection.actor = object()
    with pytest.raises(RuntimeStoreError, match='not_found'):
        await connection.resume(SessionRef('home', ''), {'latest': True, 'cwd': '/project'})
