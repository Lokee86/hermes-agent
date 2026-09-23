from agent import conversation_index_storage as storage
from agent.conversation_index_storage import ConversationIndexCursorStore


def test_cursor_store_is_profile_scoped_with_shared_home(tmp_path):
    first = ConversationIndexCursorStore(tmp_path, "fake", "profile-a")
    second = ConversationIndexCursorStore(tmp_path, "fake", "profile-b")

    assert first.path != second.path
    first.save(3)
    second.save(7)

    assert first.load() == 3
    assert second.load() == 7


def test_cursor_save_syncs_parent_directory_after_replace(monkeypatch, tmp_path):
    synced = []
    monkeypatch.setattr(storage, "_fsync_directory", lambda path: synced.append(path))
    store = ConversationIndexCursorStore(tmp_path, "fake", "default")

    store.save(9)

    assert store.load() == 9
    assert synced == [store.root]
