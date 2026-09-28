"""Late provider registration is immediately visible through the live picker catalog."""

import providers
from hermes_cli.models import list_available_providers
from hermes_cli.provider_catalog import provider_catalog_by_slug, provider_slugs
from providers import register_provider
from providers.base import ProviderProfile


def _profile(name: str, *, label: str | None = None) -> ProviderProfile:
    return ProviderProfile(
        name=name,
        display_name=label or name,
        description="late plugin (direct API)",
    )


def test_late_registered_provider_reaches_picker_catalog(monkeypatch):
    providers.list_providers()  # finish discovery before exercising late registration
    monkeypatch.setattr(providers.registry, "_REGISTRY", dict(providers.registry._REGISTRY))
    monkeypatch.setattr(providers.registry, "_ALIASES", dict(providers.registry._ALIASES))
    monkeypatch.setattr(providers.registry, "_SOURCES", dict(providers.registry._SOURCES))
    monkeypatch.setattr(providers.registry, "_PROVIDER_LIST_CACHE", None)
    # Step 7 must not rely on the remaining Step-8 catalogue sync callback.
    monkeypatch.setattr(providers.registry, "_sync_auth_registry", lambda: None)

    slug = "zz-late-plugin-provider"
    assert slug not in provider_catalog_by_slug()

    register_provider(_profile(slug))
    descriptor = provider_catalog_by_slug()[slug]
    assert descriptor.label == slug
    assert descriptor.description == "late plugin (direct API)"
    assert slug in {row["id"] for row in list_available_providers()}
    assert provider_slugs().count(slug) == 1

    register_provider(_profile(slug, label="Late Plugin Updated"))
    assert provider_catalog_by_slug()[slug].label == "Late Plugin Updated"
    assert provider_slugs().count(slug) == 1
