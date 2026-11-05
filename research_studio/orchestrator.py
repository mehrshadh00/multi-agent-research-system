from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

from .grounding import audit_claim_grounding
from .providers import LLMProvider, SearchProvider

Event = dict[str, str]
EventCallback = Callable[[Event], None]


class ResearchOrchestrator:
    """Run an observable planner → researcher → auditor → writer workflow.

    The callback is deliberately UI-agnostic: callers can stream events to
    Streamlit, a CLI, a websocket, or a persisted event log.
    """

    def __init__(self, settings, search_provider=None, llm_provider=None):
        self.search = search_provider or SearchProvider(settings.tavily_api_key)
        self.llm = llm_provider or LLMProvider(
            settings.openai_api_key, settings.openai_model
        )

    def run(
        self,
        topic: str,
        depth: str,
        audience: str,
        on_event: EventCallback | None = None,
    ) -> dict:
        events: list[Event] = []

        def emit(agent: str, message: str, status: str = "info") -> None:
            event = {
                "agent": agent,
                "message": message,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            events.append(event)
            if on_event:
                on_event(event)

        emit("Research Director", "Planning research tracks.", "running")
        plan = self.llm.complete(
            "You are a rigorous research planner. Return 4-6 concise, "
            "non-overlapping research tracks as a numbered list. No intro.",
            f"Research question: {topic}\nDepth: {depth}",
        )
        tracks = [
            line.strip(" -0123456789.)")
            for line in plan.splitlines()
            if line.strip()
        ]
        tracks = [track for track in tracks if len(track) > 8][:6] or [topic]
        emit("Research Director", f"Created {len(tracks)} research tracks.", "complete")

        emit("Evidence Researcher", f"Searching {len(tracks)} tracks.", "running")
        sources: list[dict] = []
        seen: set[str] = set()
        for index, track in enumerate(tracks, start=1):
            emit(
                "Evidence Researcher",
                f"Searching track {index}/{len(tracks)}: {track}",
                "running",
            )
            results = self.search.search(f"{topic} {track}", max_results=3)
            added = 0
            for item in results:
                url = item.get("url", "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                domain = urlparse(url).netloc
                sources.append(
                    {
                        "id": f"S{len(sources) + 1}",
                        "title": item.get("title") or domain or "Untitled source",
                        "url": url,
                        "snippet": item.get("content", "")[:1200],
                        "domain": domain,
                        "quality": "Search result · verify before citation",
                    }
                )
                added += 1
            emit(
                "Evidence Researcher",
                f"Track {index} returned {len(results)} results; added {added} new sources.",
                "complete",
            )

        if not sources:
            raise RuntimeError(
                "Search returned no usable sources. Try a narrower question or check Tavily."
            )

        evidence = "\n\n".join(
            f"[{source['id']}] {source['title']} ({source['url']})\n{source['snippet']}"
            for source in sources
        )

        emit("Fact & Bias Auditor", f"Reviewing {len(sources)} source summaries.", "running")
        audit = self.llm.complete(
            "You are a skeptical research auditor. Identify unsupported claims, "
            "source limitations, likely bias, contradictions and missing evidence. "
            "Do not invent facts. Return concise bullet points.",
            f"Question: {topic}\nEvidence:\n{evidence}",
        )
        findings = [line.strip(" -•") for line in audit.splitlines() if line.strip()]
        emit("Fact & Bias Auditor", f"Produced {len(findings)} review findings.", "complete")

        emit("Synthesis Writer", "Drafting a source-linked report.", "running")
        report = self.llm.complete(
            "You are a careful research analyst. Write a useful Markdown report "
            "for the requested audience. Use only supplied evidence. Cite inline "
            "using exact source IDs such as [S1]. Distinguish evidence from "
            "interpretation, include limitations and unanswered questions. "
            "Never fabricate citations.",
            f"Question: {topic}\nAudience: {audience}\nTracks:\n{plan}"
            f"\nEvidence:\n{evidence}\nAuditor findings:\n{audit}\n"
            "Include executive summary, findings by theme, implications, "
            "limitations, conclusion and a source list mapping IDs to URLs.",
        )
        emit("Synthesis Writer", "Report draft generated; checking citation references.", "complete")

        known_ids = {source["id"] for source in sources}
        cited_ids = set(re.findall(r"\[(S\d+)\]", report))
        unknown_ids = sorted(cited_ids - known_ids, key=lambda value: int(value[1:]))
        uncited_ids = sorted(known_ids - cited_ids, key=lambda value: int(value[1:]))
        citation_audit = []
        if unknown_ids:
            citation_audit.append(
                "Unknown citation IDs found in report: " + ", ".join(unknown_ids)
            )
        if uncited_ids:
            citation_audit.append(
                "Retrieved sources not cited in report: " + ", ".join(uncited_ids)
            )
        if not cited_ids:
            citation_audit.append("The report contains no recognized inline source citations.")
        emit(
            "Citation Validator",
            f"Found {len(cited_ids & known_ids)} valid source IDs and "
            f"{len(unknown_ids)} unknown IDs.",
            "warning" if citation_audit else "complete",
        )

        emit("Evidence Grounding Auditor", "Checking cited claims against their source snippets.", "running")
        grounding = audit_claim_grounding(report, sources, self.llm)
        grounding_status = grounding["status"]
        grounding_count = len(grounding["assessments"])
        emit(
            "Evidence Grounding Auditor",
            f"Grounding review {grounding_status}: assessed {grounding_count} cited claims.",
            "warning" if grounding_status in {"partial", "unavailable"} else "complete",
        )

        return {
            "topic": topic,
            "tracks": tracks,
            "sources": sources,
            "audit": findings,
            "citation_audit": citation_audit,
            "grounding": grounding,
            "citation_stats": {
                "known_sources": len(known_ids),
                "cited_sources": len(cited_ids & known_ids),
                "unknown_ids": unknown_ids,
                "uncited_ids": uncited_ids,
            },
            "report": report,
            "events": events,
            "mode": "live",
        }
