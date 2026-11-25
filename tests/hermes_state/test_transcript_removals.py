"""Transcript removal authority can replay after a missed lifecycle callback."""

import sqlite3

import pytest

from hermes_state import SessionDB


def test_removal_replay_after_restart_is_ordered_and_profile_local(tmp_path, monkeypatch):
    from hermes_cli import lifecycle
    from hermes_constants import get_hermes_home

    home = tmp_path / "profiles" / "source"
    path = home / "state.db"
    other = tmp_path / "profiles" / "other"
    home.mkdir(parents=True)
    other.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(other))
    wakeups = []

    def missed(hook, **payload):
        if hook == "on_transcript_removal":
            wakeups.append((get_hermes_home(), payload))
            raise RuntimeError("observer unavailable")

    monkeypatch.setattr(lifecycle, "invoke_hook", missed)
    with SessionDB(other / "state.db") as db:
        db.create_session("source-chat", source="cli")
    with SessionDB(path) as db:
        for session in ("source-chat", "other-chat", "kept-chat"):
            db.create_session(session, source="cli")
            db.append_message(session, "user", "identical text")
        assert db.set_session_archived("source-chat", True)
        assert db.set_session_archived("source-chat", False)
        assert db.committed_transcript_removals() == []

        first = db.get_messages("source-chat")[0]
        db.rewind_user_turn("source-chat", 0)
        db.append_message("source-chat", "user", "identical text")
        assert db.get_messages("source-chat")[0]["message_uid"] != first["message_uid"]
        assert db.set_session_archived("source-chat", True)
        assert db.delete_sessions(["source-chat", "other-chat", "missing"]) == 2
        assert db.get_session("kept-chat")
    assert wakeups == [(home, {"profile": "source", "hermes_home": str(home)})] * 2
    assert get_hermes_home() == other

    with SessionDB(path, read_only=True) as db:
        rewind, = db.committed_transcript_removals(limit=1)
        assert rewind == {
            "sequence": 1, "event_id": rewind["event_id"], "kind": "rewind",
            "session_id": "source-chat", "previous_head_message_uid": first["message_uid"],
            "last_surviving_message_uid": None, "removed_message_uids": [first["message_uid"]],
        }
        deletes = db.committed_transcript_removals(after_sequence=rewind["sequence"])
        assert [(event["kind"], event["session_id"]) for event in deletes] == [
            ("delete", "other-chat"), ("delete", "source-chat"),
        ]
        assert len({event["event_id"] for event in [rewind, *deletes]}) == 3
        assert db.committed_transcript_removals(after_sequence=deletes[-1]["sequence"]) == []
    with SessionDB(path, read_only=True) as db:
        assert db.committed_transcript_removals() == [rewind, *deletes]
    with SessionDB(other / "state.db", read_only=True) as db:
        assert db.get_session("source-chat")
        assert db.committed_transcript_removals() == []


def test_transcript_write_rolls_back_if_its_removal_cannot_be_recorded(tmp_path):
    with SessionDB(tmp_path / "state.db") as db:
        db.create_session("s", source="cli")
        db.append_message("s", "user", "will survive")
        before = db.get_messages("s")
        db._execute_write(lambda conn: conn.execute(
            "CREATE TEMP TRIGGER refuse_receipt BEFORE INSERT ON transcript_removals "
            "BEGIN SELECT RAISE(ABORT, 'receipt unwritable'); END"
        ))
        with pytest.raises(sqlite3.IntegrityError, match="receipt unwritable"):
            db.rewind_to_message("s", before[0]["id"])
        assert db.get_messages("s") == before
        assert db.get_session("s")["rewind_count"] == 0
        with pytest.raises(sqlite3.IntegrityError, match="receipt unwritable"):
            db.delete_session("s")
        assert db.get_session("s")
        assert db.get_messages("s") == before
        assert db.committed_transcript_removals() == []
