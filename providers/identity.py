"""Canonical inference-provider identity.

This module owns provider identity semantics shared by CLI and runtime layers.
It deliberately depends only on the provider contract and registry surface:
catalog discovery, credentials, configuration, and runtime route construction
belong elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from providers.base import ProviderProfile


@dataclass(frozen=True)
class ResolvedProvider:
    """Effective provider identity after declaration/config resolution."""

    id: str
    display_name: str
    api_mode: str = "chat_completions"
    auth_type: str = "api_key"
    env_vars: tuple[str, ...] = ()
    base_url: str = ""
    base_url_env_var: str = ""
    is_aggregator: bool = False
    is_routing_aggregator: bool = False
    source: str = ""


def _profile_for(name: str) -> ProviderProfile | None:
    # Lazy import keeps identity independent of registry implementation details
    # while avoiding an import cycle through providers.__init__.
    from providers import get_provider_profile

    return get_provider_profile(name)


def normalize_provider(name: str) -> str:
    """Return the canonical provider id for a name or registered alias."""
    key = str(name or "").strip().lower()
    if not key:
        return ""
    profile = _profile_for(key)
    if profile is None:
        return key
    return str(profile.name or key).strip().lower()


def get_provider_label(provider: str) -> str:
    """Return the provider's declared display name, falling back to its id."""
    canonical = normalize_provider(provider)
    if not canonical:
        return ""
    profile = _profile_for(canonical)
    if profile is None:
        return canonical
    return str(profile.display_name or profile.name or canonical)


def is_aggregator(provider: str) -> bool:
    """Whether a provider exposes models from more than one model namespace."""
    canonical = normalize_provider(provider)
    if canonical.startswith("custom:"):
        return True
    profile = _profile_for(canonical)
    return bool(profile and profile.is_aggregator)


def is_routing_aggregator(provider: str) -> bool:
    """Whether model selection may route to a different upstream provider."""
    canonical = normalize_provider(provider)
    if canonical.startswith("custom:"):
        return True
    profile = _profile_for(canonical)
    if profile is None:
        return False
    if profile.is_routing_aggregator is not None:
        return profile.is_routing_aggregator
    return profile.is_aggregator
