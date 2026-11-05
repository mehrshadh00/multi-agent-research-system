# Aether — Multi-Agent Research Studio

**Research, made visible.** A visual research workspace that turns a question into an inspectable, source-linked report.

## Current workflow
1. **Research Director** plans 4–6 focused research tracks.
2. **Evidence Researcher** searches each track separately, streams progress events, deduplicates URLs, and assigns stable source IDs.
3. **Fact & Bias Auditor** reviews the collected search snippets for gaps, limitations, potential bias, and contradictions.
4. **Synthesis Writer** drafts a structured report using the supplied evidence and source IDs.
5. **Citation Validator** checks whether report citation IDs exist in the retrieved source register and flags uncited sources.
6. **Evidence Grounding Auditor** performs an advisory, claim-level review of cited report lines against the associated search snippets.

The Streamlit dashboard displays agent state changes and activity events while the live workflow is running. The orchestration callback is UI-agnostic and can later feed a CLI, websocket, or persisted event log.

## Important architectural distinction
The current release is a **sequential, role-based multi-agent workflow**. The roles use a shared LLM provider with different instructions; they are not independent concurrent agents, and the critic is not a formal verification system. This keeps the execution trace understandable while the workflow is being hardened.

## Checkpointed execution (v0.3)
Each live run is saved to a local SQLite database at `.aether_data/aether.sqlite3`. Every stage transition and successful stage output is committed as a checkpoint. If a provider fails, the run is marked failed and the dashboard offers a **Resume from failed stage** action. Completed earlier stages are restored from SQLite and are not called again; the selected failed stage and all downstream stages are rerun.

The six checkpointed stages are planning, research, audit, synthesis, citation validation, and evidence grounding. Attempt counts, timestamps, errors, and run events are stored with each run. The store is local to the app filesystem; on ephemeral hosting such as a restarted Streamlit Community Cloud container, local SQLite data may be lost. Use a persistent volume or managed database before relying on long-term run history.

## Architecture
`Streamlit UI → ResearchOrchestrator → Planner → Track-by-track Tavily Search → Critic → Writer → Citation ID Validator → Claim Grounding Auditor`

Provider adapters live in `research_studio/providers.py`. The orchestrator accepts injectable search and LLM providers so its behavior can be tested without network access or API credentials.

## Quick start
```bash
git clone https://github.com/mehrshadh00/multi-agent-research-system.git
cd multi-agent-research-system
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app.py
```

Choose **Guided Demo** to explore the interface without credentials. Demo evidence is fictional and is clearly labelled.

## Live Research credentials
Set `OPENAI_API_KEY` and `TAVILY_API_KEY` as environment variables. For Streamlit Community Cloud, add them in App → Settings → Secrets:
```toml
OPENAI_API_KEY = "..."
TAVILY_API_KEY = "..."
```
Never commit secrets. `OPENAI_MODEL` optionally overrides the default `gpt-4.1-mini`.

## Development checks
```bash
ruff check .
pytest -q
```

Tests use fake providers for deterministic orchestration checks; they do not consume API credits.

## Known limitations
- Tavily snippets are not full-page retrieval, and no independent source corroboration is guaranteed.
- Citation ID validation checks reference consistency. A separate LLM grounding pass assesses cited lines against snippets, but this remains advisory and is not independent verification.
- The planner, critic, and writer are sequential roles sharing one LLM provider, not separate autonomous or concurrent model instances.
- Critic output is advisory, not a guarantee of correctness.
- Search coverage can be incomplete; human verification remains necessary.
- API usage may incur provider charges.

## Engineering roadmap
- Stronger claim segmentation and independently corroborated evidence checks.
- Distributed task execution, provider-specific retry/backoff policies, and structured outputs.
- Persistent run history across deployments and interactive trace replay.
- Independent agent configuration and optional LangGraph state machine.
- Contradiction detection, richer source quality signals, and PDF/DOCX export.
