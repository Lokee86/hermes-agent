"""Explicit cron submit rejections fail; delivery ambiguity is never a definite refusal."""
from contextlib import asynccontextmanager
import pytest

from cron import scheduler_authority
from gateway import client as gateway_client


def _peer(monkeypatch, rejection):
    class Peer:
        async def rpc(self, method, **params):
            assert method == "cron.submit"
            raise rejection
    @asynccontextmanager
    async def connected():
        yield Peer()
    monkeypatch.setattr(gateway_client, "connect_gateway", connected)


def test_explicit_owner_rejection_is_failed_and_has_no_unknown_journal(monkeypatch, tmp_path):
    from hermes_constants import get_hermes_home
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    _peer(monkeypatch, gateway_client.GatewayRPCError("invalid_workdir"))
    result = scheduler_authority.run_canonical_job({"id": "denied"}, execution_id="rejected")
    assert result[0] is False and "invalid_workdir" in result[3]
    assert not scheduler_authority.journal_path("denied", "rejected").exists()


def test_disconnect_retains_journal_and_unknown(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    _peer(monkeypatch, gateway_client.GatewayClientError("connection_closed"))
    with pytest.raises(scheduler_authority.CronExecutionUnknown):
        scheduler_authority.run_canonical_job({"id": "uncertain"}, execution_id="uncertain-fire")
    assert scheduler_authority.journal_path("uncertain", "uncertain-fire").exists()
