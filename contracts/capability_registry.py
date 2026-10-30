"""Runtime capability registry for compiled execution specifications.

Capabilities are runtime facts, not semantic labels. Missing registrations
remain UNKNOWN and are never silently promoted to AVAILABLE.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class CapabilityStatus(str, Enum):
    AVAILABLE = "available"
    CONSTRAINED = "constrained"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class CapabilityGateState(str, Enum):
    READY = "ready"
    ADAPT_REQUIRED = "adapt_required"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    status: CapabilityStatus
    limitation: str | None = None
    fallback: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("capability_name_required")
        if not isinstance(self.status, CapabilityStatus):
            raise TypeError("capability_status_invalid")


@dataclass(frozen=True)
class CapabilityResolution:
    required: tuple[CapabilitySpec, ...]
    optional: tuple[CapabilitySpec, ...]
    state: CapabilityGateState
    reasons: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return self.state is CapabilityGateState.BLOCKED


class CapabilityRegistry:
    def __init__(self, specs: Iterable[CapabilitySpec] = ()) -> None:
        self._specs: dict[str, CapabilitySpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: CapabilitySpec) -> None:
        if not isinstance(spec, CapabilitySpec):
            raise TypeError("capability_spec_invalid")
        self._specs[spec.name] = spec

    def get(self, name: str) -> CapabilitySpec:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("capability_name_required")
        return self._specs.get(
            name,
            CapabilitySpec(name=name, status=CapabilityStatus.UNKNOWN),
        )

    @staticmethod
    def _unique(names: Iterable[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for name in names:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("capability_name_required")
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return tuple(ordered)

    def resolve(
        self,
        *,
        required: Iterable[str],
        optional: Iterable[str] = (),
    ) -> CapabilityResolution:
        required_names = self._unique(required)
        required_set = set(required_names)
        optional_names = tuple(
            name for name in self._unique(optional) if name not in required_set
        )

        required_specs = tuple(self.get(name) for name in required_names)
        optional_specs = tuple(self.get(name) for name in optional_names)
        reasons: list[str] = []

        unavailable = [
            spec.name
            for spec in required_specs
            if spec.status is CapabilityStatus.UNAVAILABLE
        ]
        unknown = [
            spec.name
            for spec in required_specs
            if spec.status is CapabilityStatus.UNKNOWN
        ]
        constrained = [
            spec.name
            for spec in required_specs
            if spec.status is CapabilityStatus.CONSTRAINED
        ]

        if unavailable:
            state = CapabilityGateState.BLOCKED
            reasons.extend(
                f"mandatory_capability_unavailable:{name}" for name in unavailable
            )
        elif unknown:
            state = CapabilityGateState.UNKNOWN
            reasons.extend(
                f"mandatory_capability_unknown:{name}" for name in unknown
            )
        elif constrained:
            state = CapabilityGateState.ADAPT_REQUIRED
            reasons.extend(
                f"mandatory_capability_constrained:{name}" for name in constrained
            )
        else:
            state = CapabilityGateState.READY

        for spec in optional_specs:
            if spec.status is CapabilityStatus.UNAVAILABLE:
                reasons.append(f"optional_capability_unavailable:{spec.name}")
            elif spec.status is CapabilityStatus.UNKNOWN:
                reasons.append(f"optional_capability_unknown:{spec.name}")
            elif spec.status is CapabilityStatus.CONSTRAINED:
                reasons.append(f"optional_capability_constrained:{spec.name}")

        return CapabilityResolution(
            required=required_specs,
            optional=optional_specs,
            state=state,
            reasons=tuple(reasons),
        )
