from research_studio.orchestrator import ResearchOrchestrator
from research_studio.store import SQLiteRunStore


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
        if self.calls == 3:
            return "## Findings\nThe evidence suggests a cautious conclusion [S1]."
        return '{"assessments":[{"claim_id":"C1","verdict":"supported","reason":"The test snippet supports this limited claim."}]}'


def test_pipeline_emits_live_events_and_deduplicates_sources(tmp_path):
    emitted = []
    orchestrator = ResearchOrchestrator(
        settings=object(),
        search_provider=FakeSearch(),
        llm_provider=FakeLLM(),
        store=SQLiteRunStore(tmp_path / 'runs.sqlite3'),
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
    assert emitted[-1]["agent"] == "Evidence Grounding Auditor"


def test_pipeline_reports_unknown_and_uncited_citations(tmp_path):
    class CitationLLM(FakeLLM):
        def complete(self, system, user):
            self.calls += 1
            if self.calls == 1:
                return "1. Landscape and key concepts"
            if self.calls == 2:
                return "- Need independent corroboration."
            if self.calls == 3:
                return "Claim [S1]. Unsupported reference [S99]."
            return '{"assessments":[{"claim_id":"C1","verdict":"partially_supported","reason":"The snippet offers limited support."}]}'

    result = ResearchOrchestrator(
        settings=object(),
        search_provider=FakeSearch(),
        llm_provider=CitationLLM(),
        store=SQLiteRunStore(tmp_path / 'citation-runs.sqlite3'),
    ).run("AI research", "Quick scan", "Researchers")

    assert result["citation_stats"]["unknown_ids"] == ["S99"]
    assert result["citation_stats"]["uncited_ids"] == ["S2"]
    assert any("Unknown citation IDs" in item for item in result["citation_audit"])


def test_pipeline_fails_clearly_when_search_has_no_sources(tmp_path):
    class EmptySearch:
        def search(self, query, max_results=3):
            return []

    orchestrator = ResearchOrchestrator(
        settings=object(),
        search_provider=EmptySearch(),
        llm_provider=FakeLLM(),
        store=SQLiteRunStore(tmp_path / 'empty-runs.sqlite3'),
    )

    try:
        orchestrator.run("Unanswerable topic", "Standard", "Researchers")
    except RuntimeError as exc:
        assert "no usable sources" in str(exc)
    else:
        raise AssertionError("Expected a clear failure when no sources are returned.")


def test_failed_stage_can_resume_without_repeating_completed_work(tmp_path):
    class RetryLLM:
        def __init__(self):
            self.calls = 0
            self.fail_audit_once = True

        def complete(self, system, user):
            self.calls += 1
            if "rigorous research planner" in system:
                return "1. Landscape and key concepts\\n2. Risks and limitations"
            if "skeptical research auditor" in system:
                if self.fail_audit_once:
                    self.fail_audit_once = False
                    raise TimeoutError("temporary provider timeout")
                return "- Evidence is limited."
            if "careful research analyst" in system:
                return "## Findings\\nA cautious conclusion [S1]."
            return (
                '{"assessments":[{"claim_id":"C1","verdict":"supported",'
                '"reason":"The snippet supports this limited statement."}]}'
            )

    store = SQLiteRunStore(tmp_path / "resume.sqlite3")
    llm = RetryLLM()
    orchestrator = ResearchOrchestrator(
        settings=object(),
        search_provider=FakeSearch(),
        llm_provider=llm,
        store=store,
    )

    try:
        orchestrator.run("AI research", "Standard", "Researchers")
    except Exception as exc:
        run_id = exc.run_id
        assert exc.stage == "audit"
    else:
        raise AssertionError("Expected the first audit attempt to fail.")

    failed = store.load(run_id)
    assert failed["stages"]["planning"]["status"] == "completed"
    assert failed["stages"]["research"]["status"] == "completed"
    assert failed["stages"]["audit"]["status"] == "failed"
    assert failed["stages"]["planning"]["attempts"] == 1

    result = orchestrator.run(
        "AI research",
        "Standard",
        "Researchers",
        run_id=run_id,
        resume_from="audit",
    )

    assert result["status"] == "completed"
    assert result["stages"]["planning"]["attempts"] == 1
    assert result["stages"]["research"]["attempts"] == 1
    assert result["stages"]["audit"]["attempts"] == 2
    assert result["stages"]["synthesis"]["status"] == "completed"
    assert llm.calls == 5
    assert any("Restored completed checkpoint" in e["message"] for e in result["events"])
