"""ACP permission card for an authority-guarded model change."""
import uuid
import acp
from acp.schema import AllowedOutcome, PermissionOption
from hermes_cli.gateway_client import GatewayClientError
from hermes_cli.gateway_mutations import confirmation_title


async def confirm_model(agent, session_id, refusal):
    if agent._conn is None:
        raise GatewayClientError("model_confirmation_unavailable")
    card = acp.update_tool_call("model-confirm-" + uuid.uuid4().hex,
        title=confirmation_title(refusal), kind="other", status="pending",
        content=[acp.tool_content(acp.text_block(refusal["confirm_message"]))])
    options = [PermissionOption(option_id="allow_once", kind="allow_once", name="Switch anyway"),
               PermissionOption(option_id="deny", kind="reject_once", name="Cancel")]
    response = await agent._conn.request_permission(
        session_id=agent._editor_id(session_id), tool_call=card, options=options)
    accepted = isinstance(response.outcome, AllowedOutcome) and response.outcome.option_id == "allow_once"
    await agent._conn.session_update(session_id=agent._editor_id(session_id),
        update=acp.update_tool_call(card.tool_call_id, status="completed" if accepted else "failed"))
    return accepted
