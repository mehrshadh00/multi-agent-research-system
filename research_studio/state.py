from __future__ import annotations

from uuid import uuid4

from .store import utc_now

STAGE_ORDER = (
    "planning",
    "research",
    "audit",
    "synthesis",
    "citation_validation",
    "grounding",
)

STAGE_LABELS = {
    "planning": "Research Director",
    "research": "Evidence Researcher",
    "audit": "Fact & Bias Auditor",
    "synthesis": "Synthesis Writer",
    "citation_validation": "Citation Validator",
    "grounding": "Evidence Grounding Auditor",
}


def new_run_state(topic: str, depth: str, audience: str) -> dict:
    now = utc_now()
    return {
        "run_id": uuid4().hex,
        "status": "running",
        "created_at": now,
        "updated_at": now,
        "inputs": {"topic": topic, "depth": depth, "audience": audience},
        "artifacts": {},
        "events": [],
        "stages": {
            name: {
                "status": "pending",
                "attempts": 0,
                "started_at": None,
                "finished_at": None,
                "error": None,
            }
            for name in STAGE_ORDER
        },
    }


def reset_from(state: dict, stage_name: str) -> None:
    if stage_name not in STAGE_ORDER:
        raise ValueError(f"Unknown stage: {stage_name}")
    start = STAGE_ORDER.index(stage_name)
    for name in STAGE_ORDER[start:]:
        state["stages"][name].update(
            status="pending",
            started_at=None,
            finished_at=None,
            error=None,
        )
        state["artifacts"].pop(name, None)
