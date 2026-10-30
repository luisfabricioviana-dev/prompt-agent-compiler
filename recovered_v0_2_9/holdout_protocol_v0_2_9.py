from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).parent
HOLDOUT=ROOT/"blind_holdout_v0_2_9.json"
def load_holdout():
    data=json.loads(HOLDOUT.read_text(encoding="utf-8"))
    if not data.get("frozen") or not data.get("tuning_prohibited"):
        raise RuntimeError("holdout must remain frozen and tuning-prohibited")
    ids=[c["id"] for c in data["cases"]]
    if len(ids)!=len(set(ids)):
        raise RuntimeError("duplicate holdout ids")
    return data
