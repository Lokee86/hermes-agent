"""Recovered cron receipts settle through the scheduler's canonical terminal tail."""

import json
from contextlib import asynccontextmanager

from cron import executions, jobs, scheduler, scheduler_authority


def _fixture(monkeypatch, tmp_path):
    from gateway import client as gateway_client

    store = jobs.use_cron_store(tmp_path / "cron")
    store.__enter__()
    job = jobs.create_job(prompt="report", schedule="every 1h", deliver="telegram:1")
    row = executions.create_execution(job["id"], source="test")
    executions.mark_execution_running(row["id"])
    with executions._transaction() as conn:
        conn.execute(
            "UPDATE executions SET process_id=?,pid=? WHERE id=?",
            ("dead-owner", 999999, row["id"]),
        )
    journal = scheduler_authority.journal_path(job["id"], row["id"])
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text(
        json.dumps(
            {
                "params": {
                    "job_id": job["id"],
                    "request_id": row["id"],
                    "extra_prompt": None,
                },
                "receipt": None,
            }
        ),
        encoding="utf-8",
    )

    class Peer:
        async def rpc(self, method, **params):
            assert method == "cron.recover"
            return {
                "status": "terminal",
                "job": job,
                "result": [True, "output", "answer", None],
            }

    @asynccontextmanager
    async def connected():
        yield Peer()

    monkeypatch.setattr(gateway_client, "connect_gateway", connected)
    return store, job, row, journal


def test_recovered_execution_uses_canonical_terminal_tail(monkeypatch, tmp_path):
    from cron import delivery_queue

    store, job, row, journal = _fixture(monkeypatch, tmp_path)
    try:
        observed = []

        def enqueue(*args, **kwargs):
            # Delivery can be queued before the ledger terminalizes; the journal
            # remains the durable recovery link until _finish_completed_run settles.
            assert executions.get_execution(row["id"])["status"] == "running"
            assert journal.exists()
            observed.append("enqueue")
            return {"status": "pending"}

        monkeypatch.setattr(delivery_queue, "enqueue", enqueue)

        scheduler_authority.reconcile_pending()

        assert observed == ["enqueue"]
        assert executions.get_execution(row["id"])["status"] == "completed"
        assert jobs.get_job(job["id"])["repeat"]["completed"] == 1
        assert not journal.exists()
    finally:
        store.__exit__(None, None, None)


def test_recovery_keeps_journal_and_unfinished_row_when_settlement_fails(
    monkeypatch, tmp_path
):
    from cron import delivery_queue

    store, job, row, journal = _fixture(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(
            delivery_queue,
            "enqueue",
            lambda *args, **kwargs: {"status": "pending"},
        )

        def fail_mark(*args, **kwargs):
            raise OSError("jobs.json unavailable")

        monkeypatch.setattr(scheduler, "mark_job_run", fail_mark)

        scheduler_authority.reconcile_pending()

        assert journal.exists()
        assert executions.get_execution(row["id"])["status"] == "running"
        assert jobs.get_job(job["id"])["last_run_at"] is None
    finally:
        store.__exit__(None, None, None)
