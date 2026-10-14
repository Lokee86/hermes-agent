"""ACP completion ordering and streaming memory contracts."""
import asyncio
import tracemalloc
from types import SimpleNamespace
from unittest.mock import AsyncMock

import acp
import pytest

from acp_adapter.gateway_server import GatewayACPAgent
from hermes_cli.gateway_client import GatewayClientError


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["completed", "cancelled", "failed", "unknown"])
async def test_own_terminal_wins_over_unrelated_unknown_in_same_wakeup(outcome):
    agent = GatewayACPAgent()
    agent._snapshots["s"] = {}
    agent._gateway = SimpleNamespace(rpc=AsyncMock())
    async def submit(method, **params):
        assert method == "prompt.submit"
        # Both frames arrive before the prompt can resume from its submit reply.
        await agent._project({"session_id": "s", "type": "message.complete",
            "admission_id": "ours", "payload": {"outcome": outcome, "text": ""}})
        await agent._project({"session_id": "s", "type": "session.info",
            "payload": {"pending": [{"admission_id": "other", "status": "unknown"}]}})
        return {"admission_id": "ours"}
    agent._gateway.rpc.side_effect = submit
    if outcome in {"failed", "unknown"}:
        reason = "^admitted_turn_failed$" if outcome == "failed" else "unknown_execution.*?/discard ours"
        with pytest.raises(GatewayClientError, match=reason):
            await asyncio.wait_for(agent.prompt([acp.text_block("work")], "s"), 5)
    else:
        response = await asyncio.wait_for(agent.prompt([acp.text_block("work")], "s"), 5)
        assert response.stop_reason == ("cancelled" if outcome == "cancelled" else "end_turn")
    assert bool(agent._inputs) == (outcome == "unknown")
    assert not agent._admissions


@pytest.mark.asyncio
async def test_long_stream_retains_linear_text_and_suppresses_reused_completion():
    agent = GatewayACPAgent()
    delivered = []
    async def update(session_id, update):
        text = getattr(getattr(update, "content", None), "text", None)
        if text is not None:
            delivered.append(len(text))
    agent._conn = SimpleNamespace(session_update=update)
    agent._snapshots["s"] = {}
    chunk, count = "x" * 64, 2048
    # Warm projection imports before measuring state retained by the stream.
    await agent._project({"session_id": "s", "type": "message.delta", "admission_id": "warm",
        "payload": {"text": "warm"}})
    await agent._project({"session_id": "s", "type": "message.complete", "admission_id": "warm",
        "payload": {"outcome": "completed", "text": "warm"}})
    delivered.clear()
    tracemalloc.start()
    try:
        start = tracemalloc.get_traced_memory()[0]
        for _ in range(count):
            await agent._project({"session_id": "s", "type": "message.delta", "admission_id": "ours",
                "payload": {"text": chunk}})
        retained = tracemalloc.get_traced_memory()[0] - start
        # Linear output state, with slack for Python/SDK allocations. Retaining every
        # cumulative prefix instead takes roughly 128 MiB for this 128 KiB stream.
        assert retained < count * len(chunk) * 8 + 1_000_000, retained
        await agent._project({"session_id": "s", "type": "tool.start", "admission_id": "ours",
            "payload": {"tool_call_id": "housekeeping", "tool_name": "memory", "args": {}}})
        await agent._project({"session_id": "s", "type": "message.complete", "admission_id": "ours",
            "payload": {"outcome": "completed", "text": chunk * count, "response_reused": True}})
        assert sum(delivered) == count * len(chunk)
        assert not agent._streamed and not agent._delivered
    finally:
        tracemalloc.stop()


@pytest.mark.asyncio
async def test_latest_interim_is_deduplicated_without_hiding_a_new_final():
    agent = GatewayACPAgent()
    agent._conn = AsyncMock()
    agent._snapshots["s"] = {}
    for kind, payload in [
        ("message.interim", {"text": "commentary"}),
        ("message.interim", {"text": "answer"}),
        ("message.complete", {"text": "answer", "outcome": "completed"})]:
        await agent._project({"session_id": "s", "admission_id": "ours", "type": kind, "payload": payload})
    texts = [call.kwargs["update"].content.text for call in agent._conn.session_update.await_args_list]
    assert texts == ["commentary", "answer"]
