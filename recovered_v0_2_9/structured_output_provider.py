from __future__ import annotations
import json
from normalized_task import NormalizedTask
from semantic_contract import validate_task


class StructuredOutputProvider:
    """Adapter for structured semantic JSON produced by an external semantic model.

    This class intentionally does not call a model API. The host application supplies
    the structured output, keeping provider/model choice outside the deterministic compiler core.
    """
    def __init__(self, resolver):
        self.resolver=resolver

    def interpret(self, request: str) -> NormalizedTask:
        payload=self.resolver(request)
        if isinstance(payload,str):
            payload=json.loads(payload)
        payload=dict(payload)
        payload["raw_request"]=request
        return validate_task(NormalizedTask.from_dict(payload))
