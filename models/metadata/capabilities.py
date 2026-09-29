"""Canonical capability resolution for model metadata.

This module owns capability precedence and tri-state semantics. It deliberately
knows nothing about route selection, credentials, request formatting, catalog
membership, or any Hermes surface. Environment-specific facts arrive through
callable sources supplied by the boundary that can reach them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from models.metadata.types import ModelMetadata, ModelMetadataContext, ModelMetadataPatch, ReasoningMetadata
from models.identity import ModelRef

CapabilitySource = Callable[[ModelRef, ModelMetadataContext], ModelMetadataPatch | None]


@dataclass(frozen=True, slots=True)
class CapabilitySources:
    """Ordered external fact providers.

    The order is part of the capability contract: live runtime facts precede
    catalog facts, which precede local provider probes and declarations.
    """

    live: CapabilitySource | None = None
    catalog: CapabilitySource | None = None
    local: CapabilitySource | None = None
    provider: CapabilitySource | None = None

    def ordered(self) -> tuple[tuple[str, CapabilitySource], ...]:
        return tuple(
            (name, source)
            for name, source in (
                ("live", self.live),
                ("catalog", self.catalog),
                ("local", self.local),
                ("provider", self.provider),
            )
            if source is not None
        )


def _patch_mapping(value: object) -> ModelMetadataPatch | None:
    if isinstance(value, ModelMetadataPatch):
        return value
    if not isinstance(value, Mapping):
        return None
    fields = {
        name: value[name]
        for name in ModelMetadataPatch.__dataclass_fields__
        if name in value
    }
    return ModelMetadataPatch(**fields)


def _apply_patch(
    values: dict[str, object],
    provenance: dict[str, str],
    patch: ModelMetadataPatch,
    source: str,
) -> None:
    for field_name in ModelMetadataPatch.__dataclass_fields__:
        value = getattr(patch, field_name)
        if value is not None and values[field_name] is None:
            values[field_name] = value
            provenance[field_name] = source


def resolve_model_metadata(
    ref: ModelRef,
    *,
    context: ModelMetadataContext | None = None,
    sources: CapabilitySources | Iterable[tuple[str, CapabilitySource]] = CapabilitySources(),
) -> ModelMetadata:
    """Resolve sparse capability facts without collapsing ``False`` into unknown.

    Explicit route-bound facts win over configured facts. Remaining fields use
    the supplied source order; a source returning ``None`` means it has no
    opinion and resolution continues.
    """
    context = context or ModelMetadataContext()
    values = {
        field_name: None
        for field_name in ModelMetadataPatch.__dataclass_fields__
    }
    provenance: dict[str, str] = {}

    if context.explicit is not None:
        _apply_patch(values, provenance, context.explicit, "explicit")
    if context.configured is not None:
        _apply_patch(values, provenance, context.configured, "configured")

    ordered = sources.ordered() if isinstance(sources, CapabilitySources) else tuple(sources)
    for source_name, source in ordered:
        patch = _patch_mapping(source(ref, context))
        if patch is not None:
            _apply_patch(values, provenance, patch, source_name)

    metadata_values = dict(values)
    metadata_values["input_modalities"] = tuple(values["input_modalities"] or ())
    metadata_values["output_modalities"] = tuple(values["output_modalities"] or ())
    metadata_values["reasoning"] = values["reasoning"] or ReasoningMetadata()
    return ModelMetadata(
        ref=ref,
        **metadata_values,
        provenance=provenance,
    )


def resolve_supports_vision(
    ref: ModelRef,
    *,
    context: ModelMetadataContext | None = None,
    sources: CapabilitySources | Iterable[tuple[str, CapabilitySource]] = CapabilitySources(),
) -> bool | None:
    """Resolve only vision and stop once a source answers it."""
    context = context or ModelMetadataContext()
    for patch in (context.explicit, context.configured):
        if patch is not None and patch.supports_vision is not None:
            return patch.supports_vision
    ordered = sources.ordered() if isinstance(sources, CapabilitySources) else tuple(sources)
    for _source_name, source in ordered:
        patch = _patch_mapping(source(ref, context))
        if patch is not None and patch.supports_vision is not None:
            return patch.supports_vision
    return None


__all__ = [
    "CapabilitySource",
    "CapabilitySources",
    "resolve_model_metadata",
    "resolve_supports_vision",
]
