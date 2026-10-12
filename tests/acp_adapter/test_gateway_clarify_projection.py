"""ACP forwards canonical clarify prompts without turning detach into denial."""
import asyncio
from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest

from acp_adapter.gateway_server import GatewayACPAgent


@pytest.mark.asyncio
async def test_clarify_permission_card_answers_exact_generation():
    from acp.schema import AllowedOutcome
    agent = GatewayACPAgent()
    agent._conn = AsyncMock()
    agent._conn.request_permission.return_value = SimpleNamespace(
        outcome=AllowedOutcome(outcome='selected', option_id='choice-1'))
    agent._gateway = AsyncMock()
    prompt = {'kind': 'clarify', 'prompt_id': 'q', 'execution_generation': 7,
              'question': 'Pick a color', 'choices': ['red', 'green']}
    agent._permission('s', prompt)
    await agent._permissions[('s', 'q', 7)]
    agent._gateway.rpc.assert_awaited_once_with(
        'clarify.respond', session_id='s', prompt_id='q', execution_generation=7, answer='green')


@pytest.mark.asyncio
async def test_clarify_form_answers_and_settlement_cancels_viewer():
    agent = GatewayACPAgent()
    agent._form_elicitation = True
    agent._conn = AsyncMock()
    agent._conn.send_request.return_value = {'action': 'accept', 'content': {'answer': 'green'}}
    agent._gateway = AsyncMock()
    agent._snapshots['s'] = {}
    prompt = {'kind': 'clarify', 'prompt_id': 'q', 'execution_generation': 5,
              'question': 'Pick a color', 'choices': ['red', 'green']}
    await agent._project({'session_id': 's', 'type': 'clarify.request', 'payload': prompt})
    await agent._permissions[('s', 'q', 5)]
    args = agent._conn.send_request.await_args
    assert args.args[0] == 'elicitation/create'
    assert args.args[1]['requestedSchema']['properties']['answer']['enum'] == ['red', 'green']
    agent._gateway.rpc.assert_awaited_once_with(
        'clarify.respond', session_id='s', prompt_id='q', execution_generation=5, answer='green')
    await agent._project({'session_id': 's', 'type': 'clarify.settled',
                          'payload': {'prompt_id': 'q', 'execution_generation': 5}})
    assert ('s', 'q', 5) not in agent._permissions