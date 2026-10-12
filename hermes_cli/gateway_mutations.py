"""Prepared native controls retain their identity across ambiguous RPC replies."""
import json
import uuid
from gateway.client import GatewayClientError


class PreparedMutations:
    def __init__(self):
        self.pending = {}

    async def apply(self, client, session_id, operation, payload, *, confirm=None):
        encoded = json.dumps(payload, sort_keys=True)
        key = (session_id, operation, encoded)
        if key not in self.pending:
            snapshot = await client.rpc('session.resume', session_id=session_id)
            self.pending[key] = {'params': dict(session_id=session_id, operation=operation,
                payload=json.loads(encoded), request_id=uuid.uuid4().hex,
                expected_revision=snapshot['revision'], expected_generation=snapshot['execution_generation'])}
        entry = self.pending[key]
        if 'result' not in entry:
            try:
                entry['result'] = await client.rpc('session.mutate', **entry['params'])
            except GatewayClientError as exc:
                # A disconnect is not a definitive authority refusal. Preserve
                # the tuple; never refresh its preconditions behind the user.
                if str(exc) in {'invalid_params', 'revision_conflict', 'stale_generation',
                                'session_busy', 'unknown_execution', 'permission_denied',
                                'model_resolution_failed', 'nothing_to_compress',
                                'unsupported_compress_options'}:
                    self.pending.pop(key)
                raise
        result = entry['result']
        if result.get('status') == 'confirmation_required':
            if confirm is None:
                raise GatewayClientError(result.get('confirm_message') or 'confirmation_required')
            if not await confirm(result):
                self.pending.pop(key, None)
                return {'status': 'cancelled'}
            # The owner's confirmation token is scoped to the retained snapshot and
            # original request identity; do not refresh revision/generation here.
            params = dict(entry['params'])
            params['payload'] = {**params['payload'], 'confirm': result['confirm']}
            try:
                confirmed = await client.rpc('session.mutate', **params)
            except GatewayClientError as exc:
                if str(exc) in {'invalid_params', 'revision_conflict', 'stale_generation',
                                'session_busy', 'unknown_execution', 'permission_denied',
                                'model_resolution_failed', 'nothing_to_compress',
                                'unsupported_compress_options'}:
                    self.pending.pop(key, None)
                raise
            entry['result'] = confirmed
            return confirmed
        return result

    def acknowledge(self, session_id, operation, payload):
        self.pending.pop((session_id, operation, json.dumps(payload, sort_keys=True)), None)


def confirmation_title(refusal):
    """Human-readable label for the owner\'s guarded model-switch refusal."""
    warnings = refusal.get("warnings") or []
    return " / ".join(str(w.get("title")) for w in warnings if w.get("title")) or "Confirm model switch"


def confirm_choice(raw, choices):
    """Resolve an explicit menu choice; ambiguous input always cancels."""
    answer = str(raw or "").strip().lower()
    if answer in {"y", "yes"}:
        return choices[0][0]
    if answer in {"n", "no"}:
        return "cancel"
    for index, (key, label, *_rest) in enumerate(choices, 1):
        if answer in {str(index), str(key).lower(), str(label).strip().lower()}:
            return key
    return "cancel"


def compress_payload(arg):
    """Structured ``session.mutate(compress)`` payload from the raw ``/compress`` arguments.

    The shared parser is the one every native surface uses, so ``--preview`` stays a read-only
    flag and ``here [N]`` a boundary instead of becoming a focus topic; ``--aggressive`` has no
    canonical implementation and is refused before anything reaches the authority.
    """
    from agent.conversation_compression_manual import AGGRESSIVE_UNSUPPORTED, parse_compress_args
    request = parse_compress_args(arg)
    if request.aggressive:
        raise GatewayClientError(AGGRESSIVE_UNSUPPORTED)
    payload = {}
    if request.focus_topic:
        payload['focus'] = request.focus_topic
    if request.preview:
        payload['preview'] = True
    if request.partial:
        payload.update(partial=True, keep_last=request.keep_last)
    return payload


def slash_mutation(command, arg):
    name = command.lstrip('/')
    if name == 'model':
        from hermes_cli.model_switch import parse_model_flags_detailed
        parsed = parse_model_flags_detailed(arg)
        if parsed.is_global or parsed.is_once or parsed.force_refresh or not parsed.model_input:
            raise GatewayClientError('unsupported_model_options')
        return name, {'model': parsed.model_input, **(
            {'provider': parsed.explicit_provider} if parsed.explicit_provider else {})}
    if name == 'compress':
        return name, compress_payload(arg)
    if name != 'branch':
        raise GatewayClientError('unsupported_command')
    return name, {'title': arg} if arg else {}
