from research_studio import orchestrator


class FakeSearchProvider:
    def __init__(self, api_key):
        self.calls = []

    def search(self, query, max_results=5):
        self.calls.append(query)
        return [
            {
                "url": "https://research.example.org/paper",
                "title": "Research paper",
                "content": "A source snippet for testing.",
            },
            {
                "url": "https://data.example.org/report",
                "title": "Data report",
                "content": "Another source snippet.",
            },
        ]


class FakeLLMProvider:
    def __init__(self, api_key, model):
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        if "research planner" in system:
            return "1. Current research landscape\n2. Technical challenges"
        if "skeptical research auditor" in system:
            return "- Search snippets need verification\n- More primary sources are needed"
        return "# Research report\n\nEvidence suggests a useful direction [S1]."


def test_orchestrator_emits_inspectable_events(monkeypatch):
    monkeypatch.setattr(orchestrator, "SearchProvider", FakeSearchProvider)
    monkeypatch.setattr(orchestrator, "LLMProvider", FakeLLMProvider)

    class Settings:
        tavily_api_key = "test"
        openai_api_key = "test"
        openai_model = "test-model"

    emitted = []
    result = orchestrator.ResearchOrchestrator(Settings()).run(
        "AI research",
        "Standard",
        "Researchers",
        on_event=emitted.append,
    )

    assert result["mode"] == "live"
    assert len(result["sources"]) == 2
    assert result["events"] == emitted
    assert any("Searching track 1/2" in event["message"] for event in emitted)
    assert any("Captured source" in event["message"] for event in emitted)
    assert emitted[-1]["agent"] == "Synthesis Writer"
    assert emitted[-1]["message"] == "Report draft completed."


def test_orchestrator_deduplicates_sources(monkeypatch):
    monkeypatch.setattr(orchestrator, "SearchProvider", FakeSearchProvider)
    monkeypatch.setattr(orchestrator, "LLMProvider", FakeLLMProvider)

    class Settings:
        tavily_api_key = "test"
        openai_api_key = "test"
        openai_model = "test-model"

    result = orchestrator.ResearchOrchestrator(Settings()).run(
        "AI research", "Quick scan", "General audience"
    )
    assert len(result["sources"]) == 2
    assert len({source["url"] for source in result["sources"]}) == 2
