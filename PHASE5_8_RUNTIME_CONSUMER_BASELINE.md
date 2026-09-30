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
