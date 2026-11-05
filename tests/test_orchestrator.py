from research_studio.orchestrator import ResearchOrchestrator


class FakeSearch:
    def search(self, query, max_results=3):
        if "Landscape" in query:
            return [
                {
                    "title": "Primary paper",
                    "url": "https://example.org/paper",
                    "content": "A useful evidence snippet.",
                },
                {
                    "title": "Secondary report",
                    "url": "https://example.org/report",
                    "content": "A second evidence snippet.",
                },
            ]
        return [
            {
                "title": "Duplicate paper",
                "url": "https://example.org/paper",
                "content": "Duplicate should be ignored.",
            }
        ]


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        if self.calls == 1:
            return "1. Landscape and key concepts\n2. Risks and limitations"
        if self.calls == 2:
            return "- Search snippets do not prove causation."
        return "## Findings\nThe evidence suggests a cautious conclusion [S1]."


def test_pipeline_emits_live_events_and_deduplicates_sources():
    emitted = []
    orchestrator = ResearchOrchestrator(
        settings=object(),
        search_provider=FakeSearch(),
        llm_provider=FakeLLM(),
    )

    result = orchestrator.run(
        "AI in scientific discovery",
        "Standard",
        "Researchers",
        on_event=emitted.append,
    )

    assert result["mode"] == "live"
    assert len(result["tracks"]) == 2
    assert [source["id"] for source in result["sources"]] == ["S1", "S2"]
    assert emitted == result["events"]
    assert emitted[0]["status"] == "running"
    assert any("Searching track 1/2" in event["message"] for event in emitted)
    assert emitted[-1]["agent"] == "Citation Validator"


def test_pipeline_reports_unknown_and_uncited_citations():
    class CitationLLM(FakeLLM):
        def complete(self, system, user):
            self.calls += 1
            if self.calls == 1:
                return "1. Landscape and key concepts"
            if self.calls == 2:
                return "- Need independent corroboration."
            return "Claim [S1]. Unsupported reference [S99]."

    result = ResearchOrchestrator(
        settings=object(),
        search_provider=FakeSearch(),
        llm_provider=CitationLLM(),
    ).run("AI research", "Quick scan", "Researchers")

    assert result["citation_stats"]["unknown_ids"] == ["S99"]
    assert result["citation_stats"]["uncited_ids"] == ["S2"]
    assert any("Unknown citation IDs" in item for item in result["citation_audit"])


def test_pipeline_fails_clearly_when_search_has_no_sources():
    class EmptySearch:
        def search(self, query, max_results=3):
            return []

    orchestrator = ResearchOrchestrator(
        settings=object(),
        search_provider=EmptySearch(),
        llm_provider=FakeLLM(),
    )

    try:
        orchestrator.run("Unanswerable topic", "Standard", "Researchers")
    except RuntimeError as exc:
        assert "no usable sources" in str(exc)
    else:
        raise AssertionError("Expected a clear failure when no sources are returned.")
