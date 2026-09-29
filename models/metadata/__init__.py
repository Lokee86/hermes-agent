"""Canonical model capability/metadata domain."""

from models.metadata.interpretation import (
    UNKNOWN_MODEL_BASE,
    builtin_model_metadata,
    dict_or_empty,
    entry_supports_vision,
    extract_context,
    extract_limit,
    merge_catalog_entry_with_override,
    model_capabilities_from_entry,
    model_info_from_entry,
    override_int,
    override_to_catalog_shape,
    provider_info_from_entry,
    vision_marker_metadata,
)
from models.metadata.types import (
    ModelCapabilities,
    ModelInfo,
    ModelMetadata,
    ModelMetadataContext,
    ModelMetadataPatch,
    ProviderInfo,
    ReasoningMetadata,
)

__all__ = [
    "ModelCapabilities",
    "ModelInfo",
    "ModelMetadata",
    "ModelMetadataContext",
    "ModelMetadataPatch",
    "ProviderInfo",
    "ReasoningMetadata",
    "UNKNOWN_MODEL_BASE",
    "builtin_model_metadata",
    "dict_or_empty",
    "entry_supports_vision",
    "extract_context",
    "extract_limit",
    "merge_catalog_entry_with_override",
    "model_capabilities_from_entry",
    "model_info_from_entry",
    "override_int",
    "override_to_catalog_shape",
    "provider_info_from_entry",
    "vision_marker_metadata",
]
