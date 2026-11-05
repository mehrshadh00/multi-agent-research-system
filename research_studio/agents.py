from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AgentProfile:
    stage: str
    name: str
    role: str
    objective: str
    expected_inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    tools: tuple[str, ...] = ()

    def public_dict(self) -> dict:
        """JSON-friendly profile for the UI and persisted run trace."""
        data = asdict(self)
        data["expected_inputs"] = list(self.expected_inputs)
        data["outputs"] = list(self.outputs)
        data["tools"] = list(self.tools)
        return data


AGENT_PROFILES = {
    "planning": AgentProfile(
        stage="planning",
        name="Research Director",
        role="Planner",
        objective="Decompose the research question into focused, non-overlapping tracks.",
        expected_inputs=("topic", "research_depth"),
        outputs=("plan", "tracks"),
    ),
    "research": AgentProfile(
        stage="research",
        name="Evidence Researcher",
        role="Researcher",
        objective="Search each track concurrently and build a deduplicated source register.",
        expected_inputs=("topic", "tracks"),
        outputs=("sources", "source_ids"),
        tools=("Tavily Search",),
    ),
    "audit": AgentProfile(
        stage="audit",
        name="Fact & Bias Auditor",
        role="Critic",
        objective="Identify evidence gaps, likely bias, contradictions, and source limitations.",
        expected_inputs=("topic", "sources"),
        outputs=("raw_findings", "findings"),
    ),
    "synthesis": AgentProfile(
        stage="synthesis",
        name="Synthesis Writer",
        role="Writer",
        objective="Produce an audience-aware report grounded in the supplied source register.",
        expected_inputs=("topic", "audience", "plan", "sources", "audit_findings"),
        outputs=("markdown_report",),
    ),
    "citation_validation": AgentProfile(
        stage="citation_validation",
        name="Citation Validator",
        role="Validator",
        objective="Check citation IDs against the source register and flag missing references.",
        expected_inputs=("markdown_report", "source_ids"),
        outputs=("citation_stats", "citation_findings"),
    ),
    "grounding": AgentProfile(
        stage="grounding",
        name="Evidence Grounding Auditor",
        role="Grounding Reviewer",
        objective="Assess cited report claims against the matching retrieved snippets.",
        expected_inputs=("markdown_report", "cited_source_snippets"),
        outputs=("claim_assessments", "grounding_status"),
    ),
}


def profile_for(stage: str) -> AgentProfile:
    try:
        return AGENT_PROFILES[stage]
    except KeyError as exc:
        raise ValueError(f"Unknown agent stage: {stage}") from exc
