"""Canonical model-domain API."""

from models.identity import (
    AmbiguousModelAliasError,
    ModelAliasPattern,
    ModelRef,
    format_model_ref,
    normalize_model_id,
    normalize_model_ref,
    parse_configured_provider_ref,
    parse_model_ref,
    resolve_model_alias,
)

__all__ = [
    "AmbiguousModelAliasError",
    "ModelAliasPattern",
    "ModelRef",
    "format_model_ref",
    "normalize_model_id",
    "normalize_model_ref",
    "parse_configured_provider_ref",
    "parse_model_ref",
    "resolve_model_alias",
]
