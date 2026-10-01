# commands/ — shared slash command definitions

`COMMAND_REGISTRY` is the single built-in registry. Preserve aliases, ordering, execution keys,
busy policies, and Desktop wire metadata. `resolve_command`, `available_commands`, and
`command_desktop_meta` are the shared query interface.

Keep this package import-light. Configuration loaders, persistence, localized help rendering,
terminal dependencies, plugin discovery/lifecycle, and authorization belong to their consumers.
Gateway availability takes supplied canonical gate names; discovery never grants authority.
Dynamic metadata uses lazy `plugin_runtime.api` reads without registering another built-in index.

CLI presentation lives in `hermes_cli/commands_presentation.py`; Gateway help and configuration
gate loading live in `gateway/command_presentation.py`. `hermes_cli/commands.py` contains only
manifest-listed external plugin compatibility entries and must never be imported internally.

Tests belong in `tests/commands/` and run through `scripts/run_tests.sh`.
