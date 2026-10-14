"""Phase 4.10 plugin-runtime ownership verification through interfaces and behavior."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event

from plugin_runtime.context import PluginContext
from plugin_runtime.loading import LoadedPlugin, PluginLoaderMixin
from plugin_runtime.manager import PluginManager
from plugin_runtime.manifest import PluginManifest
from plugin_runtime.registration import PluginRegistration, replacement_coordinator


def test_phase410_cli_facade_reexports_canonical_runtime_owners() -> None:
    import hermes_cli.plugins as legacy

    assert legacy.PluginManager is PluginManager
    assert legacy.PluginContext is PluginContext
    assert legacy.PluginRegistration is PluginRegistration
    assert legacy.LoadedPlugin is LoadedPlugin
    assert legacy.PluginLoaderMixin is PluginLoaderMixin
    assert legacy.PluginManifest is PluginManifest


def test_phase410_cli_facade_routes_runtime_operations_to_canonical_owners() -> None:
    import hermes_cli.plugins as legacy
    from plugin_runtime import api, lifecycle

    assert legacy.invoke_hook is api.invoke_hook
    assert legacy.invoke_middleware is api.invoke_middleware
    assert legacy.unload_plugins is api.unload_plugins
    assert legacy.discover_plugins is lifecycle.discover_plugins
    assert legacy.get_plugin_manager is lifecycle.get_plugin_manager


def test_phase410_manager_constructs_the_canonical_runtime_context(tmp_path) -> None:
    manager = PluginManager(scope_key=str(tmp_path))
    manifest = PluginManifest(name="phase410", key="phase410", source="user")

    context = manager.context_for(manifest)

    assert type(context) is PluginContext
    assert context.manifest is manifest
    assert context._manager is manager


def test_phase410_frozen_compatibility_surface_is_inert() -> None:
    from hermes_cli import plugin_compat

    assert plugin_compat.compat_report() == {}
    assert plugin_compat.removal_in_effect() is True
    assert plugin_compat.summary_lines({}) == []


def test_phase410_register_skill_replacement_is_serialized_against_disposal(
    tmp_path, monkeypatch
) -> None:
    """An older skill lease cannot dispose between replacement write and lease attachment."""
    skill_a = tmp_path / "a.md"
    skill_b = tmp_path / "b.md"
    skill_a.write_text("# a\n", encoding="utf-8")
    skill_b.write_text("# b\n", encoding="utf-8")

    manager = PluginManager(scope_key=str(tmp_path))
    context_a = PluginContext(
        PluginManifest(name="skill_a", key="skill_a", skill_namespace="shared"),
        manager,
    )
    context_b = PluginContext(
        PluginManifest(name="skill_b", key="skill_b", skill_namespace="shared"),
        manager,
    )
    handle_a = context_a.register_skill("probe", skill_a)
    qualified = "shared:probe"

    original_acquire = replacement_coordinator.acquire
    wrote = Event()
    release = Event()

    def paused_acquire(slot, *, current, previous, restore, finalize=None):
        if (
            isinstance(current, dict)
            and current.get("plugin_key") == "skill_b"
            and slot == ("manager_mapping", id(manager._plugin_skills), qualified)
        ):
            wrote.set()
            assert release.wait(timeout=2)
        return original_acquire(
            slot,
            current=current,
            previous=previous,
            restore=restore,
            finalize=finalize,
        )

    monkeypatch.setattr(replacement_coordinator, "acquire", paused_acquire)

    handle_b = None
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            registration = pool.submit(context_b.register_skill, "probe", skill_b)
            assert wrote.wait(timeout=1)

            disposal = pool.submit(handle_a.dispose)
            try:
                disposal.result(timeout=0.05)
            except TimeoutError:
                pass
            else:
                raise AssertionError("skill disposal interleaved with replacement transaction")

            release.set()
            handle_b = registration.result(timeout=1)
            disposal.result(timeout=1)

        assert handle_b is not None
        assert manager._plugin_skills[qualified]["path"] == skill_b
        assert manager._plugin_skills[qualified]["plugin_key"] == "skill_b"
    finally:
        release.set()
        if handle_b is not None:
            handle_b.dispose()


def test_phase410_retired_load_disable_gate_is_absent() -> None:
    assert "_plugin_load_disable_reason" not in PluginManager.__dict__
    assert "_plugin_load_disable_reason" not in PluginLoaderMixin.__dict__
