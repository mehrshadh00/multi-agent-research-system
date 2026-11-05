from __future__ import annotations
import time
from html import escape
import plotly.graph_objects as go
import streamlit as st
from research_studio.config import settings
from research_studio.orchestrator import ResearchOrchestrator
from research_studio.demo import demo_result

st.set_page_config(page_title="Aether Research Studio", page_icon="✳", layout="wide")
st.markdown("""
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
""",unsafe_allow_html=True)

AGENTS=[("01 / PLANNER","Research Director","Breaks the question into focused research tracks."),("02 / SCOUT","Evidence Researcher","Finds sources and extracts evidence."),("03 / CRITIC","Fact & Bias Auditor","Challenges claims, gaps and source limitations."),("04 / AUTHOR","Synthesis Writer","Builds a structured report from reviewed evidence.")]

def agent_cards(statuses=None):
    statuses=statuses or {}
    cols=st.columns(4)
    for col,(role,name,desc) in zip(cols,AGENTS):
        state=statuses.get(name,"Standby")
        col.markdown(f'<div class="agent"><div class="role">{role}</div><div class="name">{name}</div><div class="desc">{desc}</div><p style="color:#62e6dc;font:10px monospace">● {state.upper()}</p></div>',unsafe_allow_html=True)

def pipeline(active=""):
    labels=["Question","Planning","Research","Critique","Synthesis","Report"]
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=list(range(6)),y=[0]*6,mode="lines",line=dict(color="#34445c",width=3),hoverinfo="skip"))
    for i,label in enumerate(labels):
        fig.add_trace(go.Scatter(x=[i],y=[0],mode="markers+text",text=[label],textposition="bottom center",
          marker=dict(size=25,color="#62e6dc" if label==active else "#26364b",line=dict(color="#d7e9ff",width=1)),
          textfont=dict(color="#dce8f7",size=11),hoverinfo="text"))
    fig.update_layout(height=140,margin=dict(l=10,r=10,t=10,b=30),showlegend=False,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",xaxis=dict(visible=False,range=[-.3,5.3]),yaxis=dict(visible=False,range=[-.4,.4]))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

def research_map(result):
    """Visualize the four-agent workflow and its collected evidence."""
    sources = result["sources"][:12]
    xs = [0, 1.4, 2.8, 4.2]
    ys = [0, 0, 0, 0]
    labels = ["Research Director", "Evidence Researcher", "Fact & Bias Auditor", "Synthesis Writer"]
    kinds = ["agent"] * 4
    edges = [(0, 1), (1, 2), (2, 3)]
    for index, source in enumerate(sources):
        node = len(xs)
        xs.append(1.4 + ((index % 3) - 1) * 0.32)
        ys.append(-1.0 - (index // 3) * 0.72)
        labels.append(f"S{index + 1} · {source['domain']}")
        kinds.append("source")
        edges.extend([(1, node), (node, 2)])
    edge_x, edge_y = [], []
    for start, end in edges:
        edge_x.extend([xs[start], xs[end], None])
        edge_y.extend([ys[start], ys[end], None])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1.5, color="#3c5873"), hoverinfo="skip", showlegend=False))
    custom = ["Agent"] * 4 + [source["title"] for source in sources]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=labels, textposition="bottom center", marker=dict(size=[28 if kind == "agent" else 17 for kind in kinds], color=["#62e6dc" if kind == "agent" else "#7d8df5" for kind in kinds], line=dict(color="#dce8f7", width=1)), textfont=dict(color="#dce8f7", size=10), customdata=custom, hovertemplate="%{text}<br>%{customdata}<extra></extra>", showlegend=False))
    fig.update_layout(height=max(360, 250 + len(sources) // 3 * 90), margin=dict(l=15, r=15, t=25, b=65), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False, range=[-0.6, 4.8]), yaxis=dict(visible=False), title=dict(text="AGENT COLLABORATION / EVIDENCE FLOW", font=dict(size=12, color="#91a0b5")))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("The researcher routes collected sources to the auditor, then the writer synthesizes reviewed evidence.")

with st.sidebar:
    st.markdown("## ✳ AETHER");st.caption("MULTI-AGENT RESEARCH STUDIO")
    mode=st.radio("Execution mode",["Guided Demo","Live Research"])
    st.divider();st.markdown("**System readiness**")
    st.write("OpenAI · "+("🟢 configured" if settings.openai_api_key else "⚪ missing"))
    st.write("Tavily · "+("🟢 configured" if settings.tavily_api_key else "⚪ missing"))
    st.caption("Live mode requires both keys. Demo uses fictional placeholder evidence.")
    st.divider();st.caption("AETHER / v0.1.0")

left,right=st.columns([2.4,1])
with left: topic=st.text_area("RESEARCH QUESTION",placeholder="How are multimodal AI agents changing scientific discovery?",height=95)
with right:
    depth=st.select_slider("RESEARCH DEPTH",["Quick scan","Standard","Deep dive"],value="Standard")
    audience=st.selectbox("REPORT AUDIENCE",["Technical leadership","General audience","Researchers","Product & strategy teams"])
launch=st.button("✳  Launch research mission",type="primary",use_container_width=True)
st.markdown("### The research pipeline");pipeline();agent_cards()

if launch:
    if not topic.strip(): st.warning("Enter a research question.")
    elif mode=="Live Research" and (not settings.openai_api_key or not settings.tavily_api_key):
        st.error("Live Research requires OPENAI_API_KEY and TAVILY_API_KEY.")
    else:
        status=st.status("Initializing research mission…",expanded=True);bar=st.progress(0)
        if mode=="Guided Demo":
            steps=[("Research Director","Decomposing the question…"),("Evidence Researcher","Collecting illustrative source cards…"),("Fact & Bias Auditor","Reviewing caveats…"),("Synthesis Writer","Preparing report preview…")]
            for i,(name,msg) in enumerate(steps):
                status.write(f"**{name}** — {msg}");bar.progress((i+1)*22);time.sleep(.35)
            result=demo_result(topic,depth,audience);bar.progress(100);status.update(label="Demo mission complete",state="complete",expanded=False)
        else:
            try:
                progress_by_agent = {"Research Director": 15, "Evidence Researcher": 45, "Fact & Bias Auditor": 72, "Synthesis Writer": 90}
                def on_event(event):
                    status.write(f"**{event['agent']}** — {event['message']}")
                    bar.progress(progress_by_agent.get(event["agent"], 50))
                result=ResearchOrchestrator(settings).run(topic.strip(),depth,audience,on_event=on_event)
                bar.progress(100);status.update(label="Research mission complete",state="complete",expanded=False)
            except (RuntimeError,ValueError) as exc:
                status.update(label="Mission failed",state="error");st.error(str(exc));result=None
        st.session_state["aether_result"]=result

result=st.session_state.get("aether_result")
if result:
    st.markdown("---");st.markdown("## Mission control")
    cols=st.columns(4)
    for col,label,value in zip(cols,["SOURCES REVIEWED","RESEARCH TRACKS","AUDIT FINDINGS","EXECUTION"],[len(result["sources"]),len(result["tracks"]),len(result["audit"]),result["mode"].upper()]):
        col.markdown(f'<div class="metric"><div class="label">{label}</div><div class="value">{value}</div></div>',unsafe_allow_html=True)
    st.markdown("### Agent activity");agent_cards({name:"Complete" for _,name,_ in AGENTS})
    report_tab,map_tab,evidence_tab,plan_tab,audit_tab,trace_tab=st.tabs(["📄 Final report","🕸 Research map","🔎 Evidence room","🧭 Research plan","🛡 Critic review","⚡ Activity trace"])
    with report_tab:
        st.markdown(result["report"]);st.download_button("Download report · Markdown",result["report"],"aether-research-report.md","text/markdown")
    with map_tab:
        research_map(result)
    with evidence_tab:
        for src in result["sources"]:
            title = escape(src["title"])
            domain = escape(src["domain"])
            quality = escape(src["quality"])
            snippet = escape(src["snippet"])
            url = escape(src["url"], quote=True)
            st.markdown(f'<div class="evidence"><b>{title}</b><br><span class="small-muted">{domain} · {quality}</span><br>{snippet}<br><a href="{url}" target="_blank" rel="noopener noreferrer">Open source ↗</a></div>',unsafe_allow_html=True)
    with plan_tab:
        for i,track in enumerate(result["tracks"],1): st.markdown(f"**Track {i}: {track}**")
    with audit_tab:
        for finding in result["audit"]: st.warning(finding)
    with trace_tab:
        for event in result["events"]: st.markdown(f'<div class="event"><div class="time">{event["agent"].upper()}</div><div>{event["message"]}</div></div>',unsafe_allow_html=True)
    st.caption("Demo evidence is fictional. Live results require human verification.")
