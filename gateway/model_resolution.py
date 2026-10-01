"""Gateway-owned model precedence over already-loaded application facts.

This module does not interpret provider/model identity or invocation semantics.
It only decides which application tier supplied the effective model candidate;
canonical identity/selection/routing remain owned by models/ and providers/.
"""

from __future__ import annotations

from typing import Any


def _model_candidate(value: Any) -> str:
    """Extract a model candidate from the gateway's config/session shapes."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("model") or "").strip()
    model = getattr(value, "model", None)
    return str(model or "").strip()


def effective_model_candidate(*tiers: Any) -> str:
    """Return the first non-empty model from highest to lowest gateway precedence."""
    for tier in tiers:
        candidate = _model_candidate(tier)
        if candidate:
            return candidate
    return ""


__all__ = ["effective_model_candidate"]
