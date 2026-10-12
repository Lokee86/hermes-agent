"""Recovered cron receipts must settle execution before delivery and journal removal."""
import json
from contextlib import asynccontextmanager

from cron import jobs, executions, scheduler_authority


def test_recovered_execution_is_terminal_before_delivery(monkeypatch, tmp_path):
    from gateway import client as gateway_client
    from cron import delivery_queue
    with jobs.use_cron_store(tmp_path / "cron"):
        job = jobs.create_job(prompt="report", schedule="every 1h", deliver="telegram:1")
        row = executions.create_execution(job["id"], source="test")
        executions.mark_execution_running(row["id"])
        with executions._transaction() as conn:
            conn.execute("UPDATE executions SET process_id=?,pid=? WHERE id=?",
                         ("dead-owner", 999999, row["id"]))
        journal = scheduler_authority.journal_path(job["id"], row["id"])
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(json.dumps({"params": {"job_id": job["id"], "request_id": row["id"],
                                                 "extra_prompt": None}, "receipt": None}))
        class Peer:
            async def rpc(self, method, **params):
                return {"status": "terminal", "job": job, "result": [True, "output", "answer", None]}
        @asynccontextmanager
        async def connected():
            yield Peer()
        monkeypatch.setattr(gateway_client, "connect_gateway", connected)
        observed = []
        def enqueue(*args, **kwargs):
            assert executions.get_execution(row["id"])["status"] == "completed"
            assert journal.exists()
            observed.append("enqueue")
        monkeypatch.setattr(delivery_queue, "enqueue", enqueue)
        scheduler_authority.reconcile_pending()
        assert observed == ["enqueue"]
        assert not journal.exists()
