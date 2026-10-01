# Phase 5.8 Runtime Consumer Baseline

Base architecture: Phase 5.7 closed at `15e57836d2`.

Phase 5.8.1 is a behavior/dependency baseline only. It does not move production
ownership. Phase 5.8 will hard-cut runtime consumers away from CLI-owned
provider/model helpers and onto the canonical `providers/` and `models/`
domains established in Phases 5.1-5.7.

The baseline was taken from the fresh Lexicon/Arcana snapshot
`sha256:657462de78db0b391dd0fc65b8f2bab81915737642d53a35b2fff2b2190a7c5e`
for `15e57836d2`. Arcana is registered to that snapshot.

## Classification

Every upward provider/model dependency is assigned exactly one primary class:

- **Provider identity/registry** — provider identity, aliases, labels, declared
  provider families and provider registration/discovery facts.
- **Model identity/catalogue** — model membership, static/live catalogues,
  provider/model inventory and catalogue lifecycle/cache state.
- **Metadata/capability** — context windows, reasoning, fast-mode, pricing/free
  classification and provider/model capability facts.
- **Routing** — endpoint/API-mode/runtime-kind interpretation and route/model
  normalization.
- **Selection** — policy choosing a canonical provider/model candidate.
- **Application/presentation** — command parsing, warnings, display text,
  picker presentation and live application orchestration.
- **Credential/persistence** — auth-visible availability and persisted selection
  mechanics. Credential ownership itself remains Phase 6.

The destination column names the final owner, not an interim forwarding shim.
Where the existing implementation still lives under `hermes_cli`, Phase 5.8.2
must move or expose that single implementation below the CLI boundary rather than
copying it.

## Audit scope and counts

The Phase 5.8.1 audit scans executable Python imports plus dynamic module-string
references under:

`agent/`, `gateway/`, `tui_gateway/`, `acp_adapter/`, and `plugins/`.

| Root | References | Static imports | Dynamic references | Files |
| --- | ---: | ---: | ---: | ---: |
| `agent/` | 32 | 30 | 2 | 17 |
| `gateway/` | 21 | 21 | 0 | 9 |
| `tui_gateway/` | 18 | 17 | 1 | 8 |
| `acp_adapter/` | 6 | 6 | 0 | 2 |
| `plugins/` | 13 | 13 | 0 | 10 |
| **Total** | **90** | **87** | **3** | **46** |

The scanned upward namespaces are `hermes_cli.models*`,
`hermes_cli.model_switch*`, `hermes_cli.model_selection_*`,
`hermes_cli.models_validate`, and the runtime catalogue lifecycle surface
`hermes_cli.model_catalog`.

## Runtime dependency manifest

The exhaustive per-consumer manifest is stored in
`PHASE5_8_RUNTIME_DEPENDENCY_MANIFEST.md`. It records all **90** scoped upward
references across **46** runtime files with a primary responsibility class and a
final-owner direction. This baseline remains the source of the classification and
migration rules; the manifest is the execution checklist for 5.8.2-5.8.7.

## Major runtime clusters

The manifest reduces to six migration clusters:

1. **Catalogue access** — `static_provider_model_ids`, live picker discovery,
   catalogue refresh/cache and provider/model grouping still require CLI-owned
   catalogue surfaces. Phase 5.8.2 must expose the existing single catalogue
   authority below the CLI boundary before consumers move.
2. **Startup/effective selection** — gateway/TUI still call
   `resolve_effective_model`, `resolve_startup_model_route`, and CLI
   selection-default adapters. These must become caller-supplied facts into
   `models.selection*`, followed by `providers.routing`.
3. **Live switch application** — gateway, TUI and ACP still call the CLI
   `switch_model` coordinator. Each application surface must own its own live
   state mutation while consuming canonical selection/routing.
4. **Capability leakage** — reasoning, context, fast-mode and provider/model
   capability helpers remain exposed from `hermes_cli.models*`; they belong
   under `models.metadata` or provider-specific capability sources.
5. **Provider/routing leakage** — OpenCode normalization/family, API mode,
   provider labels and provider lists remain exposed through CLI modules; these
   resolve to `providers.identity`, `providers.registry`,
   `providers.model_normalizers` and `providers.routing`.
6. **Presentation/persistence leakage** — warning, command parsing, display and
   persisted-selection helpers are application responsibilities and must move to
   the consuming application or a non-domain shared application helper rather
   than into `models/` or `providers/`.

## Boundary decisions locked for 5.8

1. `hermes_cli` is an application consumer, not a runtime provider/model
   service.
2. Phase 5.8 does not create a runtime model manager, compatibility registry,
   forwarding facade, dual read or synchronized old/new state.
3. Catalogue implementations that still physically live under `hermes_cli`
   move/expose directly to their final lower-domain owner in 5.8.2. The old CLI
   surface is not retained for runtime consumers.
4. Configuration loading may remain where it currently lives, but provider/model
   interpretation after loading flows through canonical domains.
5. Selection chooses a canonical provider/model. Routing determines invocation
   semantics. Runtime/application code satisfies credentials and mutates live
   state. Those responsibilities remain distinct.
6. Credential acquisition, OAuth/token refresh, credential pools and secret
   persistence remain Phase 6. Phase 5.8 only removes provider/model semantic
   ownership from CLI runtime dependencies.
7. Presentation-only grouping, warnings, confirmation and display may remain
   application-owned provided they consume canonical facts and do not recreate
   provider/model truth.
8. Provider plugins may own provider-specific transport/discovery mechanics, but
   normalized provider/model facts have one canonical owner.

## Existing behavior lock

Phase 5.7 closed with the same inherited failure categories recorded before the
selection migration. Its final baseline rerun was:

```text
537 passed, 31 failed in 322.04s
```

The 31 deterministic failures are:

1. **Alias/provider detection — 1**
   - short alias `sonnet` resolves to `copilot` instead of the legacy test's
     expected `anthropic`.
2. **Custom-provider model parsing — 1**
   - comma-chain custom-provider model parsing.
3. **Nous silent-default policy — 2**
   - hidden-model default and unrestricted-org expectations.
4. **Auxiliary main-first routing — 4**
   - Copilot vision/text header cases and custom endpoint forwarding cases.
5. **Actual/ACI routing and setup — 23**
   - runtime transition matrix, provider/base-URL setup matrix and key-reload
     endpoint persistence.

The Phase 5.7 closeout also recorded a focused picker/runtime gate of
`48 passed, 4 inherited failures` caused by the existing gateway picker
`get_label` import defect, plus an inherited Copilot same-provider API-mode
failure outside selection ownership.

The Phase 5.8.1 rerun of the same representative baseline is recorded below.
No production or test-code change is part of 5.8.1, so any difference from the
Phase 5.7 closeout would block 5.8.2.

## Focused baseline command

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

**Phase 5.8.1 rerun:** **537 passed, 31 failed in 269.73s**. The failure list
and category counts exactly match the Phase 5.7 closeout baseline; no new
Phase 5.8.1 failure category was introduced.

## Phase 5.8.1 acceptance rule

- The migration base is frozen at `15e57836d2`.
- Every upward dependency in the five scoped runtime roots is represented above
  with a primary responsibility class and final-owner direction.
- Existing representative behavior is rerun and inherited failures are recorded.
- No provider/model production ownership moves in this sub-phase.
- No compatibility layer is introduced.
- Phase 5.8.2 may close the lower-domain API gaps without reopening ownership
  discovery.

## Phase 5.8.2 closeout — runtime query ownership

Phase 5.8.2 closes the shared lower-domain query gaps needed by the later
consumer-migration sub-phases. It does not migrate the application coordinators
scheduled for 5.8.3-5.8.7.

Ownership changes:

- Static model catalogue policy moved from `hermes_cli.models_catalog_static`
  to `models.catalog_static`; the old owner is deleted.
- Display-only provider grouping moved separately to
  `hermes_cli.provider_groups`, keeping presentation out of the model domain.
- Codex curated/forward-compatible catalogue policy moved to
  `models.codex_catalog`; `hermes_cli.codex_models` retains live
  credential/runtime discovery and consumes the lower policy.
- models.dev disk-cache, ETag, validation and quarantine ownership moved to
  `models.models_dev_cache`; `agent.models_dev` retains network refresh and
  in-process lifecycle state.
- Fast-mode capability/override queries moved to
  `models.metadata.fast_mode`.
- Shared reasoning-effort clamping and Astra identity moved to
  `models.metadata.reasoning`; GitHub/Copilot reasoning capability queries
  moved to `models.metadata.github`.
- Pure Ollama catalogue classification moved to `models.catalog_local`;
  configuration lookup and live probing remain application/runtime mechanics.
- OpenCode family/model/base-URL interpretation is exposed from `providers`
  and runtime consumers no longer require the CLI model module for it.
- `tests/models/test_runtime_query_boundary.py` locks the lower modules
  against upward imports, duplicate CLI ownership, and restoration of the old
  static-catalogue owner.

Verification:

- Catalogue/Codex focused gate: **67 passed**.
- Fast-mode/reasoning/runtime focused gate: **93 passed**.
- models.dev cache gate: **76 passed**.
- Runtime-query/provider/ACP boundary gate: **25 passed**, 2 inherited warnings.
- Targeted `py_compile`, `ruff check`, and `git diff --check`: clean.
- Original Phase 5.8 representative baseline: **537 passed, 31 failed in
  214.95s**. The failure count and categories exactly match the 5.8.1 inherited
  baseline; no new failure category was introduced.

The remaining upward dependencies in the Phase 5.8 manifest are consumer
migration work for 5.8.3-5.8.7, not duplicate owners for the shared query
surfaces closed here.

## Phase 5.8.3 closeout — agent init and primary client lifecycle

Phase 5.8.3 hard-cuts the primary agent/runtime path away from CLI-owned
provider/model semantics. Configuration loading, authentication, persistence,
plugin dispatch, and other application mechanics remain application-owned;
provider/model interpretation now flows through the canonical lower domains.

Ownership changes:

- Canonical route URL normalization and Actual-route identity moved to
  `providers.route_identity`; primary runtime and client-lifecycle consumers
  no longer import those facts from `hermes_cli`.
- External-process runtime classification is owned by `providers.routing`.
  Agent initialization consumes that query directly rather than the CLI runtime
  backend helper.
- GitHub Copilot transport-header policy moved to `providers.github`.
  Authentication/token exchange remains in `hermes_cli.copilot_auth`.
- The Nous Hermes 3/4 suitability warning moved to
  `agent.model_warnings`, separating application warning/presentation policy
  from the CLI model-switch coordinator.
- GitHub Copilot live catalogue acquisition moved to
  `models.catalog_github`; account-scoped context-window interpretation moved
  to `models.metadata.github`.
- LM Studio reasoning-option and Ollama thinking-capability probes moved to
  `models.metadata.local`; runtime reasoning consumers no longer depend on
  `hermes_cli.models_local` for capability truth.
- The historical runtime identity `openai` now obtains direct-API endpoint and
  API-mode facts from the canonical `openai-api` provider profile without
  rewriting the runtime identity.
- Primary runtime consumers in `agent_init.py`,
  `agent_runtime_helpers.py`, `client_lifecycle.py`,
  `chat_completion_helpers.py`, `fast_mode.py`, `reasoning_params.py`,
  `model_metadata.py`, `models_dev.py`, `opencode_affinity.py`, and
  `agent/transports/*.py` have no dependency on
  `hermes_cli.models*`, `hermes_cli.model_switch*`,
  `hermes_cli.model_selection*`, `hermes_cli.models_validate`, or
  `hermes_cli.model_catalog`.
- No forwarding façade was retained for the newly moved GitHub catalogue/context
  surfaces; remaining application consumers import their lower owner directly.

Verification:

- Targeted `py_compile`, `ruff check`, and `git diff --check`: clean.
- Primary runtime ownership grep: zero scoped upward model-semantic references.
- Focused runtime/ownership gate before final façade cleanup:
  **137 passed, 2 skipped, 2 failed**. Both failures are the already-recorded
  Copilot cases in the inherited **Auxiliary main-first routing** category; no
  new focused failure remained.
- Provider-routing regression for historical `openai` identity:
  **11 passed** including the previously failing cross-provider switch case.

Phase 5.8.3 does not claim auxiliary runtime ownership; the inherited Copilot
auxiliary failures and the broader auxiliary migration remain Phase 5.8.4 work.

## Phase 5.8.4 closeout — auxiliary runtime hard cut

Phase 5.8.4 hard-cuts auxiliary model/provider semantics away from CLI-owned
selection and routing authority while keeping auxiliary orchestration,
credential acquisition, retries, health/quarantine, and transport construction
application-owned.

Ownership changes:

- Auxiliary model selection consumes `models.selection_auxiliary`; the old
  `hermes_cli.model_selection_auxiliary` owner is deleted.
- Configured-provider matching, custom-provider identity, direct-API aliases,
  and custom-resolution semantics are owned by `providers.configured`.
  `agent.configured_provider_resolution` only acquires already-loaded
  application config facts.
- Copilot auxiliary transport/header behavior consumes
  `providers.github.copilot_request_headers`; GitHub token acquisition remains
  application-owned.
- The main-session runtime route is authoritative for auxiliary main-first
  resolution. Provider/model/base URL/API mode facts are projected through
  canonical lower-domain routing rather than reconstructed from CLI helpers.
- Vision defaults/rejection are provider-profile facts; model image capability
  comes from `models.metadata`; vision-model precedence comes from
  `models.selection_auxiliary`.
- Nous auxiliary recommendation semantics are provider-owned via
  `providers.nous_recommendations`; the obsolete CLI recommendation selector is
  removed.
- Fallback route interpretation is centralized in `agent.fallback_routing`,
  which acquires application config facts then delegates provider/base/API-mode
  semantics to `providers.routing`. Main-agent and auxiliary fallback consumers
  share this route owner.
- Actual route protocol mandate is lower-owned by `providers.routing`.
- Auxiliary unhealthy-route identity uses canonical provider identity while
  custom routes remain endpoint-scoped.
- No auxiliary runtime consumer imports
  `hermes_cli.model_selection_auxiliary`, `hermes_cli.model_switch*`,
  `hermes_cli.model_selection*`, `hermes_cli.models_validate`,
  `hermes_cli.model_catalog`, or `hermes_cli.runtime_provider_custom`.

Phase 6 boundary retained:

- Credential acquisition, OAuth/token refresh, pools, secrets, and
  provider-specific auth/runtime assembly remain application-owned.
- `agent.auxiliary_client` has exactly two permitted
  `hermes_cli.runtime_provider` imports, frozen by the architecture gate:
  bare-custom runtime acquisition and Azure Foundry auth/runtime acquisition.
  These are application mechanics, not new semantic-owner surfaces, and are
  deferred to Phase 6 rather than hidden behind a forwarding façade.

Architecture gates:

- `tests/models/test_runtime_query_boundary.py` now locks the complete
  auxiliary semantic boundary, the final lower owners, canonical fallback
  routing, and the exact Phase-6 acquisition exceptions.
- The gate rejects reintroduction of CLI selection/custom-provider authority or
  new `runtime_provider` imports in the auxiliary runtime surface.

Verification:

- Final ownership gate: **14 passed**.
- Selection/capability/vision closeout set: **51 passed**.
- Main-first/custom/OpenCode/Copilot/Azure closeout set: **73 passed**.
- Fallback/routing/health/provider-parity closeout set: **102 passed**.
- Total focused 5.8.4 closeout verification: **240 passed**.
- `ruff check` and `git diff --check`: clean.

Phase 5.8.4 is closed. Gateway/session runtime migration remains Phase 5.8.5;
TUI/web/ACP remains 5.8.6; provider/plugin/environment policy remains 5.8.7.
