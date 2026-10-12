"""Callable rewind payloads preserve a single resume/CAS identity."""
import pytest
from gateway.client import GatewayClientError
from hermes_cli.gateway_mutations import PreparedMutations
from hermes_cli.gateway_chat_commands import _rewind_to


class Client:
    def __init__(self, ambiguous=False, messages=None):
        self.calls = []
        self.ambiguous = ambiguous
        self.messages = messages if messages is not None else []

    async def rpc(self, method, **params):
        self.calls.append((method, params.copy()))
        if method == 'session.resume':
            return {'revision': 7, 'execution_generation': 3, 'messages': self.messages}
        if self.ambiguous:
            self.ambiguous = False
            raise GatewayClientError('connection_closed')
        return {'status': 'applied', 'rewound_count': 1}


@pytest.mark.asyncio
async def test_callable_retry_preserves_request_id_and_snapshot():
    client = Client(True, [{'row_id': 11, 'role': 'user', 'content': 'hello'}])
    mutations = PreparedMutations()
    with pytest.raises(GatewayClientError, match='connection_closed'):
        await mutations.apply(client, 's', 'rewind', _rewind_to(1))
    result = await mutations.apply(client, 's', 'rewind', _rewind_to(1))
    assert result['status'] == 'applied'
    assert [name for name, _ in client.calls].count('session.resume') == 1
    sent = [params for name, params in client.calls if name == 'session.mutate']
    assert len(sent) == 2 and sent[0] == sent[1]
    assert sent[0]['expected_revision'] == 7
    assert sent[0]['expected_generation'] == 3
    assert sent[0]['payload'] == {'target_message_id': 11}
    mutations.acknowledge('s', 'rewind', _rewind_to(1))
    assert not mutations.pending


@pytest.mark.asyncio
async def test_callable_with_no_matching_turn_never_mutates():
    client = Client()
    result = await PreparedMutations().apply(client, 's', 'rewind', _rewind_to(1))
    assert result == {'status': 'nothing'}
    assert [name for name, _ in client.calls] == ['session.resume']
