"""Prepared confirmation retains its CAS identity and never treats refusal as success."""
import asyncio
import pytest
from gateway.client import GatewayClientError
from hermes_cli.gateway_mutations import PreparedMutations


class Owner:
    def __init__(self):
        self.calls = []
        self.fail_confirm_once = False

    async def rpc(self, method, **params):
        self.calls.append((method, params))
        if method == "session.resume":
            return {"revision": 9, "execution_generation": 6}
        if params["payload"].get("confirm") == "token":
            if self.fail_confirm_once:
                self.fail_confirm_once = False
                raise GatewayClientError("connection_closed")
            return {"status": "applied"}
        return {"status": "confirmation_required", "confirm": "token",
                "confirm_message": "guarded target"}


@pytest.mark.asyncio
async def test_approved_retry_preserves_confirmation_token_and_metadata_fence():
    owner = Owner()
    owner.fail_confirm_once = True
    mutations = PreparedMutations()
    async def approve(_): return True
    with pytest.raises(GatewayClientError, match="connection_closed"):
        await mutations.apply(owner, "s", "model", {"model": "expensive"}, confirm=approve)
    assert (await mutations.apply(owner, "s", "model", {"model": "expensive"}, confirm=approve))["status"] == "applied"
    assert sum(method == "session.resume" for method, _ in owner.calls) == 1
    sent = [params for method, params in owner.calls if method == "session.mutate"]
    assert sent[1] == sent[2]
    assert sent[0]["request_id"] == sent[1]["request_id"]
    assert sent[1]["expected_revision"] == 9 and sent[1]["expected_generation"] == 6


@pytest.mark.asyncio
async def test_denied_or_timed_out_confirmation_cancels_without_resubmission():
    for callback in (lambda _: asyncio.sleep(0, result=False),
                     lambda _: asyncio.sleep(0, result=None)):
        owner, mutations = Owner(), PreparedMutations()
        result = await mutations.apply(owner, "s", "model", {"model": "expensive"}, confirm=callback)
        assert result == {"status": "cancelled"}
        assert sum(method == "session.mutate" for method, _ in owner.calls) == 1
        assert not mutations.pending


@pytest.mark.asyncio
async def test_missing_callback_is_refusal_not_success():
    owner = Owner()
    with pytest.raises(GatewayClientError, match="guarded target"):
        await PreparedMutations().apply(owner, "s", "model", {"model": "expensive"})
    assert sum(method == "session.mutate" for method, _ in owner.calls) == 1
