"""Storage operations and runtime probing work without CLI/Gateway ownership."""
from tests.runtime.ownership_probe import probe_without_upper_layers


def test_frozen_sqlite_exports_retain_canonical_identity():
    from hermes_cli import sqlite_runtime, sqlite_safe_read
    from runtime import sqlite_runtime as runtime_owner
    from storage import sqlite_safe_read as storage_owner

    assert sqlite_runtime.probe_sqlite_runtime is runtime_owner.probe_sqlite_runtime
    for name in ("LiveConnectionError", "has_live_connection", "offline_file_access",
                 "read_header_bytes_preopen", "SQLITE_HEADER_MAGIC"):
        assert getattr(sqlite_safe_read, name) is getattr(storage_owner, name)
    for retired in ("connect_tracked", "TrackedConnection", "UntrackableConnectionError"):
        assert not hasattr(sqlite_safe_read, retired)


def test_sqlite_transactions_and_probe_need_no_upper_layers():
    probe_without_upper_layers("""
        import sys
        import tempfile
        from pathlib import Path
        from runtime.sqlite_runtime import probe_sqlite_runtime
        from storage.sqlite_util import open_db, transaction

        # WAL configuration is state policy; isolate the storage transaction primitive.
        with tempfile.TemporaryDirectory() as home:
            db = Path(home) / 'state.db'
            with transaction(open_db(db, db_label='ownership', wal=False)) as conn:
                conn.execute('CREATE TABLE items(value TEXT)')
                conn.execute("INSERT INTO items VALUES ('persisted')")
            conn = open_db(db, db_label='ownership', wal=False)
            try:
                assert conn.execute('SELECT value FROM items').fetchone()[0] == 'persisted'
            finally:
                conn.close()
        info = probe_sqlite_runtime(sys.executable, timeout=10)
        assert info is not None and info.sqlite_version_string
    """)
