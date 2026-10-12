# P1 → P2 selective propagation manifest (Step 16)

Status: **planning only**. No repair has been applied to P2 in this step.

## Frozen ancestry and sources

- P1: `split/phase1-profiles`, fork HEAD `35a51ccdafce03d4a67c57b1e228d7c62ae4a693`, Step 15 verified **54 passed** focused tests and pushed.
- P2: `split/phase2-gateway`, starting HEAD `61888d5dd392356b81b95fa63ef9429419f003c6`.
- Earlier P1 checkpoint inherited by P2: `d217d366d3e2cb17b31a917f36587e89dbc9e1db`; current P1 and P2 have diverged. Git merge-base for their current heads: `0f2fdc2757f79695d60048c1a4ec3ded7b107be6`.
- **Do not merge P1 HEAD into P2.** Preserve distinct PRs and P2's later Gateway/runtime architecture; selectively transplant semantics, not entire files. Do not restore retired `hermes_cli.gateway*` compatibility wrappers.
- P1 commits below are reference implementations, **not** proof P2 lacks each behavior. Verify P2 code and acceptance tests before each edit.

## Propagation ledger

| Target step | P1 source commit(s) | P1 behavior to preserve | Inspect on P2 | Acceptance evidence |
| --- | --- | --- | --- | --- |
| 17 — secret scope | `6aece326cb` | Resolve native HTTP config-secret scope from effective selected profile home, including omitted/current selectors | `hermes_cli/web_server_profiles.py`, `tests/hermes_cli/test_web_multi_profile_scope.py`, `tests/gateway/test_native_config_owner_scope.py` | Secondary-home credentials never borrowed from launching home |
| 18 — failed unserve | `279cfe0d7f` | Failed retirement must retain reservations, adapters, and serving ownership while reconcile continues for others | `gateway/run_profile_reconcile.py`, `gateway/run_runtime.py`, `tests/gateway/test_profile_unserve_retention.py` | Busy/live turn refuses retirement without orphaning owner |
| 19 — cron roster | `76aa9c9471` | Fallback imports/uses actual profiles module on roster-discovery failure | `hermes_cli/web_server_cron.py`, `tests/hermes_cli/test_cron_profile_roster_fallback.py` | Fallback receives module; no NameError |
| 20 — native session contracts and launch | `eed6ae7ddc`, `7bda8596f1`, `7462eee726`, `bccd39d526` | RPC handler catalog + canonical param/result validation; off-loop frozen skill rendering; idempotent hook consent; owner-scoped authorized latest/CWD resume | `gateway/session_controls.py`, `gateway/session_local.py`, `gateway/session_policy.py`, `hermes_cli/gateway_chat.py`, `tui_gateway/contracts/canonical_sessions.py` | Wire-contract, skill retry, hook, latest workspace/authorization tests |
| 21 — ACP | `16fbbceb54`, `d4f907c6dd`, `4b2dcf1b33`, `1b062f8429`, `1919948bce` | Reconnect without resubmitting ambiguous turns; unknown FIFO reporting/recovery; clarification permissions and forms; compression logical/editor aliases; segment/interim/reused response projections | `acp_adapter/gateway_server.py`, `acp_adapter/elicitation.py`, `acp_adapter/catalog.py`, `tests/acp_adapter/test_gateway_*.py` | Reconnect, unknown, cancel, clarify, compressed reopen, delivery shape tests |
| 21 test-harness companion | `35a51ccdaf` | Compressed-session test derives actual database directory from test store instead of assuming home | `tests/acp_adapter/test_gateway_compressed_reopen.py` | Test stable when run with other ACP/gateway tests |

## Execution and verification protocol

1. Before each target step, diff P2's **current** functions/tests against the P1 source commit; classify as `missing`, `partial`, `already fixed`, or `not applicable`. Record evidence in the step's commit/notes.
2. Apply only missing semantics to P2's current structure. Import tests selectively with adjusted fixtures/contracts. **No bulk cherry-pick** of source commits and no cross-branch merge.
3. Run focused red→green tests and `git diff --check` per step; identify inherited unrelated test failures separately.
4. Step 22 is the P2 combined acceptance gate for Steps 17–21, including multi-profile authority invariants, canonical wire checks, ACP reconnect/unknown/clarify/alias/render, and CLI resume. Preserve P2-native defects for Steps 23–51.
5. Before pushing P2, confirm clean tracked diff, exact commit head and review status. Step 16 commits the manifest **locally only**.

## Explicit exclusions

- P1 fixes unrelated to this propagation ledger and P2-native review findings belong to their own steps; do not absorb them into Steps 17–21.
- Do not modify P1, rewrite P2's ancestry, merge branches, or push at Step 16.
