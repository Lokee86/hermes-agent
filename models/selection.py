"""Pure provider/model selection over a caller-supplied canonical universe.

Discovery, credentials, health, client construction, persistence, and
presentation stay at higher layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from models.identity import ModelRef
from models.metadata.types import ModelMetadata
from providers.identity import normalize_provider
from providers.routing import InvocationRequest, InvocationRoute, resolve_invocation_route


@dataclass(frozen=True, slots=True)
class CapabilityRequirements:
    """Hard capability requirements; unknown never satisfies a requirement."""

    tools: bool | None = None
    vision: bool | None = None
    reasoning: bool | None = None
    structured_output: bool | None = None
    minimum_context_window: int | None = None


@dataclass(frozen=True, slots=True)
class SelectionConstraints:
    """Hard filters applied before preference ranking."""

    allowed_providers: tuple[str, ...] = ()
    allowed_models: tuple[ModelRef, ...] = ()
    excluded_models: tuple[ModelRef, ...] = ()
    require_catalogued: bool = False
    capabilities: CapabilityRequirements = field(default_factory=CapabilityRequirements)
    allowed_api_modes: tuple[str, ...] = ()
    allowed_runtime_kinds: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        normalized = (normalize_provider(value) for value in self.allowed_providers if value)
        object.__setattr__(self, "allowed_providers", tuple(dict.fromkeys(normalized)))


@dataclass(frozen=True, slots=True)
class SelectionPolicy:
    """Replayable preference data; never discovers or mutates candidates."""

    name: str = "default"
    preferred: tuple[ModelRef, ...] = ()
    provider_order: tuple[str, ...] = ()
    prefer_catalogued: bool = False

    def __post_init__(self) -> None:
        normalized = (normalize_provider(value) for value in self.provider_order if value)
        object.__setattr__(self, "provider_order", tuple(dict.fromkeys(normalized)))


@dataclass(frozen=True, slots=True)
class SelectionCandidate:
    """One canonical candidate snapshot from the available model universe."""

    ref: ModelRef
    metadata: ModelMetadata
    route: InvocationRoute
    catalogued: bool = False
    source: str = ""
    stable_order: int = 0

    def __post_init__(self) -> None:
        if self.metadata.ref != self.ref:
            raise ValueError("candidate metadata identity does not match candidate ref")
        if ModelRef(self.route.provider, self.route.model) != self.ref:
            raise ValueError("candidate route identity does not match candidate ref")


@dataclass(frozen=True, slots=True)
class SelectionRequest:
    candidates: tuple[SelectionCandidate, ...]
    purpose: str = ""
    explicit: ModelRef | None = None
    constraints: SelectionConstraints = field(default_factory=SelectionConstraints)
    policy: SelectionPolicy = field(default_factory=SelectionPolicy)

    def __post_init__(self) -> None:
        refs = tuple(candidate.ref for candidate in self.candidates)
        if len(refs) != len(set(refs)):
            raise ValueError("selection candidates must have unique canonical identities")
        if self.explicit is not None and (not self.explicit.provider or not self.explicit.model):
            raise ValueError("explicit selection requires a canonical provider and model")


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    ref: ModelRef
    reasons: tuple[str, ...]


class SelectionReason(StrEnum):
    EXPLICIT_MATCH = "explicit_match"
    PREFERRED_MATCH = "preferred_match"
    POLICY_DEFAULT = "policy_default"
    EXPLICIT_UNAVAILABLE = "explicit_unavailable"
    NO_ELIGIBLE_CANDIDATE = "no_eligible_candidate"


@dataclass(frozen=True, slots=True)
class ModelSelection:
    selected: SelectionCandidate | None
    eligible: tuple[SelectionCandidate, ...]
    rejected: tuple[CandidateRejection, ...]
    reason: SelectionReason
    purpose: str = ""
    policy: str = ""

    @property
    def success(self) -> bool:
        return self.selected is not None


def build_selection_candidate(
    ref: ModelRef,
    metadata: ModelMetadata,
    route_request: InvocationRequest,
    *,
    catalogued: bool = False,
    source: str = "",
    stable_order: int = 0,
) -> SelectionCandidate:
    """Build a candidate through the canonical Phase 5.6 route owner."""

    route = resolve_invocation_route(replace(route_request, provider=ref.provider, model=ref.model))
    return SelectionCandidate(ref, metadata, route, catalogued, source, stable_order)


def _rejections(candidate: SelectionCandidate, constraints: SelectionConstraints) -> tuple[str, ...]:
    reasons: list[str] = []
    if constraints.allowed_providers and candidate.ref.provider not in constraints.allowed_providers:
        reasons.append("provider_not_allowed")
    if constraints.allowed_models and candidate.ref not in constraints.allowed_models:
        reasons.append("model_not_allowed")
    if candidate.ref in constraints.excluded_models:
        reasons.append("model_excluded")
    if constraints.require_catalogued and not candidate.catalogued:
        reasons.append("not_catalogued")
    if constraints.allowed_api_modes and candidate.route.api_mode not in constraints.allowed_api_modes:
        reasons.append("api_mode_not_allowed")
    if constraints.allowed_runtime_kinds and candidate.route.runtime_kind not in constraints.allowed_runtime_kinds:
        reasons.append("runtime_kind_not_allowed")

    metadata, req = candidate.metadata, constraints.capabilities
    for name, actual, required in (
        ("tools", metadata.supports_tools, req.tools),
        ("vision", metadata.supports_vision, req.vision),
        ("reasoning", metadata.supports_reasoning, req.reasoning),
        ("structured_output", metadata.supports_structured_output, req.structured_output),
    ):
        if required is not None and actual is not required:
            reasons.append(f"requires_{name}={required}")
    if req.minimum_context_window is not None and (
        metadata.context_window is None or metadata.context_window < req.minimum_context_window
    ):
        reasons.append(f"minimum_context_window={req.minimum_context_window}")
    return tuple(reasons)


def _index(value, values: tuple) -> int:
    try:
        return values.index(value)
    except ValueError:
        return len(values)


def _rank(candidate: SelectionCandidate, policy: SelectionPolicy) -> tuple:
    catalog_rank = 0 if policy.prefer_catalogued and candidate.catalogued else int(policy.prefer_catalogued)
    return (
        _index(candidate.ref, policy.preferred),
        _index(candidate.ref.provider, policy.provider_order),
        catalog_rank,
        candidate.stable_order,
        candidate.ref.provider,
        candidate.ref.model,
    )


def select_model(request: SelectionRequest) -> ModelSelection:
    """Apply hard constraints, then deterministic policy preferences."""

    accepted: list[SelectionCandidate] = []
    rejected: list[CandidateRejection] = []
    for candidate in request.candidates:
        reasons = _rejections(candidate, request.constraints)
        (rejected.append(CandidateRejection(candidate.ref, reasons))
         if reasons else accepted.append(candidate))

    if request.explicit is not None:
        selected = next((item for item in accepted if item.ref == request.explicit), None)
        if selected is None:
            if not any(item.ref == request.explicit for item in rejected):
                rejected.append(CandidateRejection(request.explicit, ("not_in_universe",)))
            return ModelSelection(
                None, (), tuple(rejected), SelectionReason.EXPLICIT_UNAVAILABLE,
                request.purpose, request.policy.name,
            )
        return ModelSelection(
            selected, (selected,), tuple(rejected), SelectionReason.EXPLICIT_MATCH,
            request.purpose, request.policy.name,
        )

    eligible = tuple(sorted(accepted, key=lambda item: _rank(item, request.policy)))
    if not eligible:
        return ModelSelection(
            None, (), tuple(rejected), SelectionReason.NO_ELIGIBLE_CANDIDATE,
            request.purpose, request.policy.name,
        )
    selected = eligible[0]
    reason = (SelectionReason.PREFERRED_MATCH if selected.ref in request.policy.preferred
              else SelectionReason.POLICY_DEFAULT)
    return ModelSelection(selected, eligible, tuple(rejected), reason, request.purpose, request.policy.name)


__all__ = [
    "CapabilityRequirements", "CandidateRejection", "ModelSelection",
    "SelectionCandidate", "SelectionConstraints", "SelectionPolicy",
    "SelectionReason", "SelectionRequest", "build_selection_candidate", "select_model",
]
