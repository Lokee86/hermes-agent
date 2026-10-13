"""Explicit cron submit rejections fail; delivery ambiguity is never a definite refusal."""
from contextlib import asynccontextmanager
import json

import pytest

from cron import scheduler_authority
from gateway import client as gateway_client


def _peer(monkeypatch, rejection, *, recover=None):
    class Peer:
        async def rpc(self, method, **params):
            if method == "cron.recover" and recover is not None:
                return recover
            assert method == "cron.submit"
            raise rejection
    @asynccontextmanager
    async def connected():
        yield Peer()
    monkeypatch.setattr(gateway_client, "connect_gateway", connected)


def test_explicit_owner_rejection_is_failed_and_retained_for_settlement(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    _peer(
        monkeypatch,
        gateway_client.GatewayRPCError("invalid_workdir"),
        recover={"status": "missing"},
    )
    result = scheduler_authority.run_canonical_job({"id": "denied"}, execution_id="rejected")
    assert result[0] is False and "invalid_workdir" in result[3]
    journal = scheduler_authority.journal_path("denied", "rejected")
    assert journal.exists()
    record = json.loads(journal.read_text(encoding="utf-8-sig"))
    assert record["refusal"] == list(result)
    assert record["job"] == {"id": "denied"}


def test_disconnect_retains_journal_and_unknown(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    _peer(monkeypatch, gateway_client.GatewayClientError("connection_closed"))
    with pytest.raises(scheduler_authority.CronExecutionUnknown):
        scheduler_authority.run_canonical_job({"id": "uncertain"}, execution_id="uncertain-fire")
    assert scheduler_authority.journal_path("uncertain", "uncertain-fire").exists()
