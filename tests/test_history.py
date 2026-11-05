from research_studio.history import result_from_state


def test_completed_run_can_be_restored_from_saved_artifacts():
    state = {
        "run_id": "run-123",
        "status": "completed",
        "inputs": {"topic": "AI in science", "depth": "Standard", "audience": "Researchers"},
        "stages": {"planning": {"status": "completed"}},
        "artifacts": {
            "planning": {"plan": "Plan", "tracks": ["Landscape"]},
            "research": [{"id": "S1", "title": "Paper"}],
            "audit": {"findings": ["Need corroboration."]},
            "synthesis": "# Report",
            "citation_validation": {
                "citation_audit": [],
                "citation_stats": {
                    "known_sources": 1,
                    "cited_sources": 1,
                    "unknown_ids": [],
                    "uncited_ids": [],
                },
            },
            "grounding": {"status": "completed", "assessments": []},
        },
        "events": [{"agent": "Research Director", "message": "Complete"}],
    }

    result = result_from_state(state)

    assert result["run_id"] == "run-123"
    assert result["topic"] == "AI in science"
    assert result["report"] == "# Report"
    assert result["tracks"] == ["Landscape"]
    assert result["sources"][0]["id"] == "S1"
    assert result["events"] == state["events"]


def test_incomplete_or_failed_runs_cannot_be_restored():
    try:
        result_from_state({"status": "failed", "artifacts": {}})
    except ValueError as exc:
        assert "Only completed" in str(exc)
    else:
        raise AssertionError("Failed runs must not be loaded as completed reports.")
