"""Caller-owned fact acquisition for canonical explicit model selection."""

from __future__ import annotations

from models import ModelRef
from models.selection import ExplicitDetectionFacts
from providers import list_providers, normalize_provider

from hermes_cli.models_catalog_static import static_provider_model_ids


def build_explicit_detection_facts(
    raw_model: str,
    current_provider: str,
) -> ExplicitDetectionFacts:
    """Materialize discovery/availability facts without choosing a provider."""

    from hermes_cli.models import (
        _find_openrouter_slug,
        _model_in_provider_catalog,
        _provider_keys,
        _resolve_provider_prefix,
        _static_catalog_matches,
    )
    from hermes_cli.model_selection_defaults import select_provider_default, selected_model_id
    from hermes_cli.models_detect import (
        current_provider_catalog_match,
        current_provider_owns_vendor,
        provider_has_credentials,
    )

    raw = str(raw_model or "").strip()
    current = str(current_provider or "").strip().lower()
    current_keys = _provider_keys(current)

    named = None
    named_provider = normalize_provider(raw.lower())
    known = {
        normalize_provider(str(profile.name or "").strip().lower())
        for profile in list_providers()
        if str(profile.name or "").strip()
    }
    if named_provider not in {"custom", "openrouter"} and named_provider in known:
        defaults = tuple(static_provider_model_ids(named_provider))
        if defaults and named_provider not in current_keys:
            named = ModelRef(
                named_provider,
                selected_model_id(select_provider_default(named_provider)) or defaults[0],
            )

    static = tuple(
        ModelRef(provider, model)
        for provider, model in _static_catalog_matches(raw, current)
    )
    openrouter_slug = _find_openrouter_slug(raw)
    openrouter = ModelRef("openrouter", openrouter_slug) if openrouter_slug else None
    declared = _resolve_provider_prefix(raw)
    declared_ref = ModelRef(*declared) if declared else None

    candidate_providers = tuple(dict.fromkeys(
        ref.provider
        for ref in (
            *static,
            *(ref for ref in (named, openrouter, declared_ref) if ref is not None),
        )
    ))
    eligible = tuple(
        provider for provider in candidate_providers
        if provider_has_credentials(provider)
    )

    return ExplicitDetectionFacts(
        current_catalog_model=current_provider_catalog_match(raw, current) or "",
        current_provider_owns_model=current_provider_owns_vendor(raw, current),
        named_provider_candidate=named,
        static_candidates=static,
        current_static_owns_model=_model_in_provider_catalog(raw.lower(), current_keys),
        openrouter_candidate=openrouter,
        declared_provider_candidate=declared_ref,
        eligible_providers=eligible,
        allow_first_guess=current in {"", "auto"},
    )


__all__ = ["build_explicit_detection_facts"]
