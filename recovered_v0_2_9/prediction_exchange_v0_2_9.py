from __future__ import annotations
import json
from pathlib import Path
class PredictionExchangeError(ValueError): pass
def normalize_predictions(obj, valid_ids):
    if isinstance(obj,list):
        obj={x["id"]:x["prediction"] for x in obj}
    if not isinstance(obj,dict): raise PredictionExchangeError("predictions must be a mapping or list")
    unknown=set(obj)-set(valid_ids)
    if unknown: raise PredictionExchangeError(f"unknown case ids: {sorted(unknown)}")
    for k,v in obj.items():
        if not isinstance(v,dict): raise PredictionExchangeError(f"prediction {k} must be an object")
    return obj
def load_predictions(path,valid_ids):
    return normalize_predictions(json.loads(Path(path).read_text(encoding="utf-8")),valid_ids)
