"""ACP paths, aliases and guarded model changes use canonical interfaces."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import acp
import pytest
from acp.schema import AllowedOutcome
from acp_adapter.gateway_server import GatewayACPAgent


def agent_with_rpc():
    agent = GatewayACPAgent()
    agent._snapshots["s"] = {"pending": [], "revision": 1, "execution_generation": 0}
    agent._conn = AsyncMock()
    agent._gateway = SimpleNamespace(rpc=AsyncMock())
    return agent


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["/etc/hosts is wrong", "/notacommand please"])
async def test_unknown_slash_text_is_an_ordinary_prompt(text):
    agent = agent_with_rpc()
    agent._gateway.rpc.return_value = {"admission_id": "a", "status": "terminal", "outcome": "completed"}
    response = await agent.prompt([acp.text_block(text)], "s")
    assert response.stop_reason == "end_turn"
    calls = agent._gateway.rpc.await_args_list
    assert calls[0].args[0] == "prompt.submit"
    assert calls[0].kwargs["text"] == text
    assert all(call.args[0] != "session.mutate" for call in calls)


@pytest.mark.asyncio
async def test_compact_alias_uses_canonical_compress_mutation():
    agent = agent_with_rpc()
    agent._gateway.rpc.side_effect = [
        {"revision": 1, "execution_generation": 0},
        {"status": "preview", "lines": ["preview"]}]
    result = await agent.prompt([acp.text_block("/compact --preview")], "s")
    assert result.stop_reason == "end_turn"
    mutation = agent._gateway.rpc.await_args_list[1]
    assert mutation.kwargs["operation"] == "compress"
    assert mutation.kwargs["payload"] == {"preview": True}


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["picker", "slash"])
@pytest.mark.parametrize("choice", ["allow_once", "deny", "cancelled"])
async def test_model_guard_can_be_confirmed_or_cancelled(surface, choice):
    agent = agent_with_rpc()
    refusal = {"status": "confirmation_required", "confirm": "owner-token",
               "confirm_message": "Target has fewer tools", "warnings": [{"title": "Warning"}]}
    snapshot = {"session_id": "s", "revision": 1, "execution_generation": 0}
    agent._gateway.rpc.side_effect = [snapshot, refusal, {"status": "applied"}, snapshot]
    outcome = SimpleNamespace(outcome="cancelled") if choice == "cancelled" else AllowedOutcome(
        outcome="selected", option_id=choice)
    agent._conn.request_permission.return_value = SimpleNamespace(outcome=outcome)
    if surface == "picker":
        await agent.set_session_model("target", "s")
    else:
        result = await agent.prompt([acp.text_block("/model target")], "s")
        assert result.stop_reason == ("end_turn" if choice == "allow_once" else "cancelled")
    card = agent._conn.request_permission.await_args
    assert card.kwargs["session_id"] == "s"
    assert {option.option_id for option in card.kwargs["options"]} == {"allow_once", "deny"}
    mutations = [call for call in agent._gateway.rpc.await_args_list if call.args[0] == "session.mutate"]
    assert len(mutations) == (2 if choice == "allow_once" else 1)
    if choice == "allow_once":
        assert mutations[1].kwargs["payload"]["confirm"] == "owner-token"
    assert not agent._mutations.pending


@pytest.mark.asyncio
async def test_confirmed_model_retry_retains_request_without_asking_twice():
    from hermes_cli.gateway_client import GatewayClientError
    agent = agent_with_rpc()
    snapshot = {"session_id": "s", "revision": 1, "execution_generation": 0}
    refusal = {"status": "confirmation_required", "confirm": "token",
               "confirm_message": "Warning"}
    agent._gateway.rpc.side_effect = [
        snapshot, refusal, GatewayClientError("lost reply"), {"status": "applied"}, snapshot]
    agent._conn.request_permission.return_value = SimpleNamespace(
        outcome=AllowedOutcome(outcome="selected", option_id="allow_once"))
    with pytest.raises(GatewayClientError, match="lost reply"):
        await agent.set_session_model("target", "s")
    await agent.set_session_model("target", "s")
    mutations = [call.kwargs for call in agent._gateway.rpc.await_args_list if call.args[0] == "session.mutate"]
    assert mutations[1] == mutations[2]
    agent._conn.request_permission.assert_awaited_once()
    assert not agent._mutations.pending


@pytest.mark.asyncio
async def test_guard_without_editor_returns_defined_refusal():
    from hermes_cli.gateway_client import GatewayClientError
    agent = agent_with_rpc()
    agent._conn = None
    agent._gateway.rpc.side_effect = [
        {"revision": 1, "execution_generation": 0},
        {"status": "confirmation_required", "confirm": "token", "confirm_message": "Warning"}]
    with pytest.raises(GatewayClientError, match="model_confirmation_unavailable"):
        await agent.set_session_model("target", "s")
    assert not agent._mutations.pending
