from __future__ import annotations

import re
import time

import plotly.graph_objects as go
import streamlit as st

from research_studio.config import settings
from research_studio.demo import demo_result
from research_studio.orchestrator import ResearchOrchestrator

st.set_page_config(page_title="Aether Research Studio", page_icon="✳", layout="wide")
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700;800&display=swap');
.stApp{background:radial-gradient(ellipse at 12% 0%,#14243a 0%,#080b12 48%);color:#edf4ff;font-family:Manrope,sans-serif}
[data-testid="stSidebar"]{background:#0b111d;border-right:1px solid #202d40}
.block-container{padding-top:2rem;max-width:1500px}
.hero{padding:28px 30px;border:1px solid #25344a;border-radius:22px;background:linear-gradient(115deg,#1b3148,#111627);margin-bottom:20px}
.eyebrow,.role,.metric .label,.event .time{color:#62e6dc;font:11px 'DM Mono';letter-spacing:.14em;text-transform:uppercase}
.hero h1{font-size:38px;letter-spacing:-.04em;margin:8px 0}.hero p,.desc,.small-muted{color:#91a0b5}
.agent,.metric,.evidence{background:#111a29;border:1px solid #26354b;border-radius:15px;padding:15px}
.agent{min-height:132px}.name{font-size:16px;font-weight:800;margin:7px 0}.desc{font-size:12px}
.metric .value{font-size:25px;font-weight:800;margin-top:5px}
.evidence{margin:8px 0;background:#0d1624}.evidence a{color:#70dcd6}
.event{border-left:2px solid #3d5975;padding:3px 0 13px 14px;margin-left:6px}
.stButton>button[kind="primary"]{background:linear-gradient(90deg,#37cfc6,#7d8df5);color:#071019;border:0;border-radius:11px;font-weight:800}
</style>
<div class="hero"><div class="eyebrow">✳ AETHER / INTELLIGENCE SYSTEMS</div><h1>Research, made visible.</h1><p>A multi-agent research studio that turns a question into an evidence-backed report — with every stage in view.</p></div>
""",
    unsafe_allow_html=True,
)

AGENTS = [
    ("01 / PLANNER", "Research Director", "Breaks the question into focused research tracks."),
    ("02 / SCOUT", "Evidence Researcher", "Finds sources and extracts evidence."),
    ("03 / CRITIC", "Fact & Bias Auditor", "Challenges claims, gaps and source limitations."),
    ("04 / AUTHOR", "Synthesis Writer", "Builds a structured report from reviewed evidence."),
]


def agent_cards(statuses=None):
    statuses = statuses or {}
    cols = st.columns(4)
    for col, (role, name, desc) in zip(cols, AGENTS):
        state = statuses.get(name, "Standby")
        col.markdown(
            f'<div class="agent"><div class="role">{role}</div>'
            f'<div class="name">{name}</div><div class="desc">{desc}</div>'
            f'<p style="color:#62e6dc;font:10px monospace">● {state.upper()}</p></div>',
            unsafe_allow_html=True,
        )


def pipeline(active=""):
    labels = ["Question", "Planning", "Research", "Critique", "Synthesis", "Validation", "Report"]
    active_index = labels.index(active) if active in labels else -1
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(range(len(labels))),
            y=[0] * len(labels),
            mode="lines",
            line=dict(color="#34445c", width=3),
            hoverinfo="skip",
        )
    )
    for index, label in enumerate(labels):
        color = "#62e6dc" if index <= active_index else "#26364b"
        fig.add_trace(
            go.Scatter(
                x=[index],
                y=[0],
                mode="markers+text",
                text=[label],
                textposition="bottom center",
                marker=dict(size=25, color=color, line=dict(color="#d7e9ff", width=1)),
                textfont=dict(color="#dce8f7", size=10),
                hoverinfo="text",
            )
        )
    fig.update_layout(
        height=140,
        margin=dict(l=10, r=10, t=10, b=30),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[-0.3, len(labels) - 0.7]),
        yaxis=dict(visible=False, range=[-0.4, 0.4]),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def progress_for_event(event):
    agent = event["agent"]
    message = event["message"]
    status = event["status"]
    if agent == "Research Director":
        return 0.08 if status == "running" else 0.18
    if agent == "Evidence Researcher":
        match = re.search(r"track (\d+)/(\d+)", message, re.IGNORECASE)
        if match:
            current, total = map(int, match.groups())
            st.session_state["aether_track_total"] = total
            return 0.2 + 0.4 * (current - 1) / max(total, 1)
        match = re.search(r"Track (\d+) returned", message)
        if match:
            current, total = int(match.group(1)), max(
                1, st.session_state.get("aether_track_total", 1)
            )
            return 0.2 + 0.4 * current / total
        return 0.2 if status == "running" else 0.62
    if agent == "Fact & Bias Auditor":
        return 0.68 if status == "running" else 0.78
    if agent == "Synthesis Writer":
        return 0.82 if status == "running" else 0.9
    return 0.96


with st.sidebar:
    st.markdown("## ✳ AETHER")
    st.caption("MULTI-AGENT RESEARCH STUDIO")
    mode = st.radio("Execution mode", ["Guided Demo", "Live Research"])
    st.divider()
    st.markdown("**System readiness**")
    st.write("OpenAI · " + ("🟢 configured" if settings.openai_api_key else "⚪ missing"))
    st.write("Tavily · " + ("🟢 configured" if settings.tavily_api_key else "⚪ missing"))
    st.caption("Live mode requires both keys. Demo uses fictional placeholder evidence.")
    st.divider()
    st.caption("AETHER / v0.2.0")

left, right = st.columns([2.4, 1])
with left:
    topic = st.text_area(
        "RESEARCH QUESTION",
        placeholder="How are multimodal AI agents changing scientific discovery?",
        height=95,
    )
with right:
    depth = st.select_slider(
        "RESEARCH DEPTH",
        ["Quick scan", "Standard", "Deep dive"],
        value="Standard",
    )
    audience = st.selectbox(
        "REPORT AUDIENCE",
        ["Technical leadership", "General audience", "Researchers", "Product & strategy teams"],
    )
launch = st.button("✳  Launch research mission", type="primary", use_container_width=True)
st.markdown("### The research pipeline")
pipeline()
agent_cards()

if launch:
    if not topic.strip():
        st.warning("Enter a research question.")
    elif mode == "Live Research" and (
        not settings.openai_api_key or not settings.tavily_api_key
    ):
        st.error("Live Research requires OPENAI_API_KEY and TAVILY_API_KEY.")
    else:
        st.session_state["aether_track_total"] = 1
        status_box = st.status("Initializing research mission…", expanded=True)
        progress_bar = st.progress(0)
        agent_statuses = {name: "Standby" for _, name, _ in AGENTS}
        trace_events = []
        live_agents = st.empty()
        live_trace = st.empty()
        live_pipeline = st.empty()

        def render_event(event):
            trace_events.append(event)
            agent_statuses[event["agent"]] = event["status"]
            stage_map = {
                "Research Director": "Planning",
                "Evidence Researcher": "Research",
                "Fact & Bias Auditor": "Critique",
                "Synthesis Writer": "Synthesis",
                "Citation Validator": "Validation",
            }
            progress_bar.progress(min(99, int(progress_for_event(event) * 100)))
            status_box.write(f"**{event['agent']}** · {event['message']}")
            with live_agents.container():
                agent_cards(agent_statuses)
            with live_pipeline.container():
                pipeline(stage_map.get(event["agent"], ""))
            with live_trace.container():
                st.markdown("**Live event stream**")
                for item in trace_events[-10:]:
                    st.caption(
                        f"{item['timestamp']} · {item['agent']} · {item['status'].upper()}"
                    )
                    st.write(item["message"])

        if mode == "Guided Demo":
            demo_steps = [
                ("Research Director", "Decomposing the question…"),
                ("Evidence Researcher", "Collecting illustrative source cards…"),
                ("Fact & Bias Auditor", "Reviewing caveats…"),
                ("Synthesis Writer", "Preparing report preview…"),
            ]
            for name, message in demo_steps:
                render_event(
                    {
                        "agent": name,
                        "message": message,
                        "status": "running",
                        "timestamp": time.strftime("%H:%M:%S"),
                    }
                )
                time.sleep(0.35)
                render_event(
                    {
                        "agent": name,
                        "message": "Demo stage complete.",
                        "status": "complete",
                        "timestamp": time.strftime("%H:%M:%S"),
                    }
                )
            result = demo_result(topic, depth, audience)
            result["events"] = trace_events
        else:
            try:
                result = ResearchOrchestrator(settings).run(
                    topic.strip(),
                    depth,
                    audience,
                    on_event=render_event,
                )
            except (RuntimeError, ValueError) as exc:
                status_box.update(label="Mission failed", state="error")
                st.error(str(exc))
                result = None
            except Exception as exc:
                status_box.update(label="Mission failed", state="error")
                st.error(f"Unexpected provider error: {exc}")
                result = None

        if result:
            progress_bar.progress(100)
            status_box.update(label="Research mission complete", state="complete", expanded=False)
            st.session_state["aether_result"] = result

result = st.session_state.get("aether_result")
if result:
    st.markdown("---")
    st.markdown("## Mission control")
    cols = st.columns(4)
    metrics = [
        len(result["sources"]),
        len(result["tracks"]),
        len(result["audit"]),
        result["mode"].upper(),
    ]
    for col, label, value in zip(
        cols,
        ["SOURCES REVIEWED", "RESEARCH TRACKS", "AUDIT FINDINGS", "EXECUTION"],
        metrics,
    ):
        col.markdown(
            f'<div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{value}</div></div>',
            unsafe_allow_html=True,
        )

    tabs = st.tabs(
        [
            "📄 Final report",
            "🔎 Evidence room",
            "🧭 Research plan",
            "🛡 Critic review",
            "🔗 Citation audit",
            "⚡ Activity trace",
        ]
    )
    with tabs[0]:
        st.markdown(result["report"])
        st.download_button(
            "Download report · Markdown",
            result["report"],
            "aether-research-report.md",
            "text/markdown",
        )
    with tabs[1]:
        for source in result["sources"]:
            source_id = source.get("id", "DEMO")
            st.markdown(
                f'<div class="evidence"><b>[{source_id}] {source["title"]}</b><br>'
                f'<span class="small-muted">{source["domain"]} · {source["quality"]}</span><br>'
                f'{source["snippet"]}<br>'
                f'<a href="{source["url"]}" target="_blank">Open source ↗</a></div>',
                unsafe_allow_html=True,
            )
    with tabs[2]:
        for index, track in enumerate(result["tracks"], 1):
            st.markdown(f"**Track {index}: {track}**")
    with tabs[3]:
        for finding in result["audit"]:
            st.warning(finding)
    with tabs[4]:
        citation_stats = result.get("citation_stats")
        if citation_stats:
            cols = st.columns(3)
            cols[0].metric("Known sources", citation_stats["known_sources"])
            cols[1].metric("Cited sources", citation_stats["cited_sources"])
            cols[2].metric("Unknown IDs", len(citation_stats["unknown_ids"]))
            if result.get("citation_audit"):
                for finding in result["citation_audit"]:
                    st.warning(finding)
            else:
                st.success("All citation IDs in the report map to retrieved sources.")
            st.caption(
                "This checks citation ID consistency only. It does not prove that a "
                "source supports the sentence citing it."
            )
        else:
            st.info("Demo mode contains fictional evidence; citation validation is not performed.")
    with tabs[5]:
        for event in result["events"]:
            st.markdown(
                f'<div class="event"><div class="time">{event["agent"].upper()} · '
                f'{event.get("status", "info").upper()}</div>'
                f'<div>{event["message"]}</div></div>',
                unsafe_allow_html=True,
            )
    st.caption(
        "Search snippets are not full-page verification. Generated conclusions require "
        "human review; citation ID validation is not source-grounding verification."
    )
