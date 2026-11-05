from __future__ import annotations

import re
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

from .agents import profile_for
from .grounding import audit_claim_grounding
from .providers import LLMProvider, SearchProvider
from .state import STAGE_LABELS, new_run_state, reset_from
from .store import SQLiteRunStore

Event = dict[str, str]
EventCallback = Callable[[Event], None]


class ResearchStageError(RuntimeError):
    def __init__(self, run_id: str, stage: str, message: str):
        super().__init__(message)
        self.run_id = run_id
        self.stage = stage


class ResearchOrchestrator:
    """Checkpointed planner → researcher → auditor → writer workflow."""

    def __init__(self, settings, search_provider=None, llm_provider=None, store=None):
        self.search = search_provider or SearchProvider(settings.tavily_api_key)
        self.llm = llm_provider or LLMProvider(
            settings.openai_api_key, settings.openai_model
        )
        self.store = store or SQLiteRunStore()

    def run(
        self,
        topic: str,
        depth: str,
        audience: str,
        on_event: EventCallback | None = None,
        run_id: str | None = None,
        resume_from: str | None = None,
    ) -> dict:
        if run_id:
            state = self.store.load(run_id)
            if state is None:
                raise ValueError(f"Research run '{run_id}' was not found.")
            expected = {"topic": topic, "depth": depth, "audience": audience}
            if state["inputs"] != expected:
                raise ValueError("Resume inputs do not match the saved research run.")
            if resume_from:
                reset_from(state, resume_from)
        else:
            if resume_from:
                raise ValueError("A run_id is required when resuming a stage.")
            state = new_run_state(topic, depth, audience)

        state["status"] = "running"
        self.store.save(state)

        def emit(stage: str, message: str, status: str = "info") -> None:
            event = {
                "stage": stage,
                "agent": STAGE_LABELS[stage],
                "profile": profile_for(stage).public_dict(),
                "message": message,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            event.update(getattr(emit, "payload", {}))
            if hasattr(emit, "payload"):
                del emit.payload
            state["events"].append(event)
            self.store.save(state)
            if on_event:
                on_event(event)

        def execute(stage: str, operation, input_data: dict):
            stage_state = state["stages"][stage]
            input_preview = self._preview(input_data)
            if stage_state["status"] == "completed":
                emit(stage, "Restored completed checkpoint; skipped execution.", "skipped")
                return state["artifacts"][stage]

            stage_state["status"] = "running"
            stage_state["attempts"] += 1
            stage_state["started_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            stage_state["finished_at"] = None
            stage_state["error"] = None
            self.store.save(state)
            emit.payload = {"input_preview": input_preview}
            emit(stage, f"Starting attempt {stage_state['attempts']}.", "running")
            try:
                output = operation()
                state["artifacts"][stage] = output
                stage_state["status"] = "completed"
                stage_state["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self.store.save(state)
                emit.payload = {"output_preview": self._preview(output)}
                emit(stage, "Stage checkpoint committed.", "complete")
                return output
            except Exception as exc:
                stage_state["status"] = "failed"
                stage_state["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                stage_state["error"] = f"{type(exc).__name__}: {exc}"
                state["status"] = "failed"
                self.store.save(state)
                emit(stage, stage_state["error"], "failed")
                raise ResearchStageError(
                    state["run_id"], stage, stage_state["error"]
                ) from exc

        try:
            planning = execute(
                "planning", self._plan(topic, depth, emit),
                {"topic": topic, "research_depth": depth},
            )
            tracks = planning["tracks"]
            sources = execute(
                "research", self._research(topic, tracks, emit),
                {"topic": topic, "tracks": tracks},
            )
            audit = execute(
                "audit", self._audit(topic, sources, emit),
                {"topic": topic, "sources": self._source_manifest(sources)},
            )
            report = execute(
                "synthesis",
                self._synthesize(topic, audience, planning["plan"], sources, audit, emit),
                {
                    "topic": topic, "audience": audience,
                    "plan": planning["plan"],
                    "source_ids": [source["id"] for source in sources],
                    "audit_findings": audit["findings"],
                },
            )
            citation = execute(
                "citation_validation",
                self._validate_citations(report, sources, emit),
                {"report_excerpt": report[:1200], "source_ids": [s["id"] for s in sources]},
            )
            grounding = execute(
                "grounding", self._ground(report, sources, emit),
                {"report_excerpt": report[:1200], "source_ids": [s["id"] for s in sources]},
            )
        except ResearchStageError:
            raise

        state["status"] = "completed"
        self.store.save(state)
        return {
            "run_id": state["run_id"],
            "status": state["status"],
            "stages": state["stages"],
            "topic": topic,
            "tracks": tracks,
            "sources": sources,
            "audit": audit["findings"],
            "citation_audit": citation["citation_audit"],
            "citation_stats": citation["citation_stats"],
            "grounding": grounding,
            "report": report,
            "events": state["events"],
            "mode": "live",
        }

    def _plan(self, topic: str, depth: str, emit):
        def operation():
            emit("planning", "Breaking the question into focused research tracks.", "running")
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
            return {"plan": plan, "tracks": tracks}
        return operation

    def _research(self, topic: str, tracks: list[str], emit):
        def operation():
            # Search requests are independent. Dispatch concurrently, then consume
            # futures in track order so source IDs and traces remain deterministic.
            workers = min(4, max(1, len(tracks)))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = []
                for index, track in enumerate(tracks, start=1):
                    emit(
                        "research",
                        f"Dispatching track {index}/{len(tracks)}: {track}",
                        "running",
                    )
                    futures.append(
                        (index, track, executor.submit(
                            self.search.search, f"{topic} {track}", max_results=3
                        ))
                    )

                sources = []
                seen = set()
                for index, track, future in futures:
                    results = future.result()
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
                                "track": track,
                            }
                        )
                        added += 1
                    emit(
                        "research",
                        f"Track {index} returned {len(results)} results; added {added} new sources.",
                        "complete",
                    )
            if not sources:
                raise RuntimeError(
                    "Search returned no usable sources. Try a narrower question or check Tavily."
                )
            return sources
        return operation

    def _audit(self, topic: str, sources: list[dict], emit):
        def operation():
            emit("audit", f"Reviewing {len(sources)} source summaries.", "running")
            response = self.llm.complete(
                "You are a skeptical research auditor. Identify unsupported claims, "
                "source limitations, likely bias, contradictions and missing evidence. "
                "Do not invent facts. Return concise bullet points.",
                f"Question: {topic}\nEvidence:\n{self._evidence_text(sources)}",
            )
            findings = [line.strip(" -•") for line in response.splitlines() if line.strip()]
            return {"raw": response, "findings": findings}
        return operation

    def _synthesize(self, topic, audience, plan, sources, audit, emit):
        def operation():
            emit("synthesis", "Drafting a source-linked report.", "running")
            return self.llm.complete(
                "You are a careful research analyst. Write a useful Markdown report "
                "for the requested audience. Use only supplied evidence. Cite inline "
                "using exact source IDs such as [S1]. Distinguish evidence from "
                "interpretation, include limitations and unanswered questions. "
                "Never fabricate citations.",
                f"Question: {topic}\nAudience: {audience}\nTracks:\n{plan}"
                f"\nEvidence:\n{self._evidence_text(sources)}\n"
                f"Auditor findings:\n{audit['raw']}\n"
                "Include executive summary, findings by theme, implications, "
                "limitations, conclusion and a source list mapping IDs to URLs.",
            )
        return operation

    def _validate_citations(self, report: str, sources: list[dict], emit):
        def operation():
            known_ids = {source["id"] for source in sources}
            cited_ids = set(re.findall(r"\[(S\d+)\]", report))
            unknown_ids = sorted(cited_ids - known_ids, key=lambda value: int(value[1:]))
            uncited_ids = sorted(known_ids - cited_ids, key=lambda value: int(value[1:]))
            findings = []
            if unknown_ids:
                findings.append("Unknown citation IDs found in report: " + ", ".join(unknown_ids))
            if uncited_ids:
                findings.append("Retrieved sources not cited in report: " + ", ".join(uncited_ids))
            if not cited_ids:
                findings.append("The report contains no recognized inline source citations.")
            emit(
                "citation_validation",
                f"Found {len(cited_ids & known_ids)} valid source IDs and {len(unknown_ids)} unknown IDs.",
                "warning" if findings else "complete",
            )
            return {
                "citation_audit": findings,
                "citation_stats": {
                    "known_sources": len(known_ids),
                    "cited_sources": len(cited_ids & known_ids),
                    "unknown_ids": unknown_ids,
                    "uncited_ids": uncited_ids,
                },
            }
        return operation

    def _ground(self, report: str, sources: list[dict], emit):
        def operation():
            emit("grounding", "Checking cited claims against their source snippets.", "running")
            result = audit_claim_grounding(report, sources, self.llm)
            emit(
                "grounding",
                f"Grounding review {result['status']}: assessed {len(result['assessments'])} cited claims.",
                "warning" if result["status"] in {"partial", "unavailable"} else "complete",
            )
            return result
        return operation

    @staticmethod
    def _preview(value, limit: int = 1600) -> str:
        rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
        return rendered[:limit] + ("…" if len(rendered) > limit else "")

    @staticmethod
    def _source_manifest(sources: list[dict]) -> list[dict]:
        return [
            {"id": source["id"], "title": source["title"], "domain": source["domain"]}
            for source in sources
        ]

    @staticmethod
    def _evidence_text(sources: list[dict]) -> str:
        return "\n\n".join(
            f"[{source['id']}] {source['title']} ({source['url']})\n{source['snippet']}"
            for source in sources
        )
