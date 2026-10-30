from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from normalized_task import NormalizedTask
from semantic_contract import validate_task


class SemanticProviderError(RuntimeError):
    pass


class SemanticGroundingError(SemanticProviderError):
    pass


RISK_KEYS = [
    "REVERSIBILITY", "BLAST_RADIUS", "FINANCIAL", "LEGAL_REGULATORY",
    "SECURITY", "DATA_LOSS", "REPUTATIONAL"
]


def build_provider_schema() -> dict[str, Any]:
    """Strict-output schema for the model boundary.

    The core contract stores feature_evidence as a dict, but the provider schema uses
    a list so strict JSON Schema does not depend on dynamic object keys. The adapter
    normalizes the list back into the core representation after generation.
    """
    enums = {
        "actions": ["CREATE","MODIFY","DIAGNOSE","REVIEW","RESEARCH","ANALYZE_EVIDENCE","ANALYZE_DATA","DESIGN","OPTIMIZE","OPERATE"],
        "preservation": ["BEHAVIOR","API","OUTPUT","MEANING","QUALITY","COMPATIBILITY"],
        "performance_dimensions": ["LATENCY","THROUGHPUT","MEMORY","COMPUTE","FINANCIAL_COST","TOKEN_COST","QUALITY_ACCURACY","RESOURCE_UTILIZATION","GENERAL"],
        "evidence_policy": ["OPEN","SUPPLIED_ONLY","CURRENT_EXTERNAL","TRACEABLE"],
        "ui_requirements": ["UI","PRODUCTION","ACCESSIBILITY","RESPONSIVE","STATEFUL_UI"],
        "architecture": ["DESIGN_BEFORE_BUILD","CHANGE","BOUNDARIES","MIGRATION"],
        "external_state": ["EMAIL","CALENDAR","PUBLISHING","DATABASE","FILES","ACCOUNT","OTHER"],
        "execution": ["MULTI_STEP","LARGE_WORKLOAD","PARALLELIZABLE","INDEPENDENT_REVIEW","EXPLICIT_MULTI_AGENT","HUMAN_APPROVAL","STATEFUL"],
        "capabilities": ["WEB_CURRENT_EVIDENCE","FILE_READ","EMAIL_READ","EMAIL_WRITE","CALENDAR_READ","CALENDAR_WRITE","EXTERNAL_WRITE","AUTHORIZATION","CONNECTION_STATE","HUMAN_APPROVAL","PERSISTENT_STATE_READ","PERSISTENT_STATE_WRITE"],
    }
    props: dict[str, Any] = {}
    for key, values in enums.items():
        props[key] = {"type": "array", "items": {"type": "string", "enum": values}}

    props["risks"] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {k: {"type": "integer", "minimum": 0, "maximum": 4} for k in RISK_KEYS},
        "required": list(RISK_KEYS),
    }
    props["feature_evidence"] = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "feature": {"type": "string"},
                "source": {"type": "string", "enum": ["EXPLICIT","INFERRED","UNKNOWN","CONTRADICTION"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence_span": {"type": ["string", "null"]},
                "rationale": {"type": ["string", "null"]},
            },
            "required": ["feature","source","confidence","evidence_span","rationale"],
        },
    }
    props["unknowns"] = {"type": "array", "items": {"type": "string"}}
    props["contradictions"] = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": props,
        "required": list(props),
    }


def _default_prompt() -> str:
    path = Path(__file__).with_name("semantic_interpreter_prompt_v0_2_7.md")
    return path.read_text(encoding="utf-8")


def _payload_to_core(payload: dict[str, Any], request: str) -> dict[str, Any]:
    payload = dict(payload)
    evidence_items = payload.pop("feature_evidence", [])
    evidence_map = {}
    for item in evidence_items:
        item = dict(item)
        feature = item.pop("feature")
        evidence_map[feature] = item
    payload["feature_evidence"] = evidence_map
    payload["raw_request"] = request
    # Zero-valued risks are semantically absent in the core contract.
    payload["risks"] = {k: int(v) for k, v in payload.get("risks", {}).items() if int(v) != 0}
    return payload


def _validate_grounding(task: NormalizedTask) -> None:
    request = task.raw_request
    for feature, ev in task.feature_evidence.items():
        if ev.source == "EXPLICIT":
            if not ev.evidence_span:
                raise SemanticGroundingError(f"explicit feature {feature} has no evidence_span")
            if ev.evidence_span not in request:
                raise SemanticGroundingError(
                    f"explicit feature {feature} has evidence_span not grounded in request: {ev.evidence_span!r}"
                )


class OpenAIResponsesSemanticProvider:
    """Model-backed semantic interpreter using Responses API Structured Outputs.

    Provider/model choice remains outside the deterministic compiler core. A client may
    be injected for tests or alternative transports. If omitted, the OpenAI SDK client
    is created lazily.
    """

    def __init__(self, client=None, model: str = "gpt-5.6-terra", prompt: str | None = None):
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise SemanticProviderError("openai package is required when no client is injected") from exc
            client = OpenAI()
        self.client = client
        self.model = model
        self.prompt = prompt or _default_prompt()
        self.schema = build_provider_schema()

    def interpret(self, request: str) -> NormalizedTask:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": request},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "normalized_task_v0_2_7",
                    "description": "Normalized semantic task contract for the Prompt & Agent Compiler.",
                    "strict": True,
                    "schema": self.schema,
                }
            },
        )
        output_text = getattr(response, "output_text", None)
        if not output_text:
            parsed = getattr(response, "output_parsed", None)
            if parsed is None:
                raise SemanticProviderError("model response contained neither output_text nor output_parsed")
            payload = parsed if isinstance(parsed, dict) else dict(parsed)
        else:
            try:
                payload = json.loads(output_text)
            except json.JSONDecodeError as exc:
                raise SemanticProviderError("structured response was not valid JSON") from exc

        task = NormalizedTask.from_dict(_payload_to_core(payload, request))
        validate_task(task)
        _validate_grounding(task)
        return task
