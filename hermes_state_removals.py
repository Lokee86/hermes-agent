"""Committed transcript removal receipts for external copy consumers."""

from __future__ import annotations

from contextlib import nullcontext
import json
import logging
from pathlib import Path

logger = logging.getLogger("hermes")


class SessionTranscriptRemovalsMixin:
    TRANSCRIPT_REMOVALS_VERSION = 1

    def committed_transcript_removals(self, *, after_sequence: int = 0, limit: int = 128) -> list[dict]:
        """Page this store's committed removals in ascending sequence order.

        Persist the last processed sequence alongside the consumer's own durable
        work. Each event describes one session in this profile's store. Archive
        and restore never enter this stream.
        """
        if type(after_sequence) is not int or not 0 <= after_sequence < (1 << 63):
            raise ValueError("after_sequence must be a nonnegative SQLite integer")
        if type(limit) is not int or not 1 <= limit <= 128:
            raise ValueError("limit must be between 1 and 128")
        rows = self._read_all(
            "SELECT * FROM transcript_removals WHERE sequence > ? ORDER BY sequence LIMIT ?",
            (after_sequence, limit),
        )
        receipts = []
        for row in rows:
            receipt = {field: row[field] for field in ("sequence", "event_id", "kind", "session_id")}
            if row["kind"] == "rewind":
                receipt.update(
                    previous_head_message_uid=row["previous_head_message_uid"],
                    last_surviving_message_uid=row["last_surviving_message_uid"],
                    removed_message_uids=json.loads(row["removed_message_uids"]),
                )
            receipts.append(receipt)
        return receipts


def record_session_deletions(conn, session_ids):
    """Record exactly the specified rows that still exist in the deleting transaction."""
    conn.execute(
        "INSERT INTO transcript_removals (event_id, kind, session_id) "
        "SELECT lower(hex(randomblob(16))), 'delete', id FROM sessions "
        "WHERE id IN (SELECT value FROM json_each(?)) ORDER BY id",
        (json.dumps(session_ids),),
    )


def rewind_receipt_rows(conn, session_id):
    """Read the logical identities of the source transcript on its write connection."""
    from hermes_state_identity import _uid_list

    return [
        (uid, _uid_list(absorbed))
        for uid, absorbed in conn.execute(
            "SELECT message_uid, absorbed_message_uids FROM messages "
            "WHERE session_id = ? AND (active = 1 OR compacted = 1) ORDER BY id",
            (session_id,),
        )
    ]


def record_rewind(conn, session_id, before):
    """Record only logical identities that vanished from the committed source."""
    after = {
        logical_uid
        for uid, absorbed in rewind_receipt_rows(conn, session_id)
        for logical_uid in (uid, *absorbed)
        if logical_uid
    }
    removed = {}
    previous_head = surviving_head = None
    for uid, absorbed in before:
        if uid:
            previous_head = uid
            if not removed and uid in after:
                surviving_head = uid
        removed.update(dict.fromkeys(logical_uid for logical_uid in (uid, *absorbed)
                                     if logical_uid and logical_uid not in after))
    if not removed:
        return
    conn.execute(
        "INSERT INTO transcript_removals (event_id, kind, session_id, "
        "previous_head_message_uid, last_surviving_message_uid, removed_message_uids) "
        "VALUES (lower(hex(randomblob(16))), 'rewind', ?, ?, ?, ?)",
        (session_id, previous_head, surviving_head, json.dumps(list(removed))),
    )


def emit_transcript_removal(db):
    """Best-effort post-commit wake-up. The receipt stream is the replay authority."""
    try:
        from agent.runtime_scope import bind_profile_scope
        from hermes_cli.lifecycle import invoke_hook
        from hermes_constants import get_hermes_home, profile_name_for_home

        path = Path(db.db_path).resolve()
        home = path.parent
        profile = profile_name_for_home(home)
        # Detached copies must not wake observers for a differently named store.
        if profile is None or path.name != "state.db":
            return
        binding = bind_profile_scope(home, hydrate_secrets=False) if home != get_hermes_home().resolve() else nullcontext()
        with binding:
            invoke_hook("on_transcript_removal", profile=profile, hermes_home=str(home))
    except Exception:
        logger.warning("on_transcript_removal dispatch failed", exc_info=True)
