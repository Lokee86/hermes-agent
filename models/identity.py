"""Canonical model identity.

This module owns the meaning of provider-qualified model references. It may use
the public provider-identity API, but it does not discover model catalogues,
choose providers, resolve routes, or read credentials/configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from providers import is_aggregator, normalize_provider


@dataclass(frozen=True, slots=True)
class ModelRef:
    """Canonical provider/model identity used across Hermes surfaces."""

    provider: str
    model: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", normalize_provider(self.provider))
        object.__setattr__(self, "model", str(self.model or "").strip())


@dataclass(frozen=True, slots=True)
class ModelAliasPattern:
    """Vendor/family pattern used to resolve a short model alias."""

    vendor: str
    family: str


class AmbiguousModelAliasError(ValueError):
    """Raised when an alias has more than one valid candidate."""

    def __init__(self, alias: str, provider: str, candidates: Iterable[str]) -> None:
        self.alias = str(alias or "").strip().lower()
        self.provider = normalize_provider(provider)
        self.candidates = tuple(candidates)
        super().__init__(
            f"{self.alias!r} matches {len(self.candidates)} models on "
            f"{self.provider}: {', '.join(self.candidates)}"
        )


def _canonical_provider_ids(values: Iterable[str]) -> set[str]:
    return {
        canonical
        for value in values
        if (canonical := normalize_provider(str(value or "").strip()))
    }


def _named_custom_ids(values: Iterable[str]) -> tuple[str, ...]:
    ids = {
        normalized
        for value in values
        if (normalized := str(value or "").strip().lower()).startswith("custom:")
    }
    return tuple(sorted(ids, key=len, reverse=True))


def parse_model_ref(
    raw: str,
    default_provider: str = "",
    *,
    known_provider_ids: Iterable[str] = (),
    named_custom_provider_ids: Iterable[str] = (),
) -> ModelRef:
    """Parse Hermes provider:model syntax without guessing from punctuation.

    A colon is a provider delimiter only when its left side resolves to a known
    provider. Named custom providers are matched longest-first so
    provider-native colons in the model id remain intact.
    """

    value = str(raw or "").strip()
    if not value:
        return ModelRef(default_provider, "")

    lowered = value.lower()
    for provider_id in _named_custom_ids(named_custom_provider_ids):
        marker = f"{provider_id}:"
        if lowered.startswith(marker):
            model = value[len(marker):].strip()
            if model:
                return ModelRef(provider_id, model)

    colon = value.find(":")
    if colon > 0:
        provider_part = value[:colon].strip()
        model_part = value[colon + 1 :].strip()
        if provider_part and model_part:
            canonical = normalize_provider(provider_part)
            known = _canonical_provider_ids(known_provider_ids)
            if canonical in known:
                return ModelRef(canonical, model_part)

    return ModelRef(default_provider, value)


def parse_configured_provider_ref(
    raw: str,
    configured_provider_ids: Iterable[str],
) -> ModelRef | None:
    """Parse an explicit configured provider/model reference.

    This performs no catalogue lookup and makes no routing decision. Callers
    decide whether configured-provider interpretation outranks an aggregator's
    native slash-bearing model id.
    """

    value = str(raw or "").strip()
    if "/" not in value:
        return None

    provider_part, model_part = (part.strip() for part in value.split("/", 1))
    if not provider_part or not model_part:
        return None

    configured = _canonical_provider_ids(configured_provider_ids)
    canonical = normalize_provider(provider_part)
    if canonical not in configured:
        return None
    return ModelRef(canonical, model_part)


def format_model_ref(ref: ModelRef) -> str:
    """Encode a model reference as the stable provider:model wire form."""

    if not ref.model:
        return ""
    return f"{ref.provider}:{ref.model}" if ref.provider else ref.model


def normalize_model_id(
    provider: str,
    model: str,
    *,
    known_ids: Iterable[str] = (),
) -> str:
    """Return the canonical model id for a known provider.

    Phase 5.3.2 establishes the final seam conservatively: unknown and
    provider-native ids pass through unchanged apart from surrounding
    whitespace. Provider-specific normalization moves behind this interface in
    Phase 5.3.3. known_ids is accepted now so catalogue-assisted rules can
    consume caller-supplied candidates without identity ever owning discovery.
    """

    return str(model or "").strip()


def normalize_model_ref(
    ref: ModelRef,
    *,
    known_ids: Iterable[str] = (),
) -> ModelRef:
    """Normalize a model reference through the canonical identity seam."""

    return ModelRef(
        ref.provider,
        normalize_model_id(ref.provider, ref.model, known_ids=known_ids),
    )


def resolve_model_alias(
    alias: str,
    provider: str,
    candidates: Iterable[str],
    aliases: Mapping[str, ModelAliasPattern],
) -> str | None:
    """Resolve one short alias against caller-supplied model candidates.

    Catalogue acquisition and candidate ordering remain outside identity.
    Multiple matches are explicit ambiguity rather than an implicit version
    choice.
    """

    key = str(alias or "").strip().lower()
    pattern = aliases.get(key)
    if pattern is None:
        return None

    prefix = pattern.family
    if is_aggregator(provider):
        prefix = f"{pattern.vendor}/{pattern.family}"
    wanted = prefix.lower()

    matches = [
        candidate
        for candidate in (str(value or "").strip() for value in candidates)
        if candidate and candidate.lower().startswith(wanted)
    ]
    if len(matches) > 1:
        raise AmbiguousModelAliasError(key, provider, matches)
    return matches[0] if matches else None
