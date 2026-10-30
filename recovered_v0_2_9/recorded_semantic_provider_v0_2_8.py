from __future__ import annotations
import json
from pathlib import Path
from normalized_task import NormalizedTask
from semantic_contract import validate_task

class RecordedPredictionMissing(KeyError):
    pass

class RecordedSemanticProvider:
    """Replay model interpretations without another model/API call."""
    def __init__(self, path: str | Path):
        self.path=Path(path)
        self.predictions=json.loads(self.path.read_text(encoding="utf-8"))

    def interpret(self, request: str) -> NormalizedTask:
        if request not in self.predictions:
            raise RecordedPredictionMissing(request)
        payload=dict(self.predictions[request])
        payload["raw_request"]=request
        return validate_task(NormalizedTask.from_dict(payload))
