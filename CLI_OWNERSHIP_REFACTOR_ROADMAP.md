# Hermes CLI Ownership Refactor Roadmap

## Goal

`hermes_cli` has grown beyond a CLI package. It currently owns or hosts runtime infrastructure, profile management, provider/model resolution, Gateway control, Kanban, automation, plugin runtime, storage helpers, and other functionality consumed directly by `gateway/`.

The current inventory finds **290 non-config `gateway -> hermes_cli` import sites**.

This refactor will progressively restore explicit ownership boundaries while introducing **`nous_cli`** as the thin CLI surface.

Target dependency shape:

```text
nous_cli ─────┐
gateway ──────┼──> owned subsystems
agent ────────┘
```

rather than:

```text
gateway ──> hermes_cli ──> application/runtime internals
```

This is a behaviour-preserving architectural refactor delivered incrementally.

## Scope

The migration follows one rule:

> Move functionality to the subsystem that owns it; move only actual CLI parsing, presentation, and command orchestration into `nous_cli`.

`nous_cli` is a strangler surface, not a second implementation of Hermes functionality.

As each area migrates:

1. backing/domain logic moves to its natural owner;
2. Gateway and other runtime consumers are rewired directly to that owner;
3. the corresponding CLI surface moves into `nous_cli`;
4. obsolete `hermes_cli` implementation is deleted.

No permanent compatibility layer is planned for internal imports.

## Config is explicitly excluded

The config subsystem is intentionally out of scope.

PR **#122245** is actively introducing a `ConfigBackend` seam and routing `config.yaml` readers/writers through it. This refactor will not move, restructure, or otherwise interfere with the config family while that work is in flight.

Config ownership can be reassessed separately after #122245 settles.

---

## Phase 0 — Strangler boundary

Establish `nous_cli` as the destination for the final CLI surface.

- create the minimal `nous_cli` package/entry boundary;
- establish one explicit legacy-routing seam for commands not yet migrated;
- add architectural checks preventing newly migrated runtime code from depending back on `hermes_cli`;
- do not duplicate domain implementations.

## Phase 1 — Profiles and profile identity

Move profile-domain behaviour out of `hermes_cli.profiles`.

Includes:

- profile identity and validation;
- profile directory resolution;
- active-profile resolution;
- served-profile enumeration;
- profile existence/liveness;
- profile routing and matching.

This removes the largest single non-config Gateway dependency family: approximately **47 import sites**.

Target:

```text
gateway ──> profiles/
nous_cli ─> profiles/
```

## Phase 2 — Gateway control and topology

Move Gateway ownership machinery under `gateway/`.

Includes:

- multiplex decisions;
- served-profile state;
- host/runtime discovery;
- Gateway client/control interfaces;
- migration machinery;
- restart/drain/runtime ownership helpers.

Gateway should not import its own control-plane behaviour from a CLI package.

## Phase 3 — Runtime and persistence primitives

Extract generic infrastructure currently parked under `hermes_cli`.

Likely ownership areas:

```text
runtime/
storage/
```

Includes:

- process identity;
- process incarnation/liveness helpers;
- subprocess compatibility;
- stdio/runtime setup;
- resource limits;
- generic SQLite helpers such as transactions, database opening, and schema utilities.

## Phase 4 — Plugin runtime

Separate plugin runtime from plugin CLI management.

Runtime ownership includes:

- discovery;
- plugin manager lifecycle;
- hook invocation;
- activation/runtime state;
- compatibility warning machinery.

`nous_cli` retains only plugin-facing commands and presentation.

## Phase 5 — Providers and models

Finish consolidating provider/runtime ownership around the existing `providers/` subsystem.

Includes runtime portions of:

- provider resolution;
- model identity/catalogues;
- model/runtime routing;
- provider-specific runtime metadata;
- model switching logic that is not UI-specific.

The existing `providers/` registry/ABC is already intended to be the shared provider authority, so this phase extends that design rather than creating another abstraction.

CLI-specific model pickers and rendering remain in `nous_cli`.

## Phase 6 — Authentication and credentials

Move shared auth/account machinery out of the CLI namespace.

Includes:

- provider credential resolution;
- OAuth state;
- auth stores;
- token refresh;
- secret availability;
- runtime credential selection.

Target:

```text
gateway ─┐
agent ───┼──> auth/
nous_cli ┘
```

## Phase 7 — Shared commands and tool capability policy

Separate command protocol from command presentation.

### Shared command layer

Owns:

- canonical command definitions;
- aliases;
- availability metadata;
- dispatch contracts shared across surfaces.

### Tool runtime

Owns:

- runtime toolset resolution;
- platform capability policy;
- tool availability decisions.

### `nous_cli`

Owns:

- CLI parsing;
- interactive menus;
- formatting;
- terminal-specific command orchestration.

## Phase 8 — Kanban

Promote Kanban to an explicit subsystem.

Move runtime/domain implementation such as:

- database/storage;
- dispatch;
- notifications;
- worker coordination;
- decomposition;
- board/task domain operations.

Gateway consumes Kanban directly.

`nous_cli` owns only the `hermes kanban ...` command surface.

## Phase 9 — Automation

Move the related long-lived automation systems into an explicit ownership boundary.

Includes:

- goals;
- heartbeat;
- loops;
- associated execution/state machinery;
- blueprint/suggestion runtime where appropriate.

The intent is coherent ownership, not necessarily one giant module.

## Phase 10 — Tail evacuation

Resolve the remaining smaller dependency families individually.

Expected areas include:

- session/export helpers;
- partial compression helpers;
- status/report generation;
- web/backend helpers;
- debug/runtime utilities;
- skin/runtime state;
- miscellaneous agent/session primitives.

No generic dumping-ground package should be created. Each item moves to the subsystem that already logically owns it.

## Phase 11 — CLI cutover and old namespace removal

Once backing functionality has been evacuated:

- migrate remaining genuine CLI surface to `nous_cli`;
- make `nous_cli` the canonical CLI implementation;
- remove obsolete `hermes_cli` modules;
- remove the strangler fallback;
- update docs/import paths/tests.

At this point the only intentionally deferred `hermes_cli` area should be the config family covered separately because of **#122245**.

---

## Migration rules

Every phase should satisfy the same constraints:

- **No intentional behaviour changes.**
- **No opportunistic redesign outside the ownership boundary being migrated.**
- **No permanent internal re-export shims.**
- **No new dependency from owned subsystems back into `nous_cli`.**
- **Config remains untouched while #122245 is active.**
- Move implementation, update all in-tree consumers, then delete the obsolete implementation.
- Preserve external/plugin compatibility only through the project's existing compatibility policy.
- Add tests or structural checks that prevent the old dependency direction from returning.

Each phase should be independently reviewable and mergeable.

## Completion criteria

Primary measurable target:

```text
gateway -> hermes_cli
290 non-config import sites
        ↓
0
```

Secondary targets:

- Gateway owns Gateway lifecycle/control behaviour.
- Runtime infrastructure is independent of CLI presentation.
- Major product subsystems such as Kanban and automation have explicit owners.
- Provider and auth runtime logic are shared directly rather than routed through CLI modules.
- `nous_cli` contains CLI behaviour, not application-core behaviour.
- `hermes_cli` can be removed incrementally, with config treated separately after #122245.

This branch begins that migration rather than attempting to land the entire roadmap as one change.
