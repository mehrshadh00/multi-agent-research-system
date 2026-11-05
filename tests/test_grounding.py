from research_studio.grounding import audit_claim_grounding


class GroundingLLM:
    def __init__(self, response):
        self.response = response

    def complete(self, system, user):
        return self.response


SOURCES = [
    {
        "id": "S1",
        "title": "A study",
        "url": "https://example.org/study",
        "snippet": "The study observed an association in a small sample.",
    }
]


def test_grounding_auditor_returns_claim_level_verdicts():
    llm = GroundingLLM(
        '{"assessments":[{"claim_id":"C1","verdict":"partially_supported",'
        '"reason":"The snippet reports an association, not causation."}]}'
    )
    result = audit_claim_grounding("The intervention caused improvement [S1].", SOURCES, llm)
    assert result["status"] == "completed"
    assert result["assessments"][0]["verdict"] == "partially_supported"
    assert result["assessments"][0]["source_ids"] == ["S1"]


def test_grounding_auditor_does_not_accept_unknown_claim_ids():
    llm = GroundingLLM(
        '{"assessments":[{"claim_id":"C99","verdict":"supported","reason":"No."}]}'
    )
    result = audit_claim_grounding("A claim [S1].", SOURCES, llm)
    assert result["status"] == "partial"
    assert result["assessments"][0]["verdict"] == "not_assessed"


def test_grounding_auditor_handles_invalid_json_without_crashing():
    result = audit_claim_grounding("A claim [S1].", SOURCES, GroundingLLM("not json"))
    assert result["status"] == "unavailable"
    assert result["assessments"] == []


def test_grounding_auditor_skips_reports_without_valid_citations():
    result = audit_claim_grounding("A claim [S99].", SOURCES, GroundingLLM("not json"))
    assert result["status"] == "no_cited_claims"
    assert result["assessments"] == []
