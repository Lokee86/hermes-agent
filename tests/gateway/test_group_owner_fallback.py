"""Hosted-room metadata keeps durable actor ownership when the runtime service is absent."""
from types import SimpleNamespace

import pytest

from gateway import hosted_rooms
from gateway.session_authority import SessionAuthority
from gateway.session_contract import Principal
from gateway.session_group_controls import _group
from hermes_state import SessionDB
from hermes_state_runtime import RuntimeStoreError, begin_runtime_epoch


def _authority(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    runner = SimpleNamespace(_draining=False)
    authority = SessionAuthority(
        runner,
        profile_id=str(tmp_path),
        instance_id="owner",
        db=db,
        epoch=begin_runtime_epoch(db, instance_id="owner"),
    )
    return authority


def _actor(home, subject):
    return Principal(
        subject,
        str(home),
        frozenset({"session:read", "session:control"}),
        "viewer-" + subject,
    )


def _members():
    return [
        {"member_id": "default", "profile": "default", "handle": "default"},
        {"member_id": "two", "profile": "two", "handle": "two"},
    ]


def test_service_absent_listing_does_not_expose_another_actors_room(tmp_path):
    authority = _authority(tmp_path)
    try:
        gateway_id = hosted_rooms.local_authority_gateway_id()
        hosted_rooms.create_room(
            authority.db.db_path,
            room_id="alice-room",
            name="Alice",
            members=_members(),
            authority_gateway_id=gateway_id,
        )
        authority.db._execute_write(lambda conn: conn.execute(
            "INSERT INTO state_meta(key,value) VALUES(?,?)",
            ("gateway.hosted.owner.v1:alice-room", "alice"),
        ))
        alice = _actor(tmp_path, "alice")
        bob = _actor(tmp_path, "bob")

        assert [room["room_id"] for room in _group(
            authority, alice, tmp_path, "groups.list", {}
        )["rooms"]] == ["alice-room"]
        assert _group(authority, bob, tmp_path, "groups.list", {})["rooms"] == []
        with pytest.raises(RuntimeStoreError, match="permission_denied"):
            _group(authority, bob, tmp_path, "groups.state", {"room_id": "alice-room"})
    finally:
        authority.db.close()


def test_service_absent_create_claims_durable_owner(tmp_path):
    authority = _authority(tmp_path)
    (tmp_path / "profiles" / "two").mkdir(parents=True)
    try:
        alice = _actor(tmp_path, "alice")
        created = _group(
            authority,
            alice,
            tmp_path,
            "groups.create",
            {"room_id": "alice-room", "name": "Alice", "members": _members()},
        )
        assert created["room"]["room_id"] == "alice-room"
        with authority.db._read_ctx() as conn:
            row = conn.execute(
                "SELECT value FROM state_meta WHERE key=?",
                ("gateway.hosted.owner.v1:alice-room",),
            ).fetchone()
        assert row is not None
        assert row[0] == "alice"
    finally:
        authority.db.close()