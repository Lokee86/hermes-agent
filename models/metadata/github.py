"""Pure GitHub/Copilot reasoning capability interpretation."""

from __future__ import annotations

from typing import Any, Optional

from models.metadata.reasoning import CODEX_ASTRA_EFFORTS, clamp_effort, is_astra_model
from providers.model_normalizers import normalize_copilot_id

COPILOT_REASONING_EFFORTS_GPT5: tuple[str, ...] = ("minimal", "low", "medium", "high")
COPILOT_REASONING_EFFORTS_O_SERIES: tuple[str, ...] = ("low", "medium", "high")


def _catalog_ids(catalog: Optional[list[dict[str, Any]]]) -> tuple[str, ...]:
    return tuple(
        model_id
        for item in (catalog or ())
        if (model_id := str(item.get("id") or "").strip())
    )


def _fallback_efforts(model_id: str, *, known_ids: tuple[str, ...] = ()) -> list[str]:
    raw = str(model_id or "").strip().lower()
    if raw.startswith(("openai/o1", "openai/o3", "openai/o4", "o1", "o3", "o4")):
        return list(COPILOT_REASONING_EFFORTS_O_SERIES)
    normalized = normalize_copilot_id(model_id, known_ids).lower()
    if is_astra_model(normalized):
        return list(CODEX_ASTRA_EFFORTS)
    if normalized.startswith("gpt-5"):
        return list(COPILOT_REASONING_EFFORTS_GPT5)
    return []


def github_model_reasoning_efforts(
    model_id: Optional[str],
    *,
    catalog: Optional[list[dict[str, Any]]] = None,
) -> list[str]:
    """Return supported effort levels from caller-supplied catalog facts or model family."""
    known_ids = _catalog_ids(catalog)
    normalized = normalize_copilot_id(str(model_id or ""), known_ids)
    if not normalized:
        return []

    catalog_entry = (
        next((item for item in catalog if item.get("id") == normalized), None)
        if catalog
        else None
    )
    if catalog_entry is not None:
        capabilities = catalog_entry.get("capabilities")
        if isinstance(capabilities, dict):
            supports = capabilities.get("supports")
            efforts = supports.get("reasoning_effort") if isinstance(supports, dict) else None
            if not isinstance(efforts, list):
                return []
            return list(
                dict.fromkeys(
                    effort
                    for value in efforts
                    if (effort := str(value).strip().lower())
                )
            )
        if "reasoning" not in {
            str(value).strip().lower()
            for value in catalog_entry.get("capabilities", [])
        }:
            return []

    return _fallback_efforts(str(model_id or normalized), known_ids=known_ids)


def clamp_github_reasoning_effort(effort: Any, supported: list[str]) -> str:
    """Clamp GitHub reasoning effort with the historical medium/first fallback."""
    requested = str(effort or "medium").strip().lower()
    if requested not in supported:
        clamped = clamp_effort(requested, supported)
        requested = str(clamped or requested)
        if requested not in supported:
            requested = "medium" if "medium" in supported else supported[0]
    return requested


__all__ = [
    "COPILOT_REASONING_EFFORTS_GPT5",
    "COPILOT_REASONING_EFFORTS_O_SERIES",
    "clamp_github_reasoning_effort",
    "github_model_reasoning_efforts",
]
