"""Profile-scoped durable cursor and read-only source facade for conversation indexes."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path


def _normalize_profile_name(profile_name: str | None) -> str:
    return str(profile_name or "default").strip() or "default"


def _profile_index_digest(profile_name: str, index_name: str) -> str:
    identity = f"{profile_name}\0{index_name}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def _fsync_directory(path: Path) -> None:
    """Best-effort directory sync after an atomic cursor replacement on POSIX."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        try:
            os.fsync(fd)
        except OSError:
            pass
    finally:
        os.close(fd)


class ConversationIndexCursorStore:
    """Durable at-least-once replay cursor owned by Hermes, not the plugin."""

    def __init__(self, hermes_home: Path, index_name: str, profile_name: str = "default"):
        self.profile_name = _normalize_profile_name(profile_name)
        digest = _profile_index_digest(self.profile_name, index_name)
        self.root = Path(hermes_home) / "conversation-index"
        self.path = self.root / f"{digest}.cursor.json"
        self.index_name = index_name

    def load(self) -> int:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            cursor = payload.get("cursor")
            if (
                payload.get("index") != self.index_name
                or payload.get("profile") != self.profile_name
                or isinstance(cursor, bool)
            ):
                return 0
            return cursor if isinstance(cursor, int) and cursor >= 0 else 0
        except (OSError, ValueError, TypeError):
            return 0

    def save(self, cursor: int) -> None:
        if isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0:
            raise ValueError("cursor must be a non-negative integer")
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
        data = json.dumps(
            {"index": self.index_name, "profile": self.profile_name, "cursor": cursor},
            separators=(",", ":"),
        )
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
            _fsync_directory(self.root)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass


class ConversationIndexSourceFacade:
    """Whitelist the canonical read API exposed to an index plugin."""

    __slots__ = ("_db",)

    def __init__(self, db):
        self._db = db

    def get_conversation_snapshot(self, **kwargs):
        return self._db.get_conversation_snapshot(**kwargs)

    def hydrate_message_references(self, references, **kwargs):
        return self._db.hydrate_message_references(references, **kwargs)

    def list_index_conversation_ids(self, **kwargs):
        return self._db.list_index_conversation_ids(**kwargs)

    def resolve_index_conversation_ids(self, conversation_ids):
        return self._db.resolve_index_conversation_ids(conversation_ids)
