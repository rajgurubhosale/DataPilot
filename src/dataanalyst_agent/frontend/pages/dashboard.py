import json
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="AI Dashboard", page_icon="📊", layout="wide")

HINT_GROUP = {
    "histogram": "Distributions",
    "box": "Distributions",
    "bar": "Comparisons",
    "pareto": "Comparisons",
    "line": "Trends",
    "scatter": "Relationships",
    "heatmap": "Segments & Risk",
}
TAB_ORDER = ["Distributions", "Comparisons", "Segments & Risk", "Relationships", "Trends"]


def fmt(v) -> str:
    """Readable numbers: 2666 -> 2,666 | 14.60 -> 14.6"""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    return str(v)


def get_group(q: dict) -> str:
    """Group by planner hint, falling back to the chart's trace type."""
    group = HINT_GROUP.get(q.get("chart_hint"))
    if group:
        return group
    traces = (q.get("figure") or {}).get("data") or []
    t = traces[0] if traces else {}
    kind = t.get("type")
    if kind in ("box", "histogram"):
        return "Distributions"
    if kind == "heatmap":
        return "Segments & Risk"
    if kind == "scatter":
        return "Trends" if "lines" in (t.get("mode") or "") else "Relationships"
    return "Comparisons"


def load_dashboard():
    """Use the current run; fall back to the newest saved JSON."""
    if st.session_state.get("dashboard"):
        return st.session_state["dashboard"], st.session_state.get("target_column"), False
    files = [p for p in [*Path("data").glob("*/final_output.json"), Path("data/final_output.json")] if p.exists()]
    if files:
        newest = max(files, key=lambda p: p.stat().st_mtime)
        try:
            return json.loads(newest.read_text(encoding="utf-8")), None, True
        except Exception:
            pass
    return None, None, False


def card(qid: str, q: dict):
    facts = q.get("facts") or {}
    with st.container(border=True):
        st.markdown(f"**{q.get('question', '')}**")
        if facts.get("answer"):
            st.caption(facts["answer"])
        try:
            fig = go.Figure(q["figure"])
            fig.update_layout(
                template="plotly_white",
                height=360,
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig, use_container_width=True, theme=None, key=f"fig_{qid}")
        except Exception as e:
            st.warning(f"Could not render chart: {e}")

        with st.expander("Details"):
            for label, val in (facts.get("key_numbers") or {}).items():
                st.write(f"**{label.replace('_', ' ').title()}:** {fmt(val)}")
            if facts.get("caveats"):
                st.caption(f"Caveats: {facts['caveats']}")
            st.caption(f"Columns: {', '.join(q.get('columns', []))} · Attempts: {q.get('attempts', 1)}")
            if q.get("code"):
                st.code(q["code"], language="python")


dash, target, from_disk = load_dashboard()
if not dash:
    st.info("Upload a dataset and run the analysis first.")
    st.page_link("app.py", label="Back to Upload", icon="🏠")
    st.stop()

qs = dash.get("questions", {})
ok = {k: v for k, v in qs.items() if v.get("success")}
bad = {k: v for k, v in qs.items() if not v.get("success")}

st.title("📊 AI Analysis Dashboard")
st.caption(f"Dataset: **{dash.get('dataset', 'Uploaded dataset')}**")
if from_disk:
    st.warning("Showing the last saved run, not a new one.")

first = next(iter(ok.values()), None)
if first and (first.get("facts") or {}).get("key_numbers"):
    kpis = list(first["facts"]["key_numbers"].items())[:4]
    if kpis:
        for col, (label, val) in zip(st.columns(len(kpis)), kpis):
            col.metric(label.replace("_", " ").title(), fmt(val))

insights = dash.get("executive_insights")
if insights:
    with st.expander("💡 Key findings", expanded=True):
        st.markdown(f"**{insights.get('headline', '')}**")
        for finding in insights.get("key_findings", []):
            st.markdown(f"- {finding}")
        if insights.get("actionable_insights"):
            st.markdown("**Actionable Next Steps:**")
            for action in insights.get("actionable_insights", []):
                st.markdown(f"- {action}")
else:
    with st.expander("💡 Key findings", expanded=True):
        pass

query = st.text_input("Search", placeholder="Search questions or findings…", label_visibility="collapsed").lower()
groups: dict[str, list] = {}
for k, q in ok.items():
    text = f"{q.get('question', '')} {(q.get('facts') or {}).get('answer', '')}".lower()
    if query in text:
        groups.setdefault(get_group(q), []).append((k, q))

names = [n for n in TAB_ORDER if n in groups] + [n for n in groups if n not in TAB_ORDER]
if not names:
    st.info("No analyses match your search.")
else:
    for tab, name in zip(st.tabs([f"{n} ({len(groups[n])})" for n in names]), names):
        with tab:
            cols = st.columns(2)
            for i, (k, q) in enumerate(groups[name]):
                with cols[i % 2]:
                    card(k, q)

if bad:
    with st.expander(f"Skipped analyses ({len(bad)})"):
        for q in bad.values():
            st.write(f"- {q.get('question')}: {q.get('error')}")

st.divider()
st.download_button(
    "📥 Export dashboard JSON",
    json.dumps(dash, indent=2),
    file_name=f"{dash.get('dataset', 'analysis')}_dashboard.json",
    mime="application/json",
)
