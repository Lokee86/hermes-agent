"""Canonical model-domain API."""

from models.identity import (
    AmbiguousModelAliasError,
    MODEL_ALIASES,
    ModelAliasPattern,
    ModelRef,
    format_model_ref,
    model_alias_sort_key,
    normalize_model_id,
    normalize_model_ref,
    parse_configured_provider_ref,
    parse_model_ref,
    resolve_declared_model_id,
    resolve_model_alias,
)

__all__ = [
    "AmbiguousModelAliasError",
    "MODEL_ALIASES",
    "ModelAliasPattern",
    "ModelRef",
    "format_model_ref",
    "model_alias_sort_key",
    "normalize_model_id",
    "normalize_model_ref",
    "parse_configured_provider_ref",
    "parse_model_ref",
    "resolve_declared_model_id",
    "resolve_model_alias",
]
