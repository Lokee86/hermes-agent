"""Canonical model capability/metadata types.

This package answers "what can this model do?" without owning identity,
catalogue membership, route selection, request policy, or credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from models.identity import ModelRef


@dataclass(frozen=True, slots=True)
class ReasoningMetadata:
    """Tri-state reasoning capability details for one effective model route."""

    supported: bool | None = None
    supported_efforts: tuple[str, ...] | None = None
    mandatory: bool | None = None


@dataclass(frozen=True, slots=True)
class ModelMetadataPatch:
    """Sparse metadata facts contributed by one source.

    None means "this source has no opinion". Definitive False is preserved
    and must never be collapsed into unknown.
    """

    context_window: int | None = None
    max_output_tokens: int | None = None
    max_input_tokens: int | None = None

    supports_tools: bool | None = None
    supports_vision: bool | None = None
    supports_reasoning: bool | None = None
    supports_structured_output: bool | None = None
    supports_temperature: bool | None = None

    input_modalities: tuple[str, ...] | None = None
    output_modalities: tuple[str, ...] | None = None

    reasoning: ReasoningMetadata | None = None

    model_family: str | None = None
    open_weights: bool | None = None
    release_date: str | None = None
    status: str | None = None
    knowledge_cutoff: str | None = None


@dataclass(frozen=True, slots=True)
class ModelMetadataContext:
    """Already-resolved route context used while answering metadata questions.

    The metadata domain may observe this route, but it does not select or
    normalize it. "explicit" and "configured" are normalized sparse facts
    supplied by the configuration/runtime boundary.
    """

    base_url: str = ""
    api_key: str = ""
    allow_network: bool = False
    explicit: ModelMetadataPatch | None = None
    configured: ModelMetadataPatch | None = None


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    """Canonical effective metadata for a model identity."""

    ref: ModelRef

    context_window: int | None = None
    max_output_tokens: int | None = None
    max_input_tokens: int | None = None

    supports_tools: bool | None = None
    supports_vision: bool | None = None
    supports_reasoning: bool | None = None
    supports_structured_output: bool | None = None
    supports_temperature: bool | None = None

    input_modalities: tuple[str, ...] = ()
    output_modalities: tuple[str, ...] = ()

    reasoning: ReasoningMetadata = field(default_factory=ReasoningMetadata)

    model_family: str = ""
    open_weights: bool | None = None
    release_date: str = ""
    status: str = ""
    knowledge_cutoff: str = ""

    # field name -> provenance label (explicit/configured/live/catalog/static)
    provenance: Mapping[str, str] = field(default_factory=dict)
