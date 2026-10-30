"""Reproducible model-evaluation run identity for v0.2.10."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
import hashlib
from typing import Any, Mapping

from .semantic_provider_config import SemanticProviderConfig


def _digest(payload: bytes, field_name: str) -> str:
    if not isinstance(payload, bytes):
        raise TypeError(f"{field_name}_bytes_required")
    return hashlib.sha256(payload).hexdigest()


def _aware(value: datetime, field_name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field_name}_timezone_required")
    return value


def _required_text(value: str, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


@dataclass(frozen=True)
class EvaluationRunManifest:
    run_id: str
    provider: str
    model_id: str
    policy_version: str
    case_set_id: str
    case_set_sha256: str
    prompt_sha256: str
    schema_sha256: str
    started_at: datetime
    sdk_version: str | None = None
    request_parameters: Mapping[str, Any] = field(default_factory=dict)
    completed_at: datetime | None = None
    response_ids: tuple[str, ...] = ()
    usage: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        config: SemanticProviderConfig,
        prompt_bytes: bytes,
        schema_bytes: bytes,
        case_set_id: str,
        case_set_bytes: bytes,
        policy_version: str,
        started_at: datetime,
        sdk_version: str | None = None,
    ) -> "EvaluationRunManifest":
        if not isinstance(config, SemanticProviderConfig):
            raise TypeError("semantic_provider_config_invalid")
        return cls(
            run_id=_required_text(run_id, "run_id_required"),
            provider=config.provider,
            model_id=config.model_id,
            policy_version=_required_text(
                policy_version, "policy_version_required"
            ),
            case_set_id=_required_text(case_set_id, "case_set_id_required"),
            case_set_sha256=_digest(case_set_bytes, "case_set"),
            prompt_sha256=_digest(prompt_bytes, "prompt"),
            schema_sha256=_digest(schema_bytes, "schema"),
            started_at=_aware(started_at, "started_at"),
            sdk_version=sdk_version,
            request_parameters=dict(config.request_parameters),
        )

    def finish(
        self,
        *,
        completed_at: datetime,
        response_ids: tuple[str, ...] = (),
        usage: Mapping[str, Any] | None = None,
    ) -> "EvaluationRunManifest":
        completed = _aware(completed_at, "completed_at")
        if completed < self.started_at:
            raise ValueError("completed_at_before_started_at")
        clean_ids: list[str] = []
        for response_id in response_ids:
            if not isinstance(response_id, str) or not response_id.strip():
                raise ValueError("response_id_invalid")
            clean_ids.append(response_id.strip())
        if usage is not None and not isinstance(usage, Mapping):
            raise TypeError("usage_invalid")
        return replace(
            self,
            completed_at=completed,
            response_ids=tuple(clean_ids),
            usage=dict(usage or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "provider": self.provider,
            "model_id": self.model_id,
            "policy_version": self.policy_version,
            "case_set_id": self.case_set_id,
            "case_set_sha256": self.case_set_sha256,
            "prompt_sha256": self.prompt_sha256,
            "schema_sha256": self.schema_sha256,
            "started_at": self.started_at.isoformat(),
            "sdk_version": self.sdk_version,
            "request_parameters": dict(self.request_parameters),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at is not None
                else None
            ),
            "response_ids": list(self.response_ids),
            "usage": dict(self.usage),
        }
