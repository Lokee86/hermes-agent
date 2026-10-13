"""Transport-only cron execution; output/delivery remain with the firing scheduler."""
import asyncio
import hashlib
import json
import uuid


class CronExecutionUnknown(RuntimeError):
    """The owner may have accepted this fire; never book it as failed or re-fire."""


def journal_path(job_id, request_id):
    from hermes_constants import get_hermes_home
    key = hashlib.sha256(json.dumps([job_id, request_id]).encode()).hexdigest()
    return get_hermes_home() / 'cron' / 'admissions' / (key + '.json')


def run_canonical_job(job, *, extra_prompt=None, cancel_event=None, execution_id=None):
    from gateway.session_cron import owner_for_home, operation
    from gateway.client import connect_gateway
    from hermes_constants import get_hermes_home
    from utils import atomic_json_write

    request_id = execution_id or job.get('execution_id')
    if not request_id:
        request_id = uuid.uuid4().hex
        job['execution_id'] = request_id
    params = {'job_id': job['id'], 'request_id': request_id, 'extra_prompt': extra_prompt}
    root = get_hermes_home() / 'cron' / 'admissions'
    journal = journal_path(params['job_id'], params['request_id'])
    record = {'params': params, 'receipt': None}
    if journal.exists():
        record = json.loads(journal.read_text(encoding='utf-8-sig'))
        if record['params'] != params:
            raise CronExecutionUnknown('cron admission identity conflict')
        stored_result = record.get('result')
        if isinstance(stored_result, list) and len(stored_result) == 4:
            return tuple(stored_result)
    attempted = journal.exists()
    owner = owner_for_home(get_hermes_home())

    def save():
        root.mkdir(parents=True, exist_ok=True)
        atomic_json_write(journal, record, mode=0o600)

    async def observe(call):
        nonlocal attempted
        attempted = True
        save()
        try:
            receipt = await call('submit', params)
        except Exception as exc:
            from gateway.client import GatewayRPCError
            if not isinstance(exc, GatewayRPCError):
                raise
            # An explicit owner RPC refusal to submit is definitive: no fire
            # was admitted. Retain its terminal result only while a durable execution row
            # still needs recovery; transport loss and status failures remain unknown.
            error = f'{type(exc).__name__}: {exc}'
            result = (False, f'# Cron Job: {job["id"]} (FAILED)\n\n{error}\n', '', error)
            record['result'] = list(result)
            try:
                from cron.executions import get_execution
                execution = get_execution(params['request_id'])
            except Exception:
                execution = {'status': 'unknown'}
            if execution is None or execution.get('status') in {'completed', 'failed'}:
                journal.unlink(missing_ok=True)
            else:
                save()
            return result
        record['receipt'] = receipt
        save()
        while True:
            if cancel_event is not None and cancel_event.is_set():
                await call('cancel', receipt)
            state = await call('status', receipt)
            if state['status'] == 'terminal':
                job.update(state.get('job_flags') or {})
                return tuple(state['result'])
            if state['status'] == 'unknown':
                raise CronExecutionUnknown('unknown_execution: cron admission was not replayed')
            await asyncio.sleep(.1)

    async def remote():
        async with connect_gateway() as client:
            return await observe(lambda op, data: client.rpc('cron.' + op, **data))

    try:
        if owner is not None:
            authority, loop = owner
            try:
                current = asyncio.get_running_loop()
            except RuntimeError:
                current = None
            if current is loop:
                raise RuntimeError('cron synchronous execution must run off the owner event loop')
            return asyncio.run_coroutine_threadsafe(
                observe(lambda op, data: operation(authority, op, data)), loop).result()
        return asyncio.run(remote())
    except Exception as exc:
        if attempted:
            raise CronExecutionUnknown(f'Cron execution unverified; reconcile {journal}: {exc}') from exc
        error = f'{type(exc).__name__}: {exc}'
        return False, f'# Cron Job: {job["id"]} (FAILED)\n\n{error}\n', '', error

def reconcile_pending(*, allow_connect=True):
    """Observe prepared fires; never submit missing or interrupted work.

    With allow_connect=False, a headless tick leaves durable receipts for the next
    live owner instead of ensuring or spawning a gateway.
    """
    from gateway.session_cron import owner_for_home, operation
    from hermes_constants import get_hermes_home
    from gateway.client import connect_gateway
    from cron.jobs import get_job, pause_job, save_job_output
    from cron.scheduler import (
        _RunDelivery,
        _apply_agent_failure_marker,
        _compose_run_delivery,
        _delivery_lane_value,
        _finish_completed_run,
        _is_cron_silence_response,
        _normalize_deliver_value,
        _resolve_delivery_targets,
    )
    from cron.delivery_queue import enqueue
    from cron.executions import execution_owner_live
    import logging

    root = get_hermes_home() / 'cron' / 'admissions'
    for journal in sorted(root.glob('*.json')):
        try:
            record = json.loads(journal.read_text(encoding='utf-8-sig'))
            params = record['params']
            if journal != journal_path(params['job_id'], params['request_id']):
                raise ValueError('cron journal identity conflict')
            # A still-live firing process owns its journal and terminal tail.
            if execution_owner_live(params['request_id'], params['job_id']):
                continue
            owner = owner_for_home(get_hermes_home())
            if owner is None and not allow_connect:
                continue
            stored_result = record.get('result')
            if isinstance(stored_result, list) and len(stored_result) == 4:
                recovered_job = get_job(params['job_id'])
                if recovered_job is None:
                    from cron.executions import get_execution, recover_receipted_execution
                    success, _output, _answer, error = stored_result
                    settled = recover_receipted_execution(
                        params['request_id'], params['job_id'], success=bool(success), error=error,
                        delivery_outcome='suppressed')
                    current = get_execution(params['request_id'])
                    if settled is not None or current is None or current.get('status') in {'completed', 'failed'}:
                        journal.unlink(missing_ok=True)
                    continue
                state = {'status': 'terminal', 'result': stored_result, 'job': recovered_job}
            else:
                async def observe():
                    if owner is not None:
                        return await operation(owner[0], 'recover', params)
                    async with connect_gateway() as client:
                        return await client.rpc('cron.recover', **params)
                if owner is not None:
                    state = asyncio.run_coroutine_threadsafe(observe(), owner[1]).result(timeout=20)
                else:
                    state = asyncio.run(observe())
            if state['status'] != 'terminal':
                if state['status'] in {'unknown', 'missing'} and record.get('paused_for_status') != state['status']:
                    paused = pause_job(
                        params['job_id'],
                        reason='Canonical cron ' + state['status'] + '; no automatic re-execution')
                    if paused is not None:
                        from utils import atomic_json_write
                        record['paused_for_status'] = state['status']
                        atomic_json_write(journal, record, mode=0o600)
                continue
            success, output, answer, error = state['result']
            job = state['job']
            job['execution_id'] = params['request_id']
            # A live firer owns its own settlement; never duplicate its delivery.
            if execution_owner_live(params['request_id'], job['id']):
                continue
            # Reuse the scheduler's canonical terminal tail. Recovery may save/queue
            # the result again, but jobs.json, the execution ledger, delivery outcome,
            # incidents, and journal removal must settle through one path. If any of
            # that bookkeeping raises, the outer handler leaves this journal in place
            # for the next reconciliation attempt.
            success, error, agent_declared = _apply_agent_failure_marker(
                job, success, error, answer
            )
            d = _RunDelivery(
                job=job,
                success=success,
                error=error,
                agent_declared=agent_declared,
            )
            output_file = save_job_output(job['id'], output)
            (
                content,
                d.blocked_config,
                silent,
                d.incident_acked,
                d.failure_incident_id,
            ) = _compose_run_delivery(
                job,
                success=success,
                error=error,
                final_response=answer,
                output_file=output_file,
            )
            d.should_deliver = (
                bool(content.strip())
                and not silent
                and not (success and _is_cron_silence_response(content))
            )
            if d.should_deliver:
                d.unresolved_origin = (
                    _normalize_deliver_value(
                        _delivery_lane_value(job, for_failure=not d.success)
                    )
                    == 'origin'
                    and not _resolve_delivery_targets(
                        job, for_failure=not d.success
                    )
                )
                if (
                    not d.unresolved_origin
                    and _normalize_deliver_value(
                        _delivery_lane_value(job, for_failure=not d.success)
                    )
                    != 'local'
                ):
                    queued = enqueue(
                        params['request_id'],
                        job,
                        content,
                        for_failure=not d.success,
                    )
                    d.delivery_attempted = True
                    job['last_delivery_queued'] = {
                        'canonical': {
                            'status': queued['status'],
                            'execution_id': params['request_id'],
                        }
                    }
            from cron.scheduler_bookkeeping import fail_empty_response

            fail_empty_response(d, answer)
            _finish_completed_run(d, None, params['request_id'], recovered=True)
        except Exception:
            logging.getLogger(__name__).warning('Cron receipt recovery deferred: %s', journal, exc_info=True)
