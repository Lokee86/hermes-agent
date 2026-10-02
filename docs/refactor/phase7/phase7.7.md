# Phase 7.7 — integration and verification

Status: the Phase 7 ownership implementation is complete. Focused regressions,
package-content verification, frozen baseline replay, and combined Phase 5/6/7
integration checks are recorded below. A pre-existing Windows Gateway
file-effect failure prevents claiming an entirely green broad suite.

## Independent Phase 7 verification

- Phase 7.6's final 16-file ownership selection passed 287 tests, with six
  skips. Its two additional Windows configuration test failures were caused by
  POSIX case assumptions in an unchanged fixture.
- The corrected configuration tests now pass: **173 passed**.
- Model-facing tool-hook tests retargeted to the canonical plugin API:
  **23 passed**.
- The structural checker contract suite: **44 passed**. The ownership scanner
  is blocking in CI.
- Frozen baseline replay: all **102** command definitions and **2,100**
  tool-selection cases check successfully. The **104** approved explicit-empty
  corrections from Phase 7.4 are the only accepted changes to selection output.
- `git diff --check` passed for the test repairs.

## Package verification

The standalone Phase 7 wheel builds using the repository's documented Nix
build marker (`HERMES_NIX_BUILD=1`); unmarked wheel builds are deliberately
blocked by the repository. The resulting wheel has 2,192 members. After
extracting it and excluding the source checkout from Python's import path,
`commands`, `commands.execution`, `tools.platform_policy`,
`tools.toolset_scope`, and `plugin_runtime.api` import successfully.
The retired internal modules `hermes_cli/slash_exec.py`,
`hermes_cli/toolset_scope.py`, and
`hermes_cli/commands_platforms.py` are absent from the archive.
This exercises Python-wheel contents, not an OS installer or full Nix build.
The combined Phase 5/6/7 branch also builds with the Nix marker: its extracted
wheel contains 2,330 members. Eight essential auth/command/tool/route modules
are present; isolated imports and both Actual-provider and generic route
normalization checks pass. Retired Phase 7 internal CLI files remain absent.

## Combined Phase 5 / Phase 6 / Phase 7 verification

The independent Phase 7.6 hard cut and completed Phase 5 consumer branch were
combined, then Phase 6's completed auth branch was merged and reconciled in
`refactor/phase7-integration` at `144d5b0f`. Phase 5's
`hermes_cli.route_identity` and the additional Phase 6 URL/Actual-provider
helpers now coexist in their existing owner; no forwarding facade was added.
The externally documented plugin import regression exercises real imports
rather than unavailable static-scanner helper functions.

Verification against the combined checkout:

- **65 passed** in `tests/auth`.
- **188 passed, one skipped** across command discovery/execution, CLI tooling,
  Gateway command discovery/authorization/toolsets, Desktop/TUI selection,
  ACP command dispatch and canonical tool-platform policy.
- Phase 7 structural ownership scanner: **passed** across 8,200 Python files.
- Plugin compatibility-pointer audit: **passed**; no first-party dependency
  on the 2,082 manifest entries (with UTF-8 console output).
- Syntax compilation of `auth`, `commands`, `tools`, and the merged route
  identity module: **passed**.
- Merged index: no unmerged entries; staged whitespace check passed.

## Existing regression limitation

`test_launch_policy_reaches_real_turn_runner` remains unreliable on this
Windows host. Its `policy-proof.txt` file can be absent even though the
terminal dispatch succeeds; that same missing-file assertion was reproduced
against the unchanged Phase 4 foundation under the same Python 3.11 runner.
The Phase 7 fixture now decodes actual terminal result payloads and compares
native Windows and MSYS working-directory representations instead of
searching JSON-escaped path strings. A canonical Python 3.14 run reached
that assertion for the CLI surface, but subsequent runs still exposed the
baseline file-effect failure, sometimes in a later surface.

Do not count that test as passing or attribute its baseline defect to this
ownership migration. The complete Desktop/TUI suite, OS-specific installer
validation, full Nix build, and the entire repository test suite are not
claimed here. Phase 6's independent closeout also documents its existing
Windows fixture failures and TUI-file timeout.
