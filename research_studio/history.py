from __future__ import annotations


def result_from_state(state: dict) -> dict:
    """Rebuild the dashboard result from a completed persisted checkpoint."""
    if state.get("status") != "completed":
        raise ValueError("Only completed research runs can be loaded as reports.")

    artifacts = state.get("artifacts", {})
    required = {
        "planning",
        "research",
        "audit",
        "synthesis",
        "citation_validation",
        "grounding",
    }
    missing = sorted(required - artifacts.keys())
    if missing:
        raise ValueError("Saved run is missing completed artifacts: " + ", ".join(missing))

    return {
        "run_id": state["run_id"],
        "status": "completed",
        "stages": state["stages"],
        "topic": state["inputs"]["topic"],
        "tracks": artifacts["planning"]["tracks"],
        "sources": artifacts["research"],
        "audit": artifacts["audit"]["findings"],
        "citation_audit": artifacts["citation_validation"]["citation_audit"],
        "citation_stats": artifacts["citation_validation"]["citation_stats"],
        "grounding": artifacts["grounding"],
        "report": artifacts["synthesis"],
        "events": state.get("events", []),
        "mode": "live",
    }
