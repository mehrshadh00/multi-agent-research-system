from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

from .providers import LLMProvider, SearchProvider


class ResearchOrchestrator:
    """Inspectable four-agent pipeline with optional live event callbacks."""

    def __init__(self, settings):
        self.search = SearchProvider(settings.tavily_api_key)
        self.llm = LLMProvider(settings.openai_api_key, settings.openai_model)

    def run(
        self,
        topic: str,
        depth: str,
        audience: str,
        on_event: Callable[[dict[str, str]], None] | None = None,
    ) -> dict:
        events = []

        def log(agent: str, message: str) -> None:
            event = {"agent": agent, "message": message}
            events.append(event)
            if on_event is not None:
                on_event(event)

        log("Research Director", "Creating independent research tracks.")
        plan = self.llm.complete(
            "You are a rigorous research planner. Return 4-6 concise, non-overlapping "
            "research tracks as a numbered list. No intro.",
            f"Research question: {topic}\nDepth: {depth}",
        )
        tracks = [
            line.strip(" -0123456789.)")
            for line in plan.splitlines()
            if line.strip()
        ]
        tracks = [track for track in tracks if len(track) > 8][:6] or [topic]
        log("Research Director", f"Created {len(tracks)} research tracks.")

        log("Evidence Researcher", f"Searching {len(tracks)} research tracks.")
        raw = []
        for index, track in enumerate(tracks, start=1):
            log("Evidence Researcher", f"Searching track {index}/{len(tracks)}: {track}")
            raw.extend(self.search.search(f"{topic} {track}", max_results=3))

        seen = set()
        sources = []
        for item in raw:
            url = item.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            domain = urlparse(url).netloc
            sources.append(
                {
                    "title": item.get("title") or domain,
                    "url": url,
                    "snippet": item.get("content", "")[:650],
                    "domain": domain,
                    "quality": "Search result · verify before citation",
                }
            )
            log("Evidence Researcher", f"Captured source {len(sources)}: {domain}")

        if not sources:
            raise RuntimeError("Search returned no sources. Try a narrower research question.")

        evidence = "\n\n".join(
            f"[S{i}] {source['title']} ({source['url']})\n{source['snippet']}"
            for i, source in enumerate(sources, 1)
        )
        log("Fact & Bias Auditor", f"Auditing {len(sources)} retrieved source summaries.")
        audit = self.llm.complete(
            "You are a skeptical research auditor. Identify unsupported claims, source "
            "limitations, likely bias, contradictions and missing evidence. Do not invent "
            "facts. Return concise bullet points.",
            f"Question: {topic}\nEvidence:\n{evidence}",
        )
        findings = [line.strip(" -") for line in audit.splitlines() if line.strip()]
        log("Fact & Bias Auditor", f"Produced {len(findings)} audit findings.")

        log("Synthesis Writer", "Synthesizing a source-linked report with explicit limitations.")
        report = self.llm.complete(
            "You are a careful research analyst. Write a useful Markdown report for the "
            "requested audience. Use only supplied evidence. Cite inline as [S1], [S2]. "
            "Distinguish facts from interpretation, include limitations and unanswered "
            "questions. Never fabricate citations.",
            f"Question: {topic}\nAudience: {audience}\nTracks:\n{plan}\nEvidence:\n"
            f"{evidence}\nAuditor findings:\n{audit}\nInclude executive summary, findings "
            "by theme, implications, limitations, conclusion and source list mapping [S#] "
            "to URLs.",
        )
        log("Synthesis Writer", "Report draft completed.")
        return {
            "topic": topic,
            "tracks": tracks,
            "sources": sources,
            "audit": findings,
            "report": report,
            "events": events,
            "mode": "live",
        }
