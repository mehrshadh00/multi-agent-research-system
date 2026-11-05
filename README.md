# Aether — Multi-Agent Research Studio

**Research, made visible.** A visual research workspace that turns a question into an inspectable, source-linked report.

## Current workflow
1. **Research Director** plans 4–6 focused research tracks.
2. **Evidence Researcher** searches tracks concurrently (up to four workers), deduplicates URLs, and assigns stable source IDs.
3. **Fact & Bias Auditor** reviews the collected search snippets for gaps, limitations, potential bias, and contradictions.
4. **Synthesis Writer** drafts a structured report using the supplied evidence and source IDs.
5. **Citation Validator** checks whether report citation IDs exist in the retrieved source register and flags uncited sources.
6. **Evidence Grounding Auditor** performs an advisory, claim-level review of cited report lines against the associated search snippets.

The Streamlit dashboard displays agent state changes and activity events while the live workflow is running. Completed missions can be reopened from the recent history panel, and the complete run result plus execution trace can be exported as JSON. Each stage has an explicit profile describing its role, objective, expected inputs, outputs, and tools. The persisted trace stores bounded input/output snapshots so a run can be inspected after completion. Independent web searches are dispatched concurrently (up to four workers); results are collected in track order to keep source IDs deterministic. DuckDuckGo is the zero-key default, while Tavily is an optional override when `TAVILY_API_KEY` is present.

## Important architectural distinction
The current release is a **sequential, role-based multi-agent workflow**. The roles use a shared LLM provider with different instructions; they are not independent concurrent agents, and the critic is not a formal verification system. This keeps the execution trace understandable while the workflow is being hardened.

## Checkpointed execution (v0.3)
Each live run is saved to a local SQLite database at `.aether_data/aether.sqlite3`. Every stage transition and successful stage output is committed as a checkpoint. If a provider fails, the run is marked failed and the dashboard offers a **Resume from failed stage** action. Completed earlier stages are restored from SQLite and are not called again; the selected failed stage and all downstream stages are rerun.

The six checkpointed stages are planning, research, audit, synthesis, citation validation, and evidence grounding. Attempt counts, timestamps, errors, input/output previews, agent profile metadata, and run events are stored with each run. The store is local to the app filesystem; on ephemeral hosting such as a restarted Streamlit Community Cloud container, local SQLite data may be lost. Use a persistent volume or managed database before relying on long-term run history.

## Architecture
`Streamlit UI → ResearchOrchestrator → Planner → Concurrent DuckDuckGo/Tavily Search → Critic → Writer → Citation ID Validator → Claim Grounding Auditor`

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

## Free Live Research setup (recommended)

Aether defaults to **Gemini + DuckDuckGo** so you can run the full live workflow without an OpenAI API subscription or a paid search API:

1. Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/apikey).
2. Add the key to your local `.streamlit/secrets.toml` or Streamlit Community Cloud → App → Settings → Secrets:
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   LLM_PROVIDER = "gemini"
   GEMINI_MODEL = "gemini-3.8-flash"
   ```
3. Restart/redeploy Aether and select **Live Research**. DuckDuckGo search is automatic and needs no API key.

The Gemini Developer API offers a free tier for selected models, subject to model-specific rate limits and availability. Free-tier data handling terms differ from paid tiers; review Google's current terms before sending sensitive or confidential material. Free quotas can change or be exhausted.

### Optional providers

- **OpenAI:** set `LLM_PROVIDER = "openai"`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL`. OpenAI API usage is billed separately from ChatGPT subscriptions.
- **Tavily:** add `TAVILY_API_KEY` to use Tavily instead of the default DuckDuckGo search. Without it, DuckDuckGo remains active.

Never commit API keys. The example file `.streamlit/secrets.toml.example` documents all supported settings.
 
## Run with Docker

The container exposes Streamlit on port 8501 and includes a health check. Docker Compose also mounts a named volume so SQLite checkpoints survive container recreation.

```bash
# Optional: export your provider keys before starting
export GEMINI_API_KEY="your-gemini-api-key"
# Optional: export TAVILY_API_KEY to override DuckDuckGo search
docker compose up --build -d
```

Open http://localhost:8501. To stop the app, run `docker compose down`. The named `aether_data` volume is retained; add `-v` only if you intentionally want to delete saved missions.

## Deploy on Streamlit Community Cloud

1. Create a new app from this repository.
2. Select branch `main` and main file `app.py`.
3. Add `GEMINI_API_KEY` in the app's Secrets settings. No Tavily key is required.
4. Deploy and open the generated app URL.

**Persistence note:** Streamlit Community Cloud local storage is not a durable database. Saved run history may disappear when the app container is recycled. Use Docker with a persistent volume or move `SQLiteRunStore` to a managed database for durable production history.

## Development checks
```bash
ruff check .
pytest -q
```

Tests use fake providers for deterministic orchestration checks; they do not consume API credits.

## Known limitations
- Search snippets are not full-page retrieval, and no independent source corroboration is guaranteed.
- Citation ID validation checks reference consistency. A separate LLM grounding pass assesses cited lines against snippets, but this remains advisory and is not independent verification.
- The planner, critic, and writer are sequential roles sharing one LLM provider, not separate autonomous or concurrent model instances.
- Critic output is advisory, not a guarantee of correctness.
- Search coverage can be incomplete; human verification remains necessary.
- Gemini free-tier quotas are limited and can change. If you select OpenAI or configure a paid Tavily account, those providers may incur charges.

## Release scope and next steps
The current portfolio release includes the six-stage research workflow, concurrent search tracks, agent I/O trace, SQLite checkpoints, failed-stage recovery, completed-run history, JSON export, deterministic tests, and Docker packaging. The remaining production extensions are external durable storage, provider-level retry/backoff and rate limiting, independent model selection per agent, and stronger source corroboration. These are intentionally documented as future work rather than implied capabilities.
