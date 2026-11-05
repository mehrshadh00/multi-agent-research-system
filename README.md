# Aether — Multi-Agent Research Studio

**Research, made visible.** A visual workspace that turns a question into an evidence-backed report through an inspectable four-agent pipeline.

## Experience
- Research Director: decomposes the question into independent tracks.
- Evidence Researcher: searches the web and collects source snippets.
- Fact & Bias Auditor: identifies gaps, unsupported claims and source limitations.
- Synthesis Writer: creates a structured Markdown report with source IDs.
- Streamlit dashboard: workflow map, agent cards, evidence room, audit findings, activity trace and downloadable report.
- Guided Demo: explores the UI without API keys. All sample sources are explicitly fictional.

## Architecture
`Streamlit UI → ResearchOrchestrator → Planner → Tavily Search → Critic → Writer → Report`

Provider adapters are isolated in `research_studio/providers.py`; orchestration is independent of the UI.

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
Open Guided Demo without credentials.

## Live Research credentials
Set environment variables `OPENAI_API_KEY` and `TAVILY_API_KEY`. For Streamlit Community Cloud, add both in App → Settings → Secrets:
```toml
OPENAI_API_KEY = "..."
TAVILY_API_KEY = "..."
```
Never commit secrets. `OPENAI_MODEL` optionally overrides the default `gpt-4.1-mini`.

## Tests
```bash
pytest -q
ruff check .
```

## Limitations
- Live mode uses Tavily search snippets, not full-page verification.
- Generated summaries and reports require human fact-checking.
- Critic review is not a guarantee of correctness.
- Demo Mode is fictional UI preview data, not research output.
- API usage may incur provider charges.

## Roadmap
Streaming agent events and cancellation; claim-to-evidence mapping; contradiction detection; PDF/DOCX export; replayable mission traces; optional LangGraph runtime and persistent research history.
