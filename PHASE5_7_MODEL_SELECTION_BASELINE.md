# Phase 5.7 Model Selection Baseline

Base architecture: Phase 5.6 closed at `e2cb59b136`.

Phase 5.7.1 is a behavior/classification baseline only. It does not introduce the
future `models.selection` owner or migrate production callers.

## Classification

The migration uses four responsibility classes:

- **Domain mechanics** — canonical provider/model identity, catalogue membership,
  metadata/capability lookup, and route interpretation.
- **Selection policy** — which valid provider/model candidate should be chosen for
  a specific purpose.
- **Credential/runtime mechanics** — availability, credentials, health, client
  construction, validation, fallback execution, and persistence.
- **Presentation/apply** — picker rendering, warnings, confirmation, display,
  mutation of live CLI state, and user-facing errors.

## Current selection owners

| Surface | Current decision sites | Classification | Phase 5.7 destination |
| --- | --- | --- | --- |
| Explicit/startup switch | `hermes_cli/model_switch.py::resolve_startup_model_route`, `resolve_alias`, configured/current/aggregator matching, `switch_model` | Domain mechanics + selection policy mixed with credentials/runtime and apply | Canonical selection mechanics/policy move to `models.selection`; credentials, validation, persistence and display remain downstream |
| Default/silent selection | `hermes_cli/models.py::get_preferred_silent_default_model`, `pick_silent_default_model`, `recommended_nous_default_model`, provider default helpers | Selection policy over catalogue/account facts | Default policy over the canonical model universe; Portal/account discovery remains outside |
| Setup/auth picker | `hermes_cli/auth_model_picker.py`, auth/setup provider gates | Selection policy + credential availability + presentation | Candidate eligibility consumes canonical selection/query output; auth state and UI remain outside |
| CLI /model picker | `hermes_cli/cli_model_switch_mixin.py::_handle_model_picker_selection`, `_handle_model_switch` | Selection policy + presentation + runtime apply | Candidate/model interpretation consumes selection seam; picker state/rendering/apply remain here |
| Shared inventory | `hermes_cli/inventory.py` picker/setup projections | Domain aggregation + selection policy + credential visibility | Provider/model truth remains derived from existing owners; selection-specific eligibility moves to shared selection policy |
| Auxiliary model choice | `agent/auxiliary_client.py::_get_auxiliary_task_config`, `_fast_model_from_catalog`, `_get_aux_model_for_provider`, `_main_route_target` | Selection policy | Auxiliary/fast/vision policies consume canonical candidates |
| Auxiliary automatic routing | `agent/auxiliary_client.py::_resolve_auto_route` | Selection policy mixed with runtime availability | Model/provider preference moves to selection policy; credential/health/runtime availability stays downstream |
| Auxiliary client resolution | `agent/auxiliary_client.py::resolve_provider_client` | Credential/runtime mechanics; some residual model fallback choice | Runtime resolver consumes a model selection; credential/client construction stays here |
| Auxiliary health/fallback | `agent/auxiliary_health.py`, `auxiliary_fallback_recovery.py`, `call_llm`, `async_call_llm` | Credential/runtime mechanics | Remains downstream; selection does not own runtime failure recovery |
| Selection warnings | `hermes_cli/model_selection_guards.py` | Presentation/apply | Remains post-selection |
| ACP/runtime consumers | ACP model switch/catalog and live agent `switch_model` paths | Runtime application | Consume canonical selection after Phase 5.7/5.8 cutover |

## Key boundary decisions

1. A model-selection result answers **which canonical provider/model should be
   used**. It does not contain or acquire credentials.
2. Provider/model identity, catalogue membership, model metadata/capabilities and
   invocation-route semantics remain owned by the Phase 5.1-5.6 domain modules.
   Phase 5.7 derives candidates from those owners; it does not duplicate them.
3. Credential presence, pool exhaustion, OAuth state, route health and runtime
   failures may make a preferred selection temporarily unsatisfiable, but they
   are not model-domain truth.
4. Picker/setup presentation may sort, group, search, disable and confirm rows,
   but must eventually consume the same canonical candidate universe as
   automatic selection.
5. Auxiliary runtime fallback remains distinct from model-selection policy.
6. No compatibility selection registry, dual read, forwarding wrapper or
   synchronized old/new policy is required for this internal hard cut.

## Existing behavior locks

Representative existing tests already pin the behavior that must survive the
migration:

- `tests/hermes_cli/test_models.py` — Nous/default policy and broad model
  selection behavior.
- `tests/hermes_cli/test_model_alias_credentials.py` — alias/provider identity
  and credential-boundary behavior.
- `tests/hermes_cli/test_model_switch_custom_providers.py` — configured/named
  custom-provider switching.
- `tests/hermes_cli/test_cli_provider_resolution.py` — provider resolution and
  picker/setup integration.
- `tests/hermes_cli/test_nous_policy_surfaces.py` — Nous policy exposure.
- `tests/hermes_cli/test_aux_picker_inventory.py` — shared picker inventory.
- `tests/agent/test_auxiliary_client.py` — default/fast/vision/provider-auto and
  resolver/fallback behavior.
- `tests/agent/test_auxiliary_main_first.py` — main-provider-first text/vision
  policy.
- `tests/agent/test_actual_auxiliary_routing.py` — integrated auxiliary route
  behavior.
- `tests/acp_adapter/test_acp_dashboard_model_switch_validation.py` — ACP switch
  validation/application boundary.

Additional focused coverage already exists for Bedrock region-scoped picker
models, exhausted pools, auto-provider non-guessing, auxiliary multi-hop
fallback, Anthropic pool fallback, one-turn CLI switching, context application,
and named custom providers.

## Contract gaps to close during migration

The following are gaps to make explicit as callers are moved onto the final
selection seam, not reasons to introduce a temporary seam in 5.7.1:

1. Startup, typed `/model`, interactive picker and ACP should produce equivalent
   canonical provider/model identity for equivalent input/context.
2. Explicit provider/model, current session state, configured declarations,
   catalogue defaults and fallback/default policy need one deterministic
   precedence contract.
3. Canonical inventory consumers should agree on model eligibility for the same
   non-presentation context.
4. Failed selection/runtime application must remain atomic: live model, provider,
   endpoint, credentials, reasoning state and persisted config are unchanged.
5. Auxiliary fast/default/vision policy should be testable independently from
   credentials, health and client construction.
6. Sync and async auxiliary fallback should retain equivalent provider/model
   decisions.
7. A preferred but currently unhealthy/uncredentialed route must remain distinct
   from a model being invalid or outside the allowed selection universe.

## Focused pre-migration gate

```text
python -m pytest -q \
  tests/hermes_cli/test_models.py \
  tests/hermes_cli/test_model_alias_credentials.py \
  tests/hermes_cli/test_model_switch_custom_providers.py \
  tests/hermes_cli/test_cli_provider_resolution.py \
  tests/hermes_cli/test_nous_policy_surfaces.py \
  tests/hermes_cli/test_aux_picker_inventory.py \
  tests/agent/test_auxiliary_client.py \
  tests/agent/test_auxiliary_main_first.py \
  tests/agent/test_actual_auxiliary_routing.py \
  tests/acp_adapter/test_acp_dashboard_model_switch_validation.py
```

Result before the selection-ownership migration:

```text
542 passed, 31 failed in 459.69s
```

The deterministic baseline failures are grouped as follows:

1. **Alias/provider detection — 1 failure**
   - `tests/hermes_cli/test_models.py::TestDetectProviderForModel::test_short_alias_resolves_to_static_model`
   - `sonnet` currently resolves to `copilot` instead of the test's expected `anthropic`.
   - Independently reproduced on the untouched Phase 5.6 worktree: **1 failed, 75 passed** for `test_models.py`.

2. **Custom-provider model parsing — 1 failure**
   - `tests/hermes_cli/test_model_switch_custom_providers.py::test_list_splits_comma_chain_custom_provider_model`.

3. **Nous silent-default policy — 2 failures**
   - `TestRecommendedDefaultEndpoint::test_hidden_model_is_never_the_silent_default`.
   - `TestRecommendedDefaultEndpoint::test_unrestricted_org_is_unaffected`.

4. **Auxiliary main-first routing — 4 failures**
   - Copilot vision/text header cases.
   - Custom and `custom:*` main-runtime endpoint forwarding cases.

5. **Actual/ACI routing and setup — 23 failures**
   - The `test_actual_runtime_transitions_reach_chat_completions` init/auto/switch/restore matrix.
   - The `test_actual_setup_keeps_provider_settings_in_yaml` provider/base-URL matrix.
   - `test_actual_key_reload_keeps_yaml_endpoint`.

The Phase 5.7.1 worktree contains no production or test-code changes, so these are
the inherited Phase 5.6 baseline rather than regressions introduced by this
sub-phase. Later 5.7 gates must introduce no additional failures or change these
failure modes unless a migrated selection contract intentionally repairs one and
its expectation is updated in the same sub-phase.

## Phase 5.7.1 acceptance rule

- Every known provider/model choice site is classified above.
- Existing representative behavior is green, or deterministic pre-existing
  failures are recorded here.
- No production selection ownership moves in this sub-phase.
- Phase 5.7.2 may establish the canonical selection contract without reopening
  ownership discovery.
