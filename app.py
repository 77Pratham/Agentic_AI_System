"""
app.py — Agentic AI System with Human Feedback Loop
Run: streamlit run app.py

Human Feedback flow:
  1. User asks question → agent answers
  2. User clicks 👍 (done) or 👎 (bad answer)
  3. On 👎 → text box appears: "What was wrong?"
  4. User types correction → agent reruns with that context injected
  5. Repeat until 👍 or user gives up
"""

import re
import streamlit as st
from agent import run_agent
from report_pdf import generate_pdf

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Agentic AI System", page_icon="🤖", layout="wide")

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background:#0f1117; color:#e6edf3; }
h1 { font-family:'Courier New',monospace; font-size:2rem; color:#58a6ff;
     border-bottom:1px solid #21262d; padding-bottom:.5rem; }
.subtitle { color:#8b949e; font-size:.9rem; margin-bottom:1.5rem; }
.section-header { font-size:.75rem; font-weight:700; text-transform:uppercase;
                  letter-spacing:.1em; color:#8b949e; margin-bottom:.4rem; }
.answer-box { background:#161b22; border:1px solid #30363d;
              border-left:3px solid #58a6ff; border-radius:6px;
              padding:1rem 1.25rem; font-size:1rem; line-height:1.6; }
.answer-box-revised { background:#161b22; border:1px solid #30363d;
                      border-left:3px solid #3fb950; border-radius:6px;
                      padding:1rem 1.25rem; font-size:1rem; line-height:1.6; }
.output-box { background:#0d1117; border:1px solid #30363d;
              border-left:3px solid #f0883e; border-radius:6px;
              padding:.75rem 1.25rem; font-family:'Courier New',monospace;
              font-size:.85rem; color:#e3b341; }
.error-box  { background:#1f0d0d; border:1px solid #f85149; border-radius:6px;
              padding:.75rem 1.25rem; font-family:'Courier New',monospace;
              font-size:.85rem; color:#f85149; }
.feedback-box { background:#161b22; border:1px solid #f0883e44;
                border-radius:8px; padding:1rem 1.25rem; margin-top:1rem; }
.feedback-approved { background:#0d1f0d; border:1px solid #3fb950;
                     border-radius:8px; padding:.75rem 1.25rem; margin-top:1rem;
                     color:#3fb950; font-weight:600; }
.feedback-rejected { background:#1f1200; border:1px solid #f0883e;
                     border-radius:8px; padding:.75rem 1.25rem; margin-top:1rem;
                     color:#f0883e; font-weight:600; }
.history-item { background:#0d1117; border:1px solid #21262d; border-radius:6px;
                padding:.75rem 1rem; margin-bottom:.5rem; }
.history-correction { font-size:.8rem; color:#f0883e; margin-top:.3rem; }
.query-chip { display:inline-block; background:#161b22; border:1px solid #30363d;
              border-radius:20px; padding:3px 12px; font-size:.78rem;
              color:#8b949e; margin:3px; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px;
         font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.badge-search { background:#1d4ed8; color:#bfdbfe; }
.badge-code   { background:#14532d; color:#bbf7d0; }
.badge-deep   { background:#4c1d95; color:#e9d5ff; }
hr { border-color:#21262d; }
.stButton > button { background:#238636; color:white; border:none; border-radius:6px;
                     font-weight:600; padding:.5rem 1.5rem; font-size:.95rem; }
.stButton > button:hover { background:#2ea043; }
.deep-toggle { background:#161b22; border:1px solid #bc8cff33; border-radius:8px;
               padding:.75rem 1rem; margin-bottom:1rem; }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ───────────────────────────────────────────────────────
# Everything lives in session_state so it survives Streamlit reruns

defaults = {
    "result":            None,    # current agent result dict
    "question":          "",      # current question
    "deep_research":     False,
    "feedback_given":    None,    # None | "approved" | "rejected"
    "feedback_history":  [],      # list of {question, answer, correction, rerun_answer}
    "awaiting_correction": False, # True when 👎 was clicked, waiting for text
    "correction_text":   "",      # what the user typed as correction
    "turn":              0,       # increments each rerun so widgets get fresh keys
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Helpers ─────────────────────────────────────────────────────────────────

def do_run(question: str, deep_research: bool, human_correction: str = ""):
    """Call run_agent and store result in session_state."""
    with st.spinner("🤖 Agent is thinking…"):
        result = run_agent(
            question.strip(),
            deep_research=deep_research,
            human_correction=human_correction,
        )
    st.session_state.result            = result
    st.session_state.feedback_given    = None
    st.session_state.awaiting_correction = False
    st.session_state.correction_text   = ""
    st.session_state.turn             += 1


def render_badge(action: str) -> str:
    if action == "deep_research":
        return '<span class="badge badge-deep">🔬 Deep Research</span>'
    elif action == "code":
        return '<span class="badge badge-code">⚙️ Code Execution</span>'
    return '<span class="badge badge-search">🔍 Web Search</span>'


def render_result(result: dict, box_class: str = "answer-box"):
    """Render the agent result (answer, code, output, sources)."""
    action = result.get("action", "")

    # Badge
    st.markdown(f"**Mode:** {render_badge(action)}", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if action == "deep_research":
        # Sub-questions
        queries = result.get("research_queries", [])
        if queries:
            st.markdown('<p class="section-header">🧠 Sub-questions researched</p>',
                        unsafe_allow_html=True)
            chips = " ".join(f'<span class="query-chip">{q}</span>' for q in queries)
            st.markdown(chips, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # Scraping stats
        rr = result.get("research_results", [])
        if rr:
            total = sum(len(r.get("scraped_pages", [])) for r in rr)
            with st.expander(f"🌐 Web pages scraped ({total} total)"):
                for item in rr:
                    st.markdown(f"**{item['query']}**")
                    for p in item.get("scraped_pages", []):
                        st.markdown(f"&nbsp;&nbsp;✓ [{p['url'][:70]}]({p['url']}) — {len(p['text'])} chars")
            st.markdown("<br>", unsafe_allow_html=True)

        # Report
        if result.get("research_report"):
            st.markdown('<p class="section-header">📄 Research Report</p>',
                        unsafe_allow_html=True)
            st.markdown(result["research_report"])

        # PDF Download
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<p class="section-header">⬇️ Download Report</p>',
                    unsafe_allow_html=True)

        col_dl, col_info = st.columns([2, 5])
        with col_dl:
            try:
                pdf_bytes = generate_pdf(
                    question         = st.session_state.get("question", "Research Report"),
                    report_markdown  = result.get("research_report", ""),
                    research_queries = result.get("research_queries", []),
                    sources          = result.get("sources", []),
                    research_results = result.get("research_results", []),
                )
                safe_name = re.sub(r"[^\w\s-]", "",
                                   st.session_state.get("question", "report")[:50])
                safe_name = re.sub(r"\s+", "_", safe_name.strip()).lower()
                filename  = f"research_{safe_name}.pdf"
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
        with col_info:
            st.markdown(
                '<p style="color:#8b949e; font-size:.85rem; padding-top:.5rem;">'
                'Includes cover page · all sections · sub-questions · sources list'
                '</p>',
                unsafe_allow_html=True,
            )

    else:
        # Answer
        st.markdown('<p class="section-header">📝 Answer</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="{box_class}">{result["answer"]}</div>',
                    unsafe_allow_html=True)

        # Code
        if result.get("code"):
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p class="section-header">🐍 Generated Python Code</p>',
                        unsafe_allow_html=True)
            st.code(result["code"], language="python")

        # Execution output
        if result.get("execution_output"):
            st.markdown('<p class="section-header">📤 Execution Output</p>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="output-box">{result["execution_output"]}</div>',
                        unsafe_allow_html=True)

        # Execution error
        if result.get("execution_error"):
            st.markdown('<p class="section-header">⚠️ Execution Error</p>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="error-box">{result["execution_error"]}</div>',
                        unsafe_allow_html=True)

        # Self-correction log
        rc = result.get("retry_count", 0)
        if rc > 0:
            status = "✅ Succeeded" if result.get("execution_output") else "❌ All retries failed"
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f'<p class="section-header">🔄 Self-Correction Log &nbsp;'
                f'<span style="color:#8b949e;font-weight:400;text-transform:none;">'
                f'{rc} retry attempt(s) — {status}</span></p>',
                unsafe_allow_html=True,
            )
            for attempt in result.get("retry_history", []):
                with st.expander(f"Attempt {attempt['attempt']} — Error"):
                    st.code(attempt["code"], language="python")
                    st.markdown(f'<div class="error-box">{attempt["error"]}</div>',
                                unsafe_allow_html=True)

    # Sources
    if result.get("sources"):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<p class="section-header">🔗 Sources</p>', unsafe_allow_html=True)
        for i, url in enumerate(result["sources"], 1):
            st.markdown(f"{i}. [{url}]({url})")


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("<h1>🤖 Agentic AI System</h1>", unsafe_allow_html=True)
st.markdown('<p class="subtitle">Gemini · LangGraph · Tavily · Web Scraping · Human Feedback</p>',
            unsafe_allow_html=True)

# ─── Input ───────────────────────────────────────────────────────────────────
col_q, col_toggle = st.columns([5, 2])
with col_q:
    question = st.text_input(
        "question",
        placeholder="e.g. What are the latest breakthroughs in quantum computing?",
        label_visibility="collapsed",
        key="question_input",
    )
with col_toggle:
    deep_research = st.toggle("🔬 Deep Research Mode", value=False,
                              help="Generates sub-questions, multi-searches, scrapes pages, writes report. ~30-60s.")

if deep_research:
    st.markdown(
        '<div class="deep-toggle">🔬 <b>Deep Research ON</b> — '
        'sub-questions → multi-search → scrape → report. '
        '<span style="color:#8b949e">~30-60s</span></div>',
        unsafe_allow_html=True,
    )

run_btn = st.button("▶  Run Agent")

with st.expander("💡 Example queries"):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**🔍 Quick Search**")
        st.caption("Who won the 2024 Nobel Prize in Physics?")
    with c2:
        st.markdown("**⚙️ Code**")
        st.caption("Calculate compound interest ₹10000 at 8% for 5 years")
    with c3:
        st.markdown("**🔬 Deep Research**")
        st.caption("Impact of AI on the job market in 2024")

st.markdown("---")

# ─── Initial Run ─────────────────────────────────────────────────────────────
if run_btn:
    if not question.strip():
        st.warning("Please enter a question first.")
        st.stop()
    # Reset feedback history on a fresh question
    st.session_state.feedback_history  = []
    st.session_state.deep_research     = deep_research
    st.session_state.question          = question
    do_run(question, deep_research)

# ─── Show Result + Feedback UI ───────────────────────────────────────────────
if st.session_state.result is not None:
    result   = st.session_state.result
    turn     = st.session_state.turn
    history  = st.session_state.feedback_history

    # ── Past feedback rounds (collapsed) ─────────────────────────────────────
    if history:
        with st.expander(f"📜 Feedback History ({len(history)} round(s))", expanded=False):
            for i, h in enumerate(history, 1):
                st.markdown(
                    f'<div class="history-item">'
                    f'<b>Round {i} answer:</b> {h["answer"][:300]}{"..." if len(h["answer"])>300 else ""}'
                    f'<div class="history-correction">👎 Your correction: <i>"{h["correction"]}"</i></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Current answer ────────────────────────────────────────────────────────
    is_revised = len(history) > 0
    box_class  = "answer-box-revised" if is_revised else "answer-box"

    if is_revised:
        st.markdown(
            f'<div class="feedback-rejected">'
            f'🔁 Revised answer (after {len(history)} correction(s))</div>',
            unsafe_allow_html=True,
        )

    render_result(result, box_class=box_class)

    # ── Feedback section ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<p class="section-header">💬 Was this answer helpful?</p>',
                unsafe_allow_html=True)

    feedback_given = st.session_state.feedback_given

    if feedback_given == "approved":
        st.markdown(
            '<div class="feedback-approved">👍 Great! Glad it helped.</div>',
            unsafe_allow_html=True,
        )

    elif feedback_given == "rejected" and not st.session_state.awaiting_correction:
        # Show correction box
        st.markdown(
            '<div class="feedback-box">'
            '👎 <b>Tell the agent what was wrong</b> — it will rerun with your correction.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        correction = st.text_area(
            "What was wrong with the answer?",
            placeholder=(
                "e.g. 'You got the year wrong, it was 2023 not 2022' · "
                "'Include more details about the economic impact' · "
                "'The code output is wrong, it should calculate net not gross'"
            ),
            height=100,
            key=f"correction_input_{turn}",
        )

        col_submit, col_cancel = st.columns([2, 5])
        with col_submit:
            if st.button("🔁 Rerun with correction", key=f"rerun_{turn}"):
                if not correction.strip():
                    st.warning("Please describe what was wrong first.")
                else:
                    # Save this round to history
                    st.session_state.feedback_history.append({
                        "answer":     result.get("answer", ""),
                        "correction": correction.strip(),
                    })
                    st.session_state.awaiting_correction = True
                    # Rerun agent with the correction injected
                    do_run(
                        st.session_state.question,
                        st.session_state.deep_research,
                        human_correction=correction.strip(),
                    )
                    st.rerun()
        with col_cancel:
            if st.button("✕ Cancel", key=f"cancel_{turn}"):
                st.session_state.feedback_given = None
                st.rerun()

    else:
        # Neither approved nor rejected yet — show the buttons
        col_yes, col_no, col_spacer = st.columns([1, 1, 6])
        with col_yes:
            if st.button("👍  Looks good", key=f"approve_{turn}"):
                st.session_state.feedback_given = "approved"
                st.rerun()
        with col_no:
            if st.button("👎  Not right", key=f"reject_{turn}"):
                st.session_state.feedback_given = "rejected"
                st.rerun()

    # ── Debug JSON ────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔧 Full JSON Response (Debug)"):
        st.json({
            "answer":           result.get("answer","")[:400],
            "action":           result.get("action",""),
            "code":             result.get("code",""),
            "execution_output": result.get("execution_output",""),
            "execution_error":  result.get("execution_error",""),
            "retry_count":      result.get("retry_count",0),
            "sources":          result.get("sources",[]),
            "research_queries": result.get("research_queries",[]),
            "feedback_rounds":  len(st.session_state.feedback_history),
        })

# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="color:#8b949e;font-size:.78rem;text-align:center;">'
    'Agentic AI Bootcamp · LangGraph + Gemini + Tavily + BeautifulSoup + Human Feedback</p>',
    unsafe_allow_html=True,
)