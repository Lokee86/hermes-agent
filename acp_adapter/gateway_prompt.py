"""ACP prompt admission and command adaptation; execution stays in the gateway."""
import json
import uuid
from functools import partial

import acp
from acp.schema import PromptResponse
from hermes_cli.gateway_client import GatewayClientError, GatewayRPCError
from acp_adapter.gateway_model_confirmation import confirm_model
from acp_adapter.gateway_server import _stage_user_content


def prepare_input(agent, session_id, content):
    fingerprint = json.dumps(content, sort_keys=True)
    attempt = agent._inputs.get(session_id)
    if attempt is not None and attempt["fingerprint"] != fingerprint:
        raise GatewayClientError("unacknowledged_input_pending: retry the previous prompt first")
    if session_id in agent._submitting or session_id in agent._admissions:
        raise GatewayClientError("session_busy")
    if attempt is None:
        text, attachments = _stage_user_content(content)
        submit = {"text": text}
        if attachments:
            submit["attachments"] = attachments
        attempt = {"fingerprint": fingerprint, "input_id": uuid.uuid4().hex, "submit": submit}
    return attempt


async def slash_prompt(agent, session_id, command, arg):
    from hermes_cli.gateway_mutations import slash_mutation
    operation, payload = slash_mutation(command.name, arg)
    if operation == "branch":
        raise GatewayClientError("use_acp_fork_session")
    client = await agent._client()
    result = await agent._mutations.apply(client, session_id, operation, payload,
        confirm=partial(confirm_model, agent, session_id))
    if result.get("status") == "cancelled":
        return PromptResponse(stop_reason="cancelled")
    if result.get("status") == "preview":
        await agent._conn.session_update(session_id=agent._editor_id(session_id),
            update=acp.update_agent_message_text("\n".join(result["lines"]) + "\n"))
    else:
        agent._snapshots[session_id] = await client.rpc("session.resume", session_id=session_id)
    agent._mutations.acknowledge(session_id, operation, payload)
    return PromptResponse(stop_reason="end_turn")


async def submit_input(agent, client, session_id, attempt):
    agent._inputs[session_id] = attempt
    agent._submitting.add(session_id)
    try:
        if "receipt" in attempt:
            receipt = await client.rpc("prompt.receipt", session_id=session_id,
                admission_id=attempt["receipt"]["admission_id"], include_result=True)
        else:
            receipt = await client.rpc("prompt.submit", session_id=session_id,
                input_id=attempt["input_id"], **attempt["submit"])
        attempt["receipt"] = receipt
        return receipt
    except BaseException as exc:
        agent._pending_cancels.discard(session_id)
        if isinstance(exc, GatewayRPCError) and str(exc) in {
                "invalid_params", "permission_denied", "not_found", "profile_mismatch"}:
            agent._inputs.pop(session_id, None)
        raise
    finally:
        agent._submitting.discard(session_id)


async def settled_result(agent, client, session_id, receipt):
    admission_id = receipt["admission_id"]
    terminal = agent._terminals.pop(admission_id, None)
    if terminal is None:
        settled = receipt if "result" in receipt else await client.rpc("prompt.receipt",
            session_id=session_id, admission_id=admission_id, include_result=True)
        terminal = {"outcome": settled.get("outcome"),
                    "text": (settled.get("result") or {}).get("final_response") or ""}
        await agent._project({"session_id": session_id, "admission_id": admission_id,
                             "type": "message.complete", "payload": terminal})
        agent._terminals.pop(admission_id, None)
    return terminal


async def wait_for_result(agent, session_id, admission_id):
    if session_id in agent._pending_cancels:
        agent._pending_cancels.discard(session_id)
        await agent._cancel_admission(session_id, admission_id)
    async with agent._changed:
        await agent._changed.wait_for(lambda: admission_id in agent._terminals or agent._failure is not None
            or any(p.get("status") == "unknown" for p in agent._snapshots.get(session_id, {}).get("pending", [])))
        # A committed result for this admission is authoritative even if a
        # different turn becomes unknown or the transport closes in the same wakeup.
        if admission_id in agent._terminals:
            return agent._terminals.pop(admission_id)
        if agent._failure:
            raise agent._failure
        unknown = next((p for p in agent._snapshots.get(session_id, {}).get("pending", [])
                        if p.get("status") == "unknown"), None)
        if unknown is not None:
            raise GatewayClientError(agent._unknown_recovery(session_id, unknown["admission_id"]))
        return agent._terminals.pop(admission_id)


def finish_prompt(agent, session_id, admission_id, terminal):
    outcome = terminal.get("outcome")
    if outcome == "unknown":
        raise GatewayClientError(agent._unknown_recovery(session_id, admission_id))
    agent._inputs.pop(session_id, None)
    if outcome == "failed":
        raise GatewayClientError("admitted_turn_failed")
    return PromptResponse(stop_reason="cancelled" if outcome in {"cancelled", "interrupted"} else "end_turn")


async def prompt(agent, prompt, session_id, **kwargs):
    session_id = agent._aliases.get(session_id, session_id)
    if session_id not in agent._snapshots and session_id not in agent._inputs:
        raise GatewayClientError("not_found")
    unknown = next((p for p in agent._snapshots.get(session_id, {}).get("pending", [])
                    if p.get("status") == "unknown"), None)
    if unknown is not None and session_id not in agent._inputs:
        raise GatewayClientError(agent._unknown_recovery(session_id, unknown["admission_id"], unsent=True))
    from acp_adapter.content import _content_blocks_to_openai_user_content
    attempt = prepare_input(agent, session_id, _content_blocks_to_openai_user_content(prompt))
    text = attempt["submit"]["text"]
    parts = text.strip().split(None, 1)
    from hermes_cli.commands import resolve_command
    command = resolve_command(parts[0]) if parts and text.lstrip().startswith("/") and not attempt["submit"].get("attachments") else None
    if command is not None:
        return await slash_prompt(agent, session_id, command, parts[1] if len(parts) > 1 else "")
    client = await agent._client(reconnect=True)
    if session_id not in agent._snapshots:
        # Restore the viewer without changing the retained submission identity.
        agent._snapshots[session_id] = await client.rpc("session.resume", session_id=session_id)
    receipt = await submit_input(agent, client, session_id, attempt)
    admission_id = receipt["admission_id"]
    agent._admissions[session_id] = admission_id
    try:
        if receipt.get("status") == "terminal":
            terminal = await settled_result(agent, client, session_id, receipt)
        elif receipt.get("status") == "unknown":
            raise GatewayClientError(agent._unknown_recovery(session_id, admission_id))
        else:
            terminal = await wait_for_result(agent, session_id, admission_id)
        return finish_prompt(agent, session_id, admission_id, terminal)
    finally:
        if agent._admissions.get(session_id) == admission_id:
            agent._admissions.pop(session_id, None)
