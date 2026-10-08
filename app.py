"""
CareCompanion front end, laid out like an answer engine:
centered question, sources above the answer, inline citations, related follow-ups,
and a follow-up box pinned to the bottom. Tuned for older readers: larger default
text, an always-visible text size switch, high-contrast ink, and read-aloud.
Run:  streamlit run app.py
"""

import html
import json
import re

import streamlit as st
import streamlit.components.v1 as components

from rag import answer

st.set_page_config(
    page_title="CareCompanion",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

TEXT_SIZES = {"Regular": 17, "Large": 19, "Largest": 22}

STARTERS = [
    "Mom gets confused every evening. What helps?",
    "How do I make the bathroom safer?",
    "How do I get Dad to eat more?",
    "How do I avoid caregiver burnout?",
]
MORE_QUESTIONS = STARTERS + [
    "What should I do if Mom wanders at night?",
    "How can I keep track of Dad's medications?",
    "What are early signs of dementia?",
    "How do I talk to Dad about giving up driving?",
]

# ---------- state ----------
st.session_state.setdefault("history", [])
st.session_state.setdefault("pending", None)
st.session_state.setdefault("text_size", "Large")

base = TEXT_SIZES[st.session_state.text_size]
history = st.session_state.history
is_home = not history

ICON_SOURCES = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5V5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2"/><path d="M8 7h6"/></svg>'
ICON_ANSWER = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21c-4.5-3-8-6.2-8-10.2A4.8 4.8 0 0 1 12 7.6a4.8 4.8 0 0 1 8 3.2C20 14.8 16.5 18 12 21z"/></svg>'
ICON_RELATED = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6h16M4 12h10M4 18h7"/></svg>'

# ---------- styles ----------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400..650&display=swap');

:root {{
  --page: #FCFCF9;
  --surface: #FFFFFF;
  --surface-2: #F3F3EE;
  --ink: #1A2A2E;
  --ink-soft: #55625F;
  --line: rgba(39, 26, 0, 0.14);
  --teal: #1A6C77;
  --teal-bright: #20808D;
  --teal-wash: #E6F2F3;
  --alarm: #B3261E;
  --alarm-wash: #FCEDEB;
  --base: {base}px;
}}

html, body, .stApp, .stApp * {{ font-family: 'Inter', ui-sans-serif, system-ui, sans-serif !important; }}
.stApp {{ background: var(--page); color: var(--ink); }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{ max-width: 780px; padding-top: 1.4rem; padding-bottom: 8rem; }}
.stApp p, .stApp li {{ font-size: var(--base); line-height: 1.65; color: var(--ink); }}

/* ---------- top bar ---------- */
.stApp .cc-brand {{ display: flex; align-items: center; gap: 0.5rem; font-size: 1.15rem; font-weight: 550;
  letter-spacing: -0.015em; color: var(--ink); margin: 0; }}
.stApp .cc-brand svg {{ color: var(--teal-bright); }}
.stApp .cc-911 {{ display: inline-flex; align-items: center; gap: 0.35rem; height: 36px; padding: 0 0.85rem;
  border: 1px solid var(--line); border-radius: 9999px; color: var(--alarm); font-size: 0.95rem;
  font-weight: 550; text-decoration: none; white-space: nowrap; background: var(--surface); }}
.stApp .cc-911:hover, .stApp .cc-911:focus-visible {{ border-color: var(--alarm); background: var(--alarm-wash); }}
[data-testid="stButtonGroup"] button {{ min-height: 36px; font-size: 0.95rem; border-color: var(--line); }}
[data-testid="stButtonGroup"] button[kind*="Active"], [data-testid="stButtonGroup"] button[aria-checked="true"] {{
  background: var(--surface-2); color: var(--ink); }}

/* ---------- home ---------- */
.stApp .cc-hero {{ text-align: center; font-size: calc(var(--base) * 1.85); font-weight: 450; letter-spacing: -0.025em;
  line-height: 1.2; color: var(--ink); margin: 20vh auto 1.6rem; max-width: 22ch; }}
.stApp .cc-home-note {{ text-align: center; font-size: calc(var(--base) * 0.82) !important; color: var(--ink-soft) !important; margin: 1.4rem auto 0; max-width: 52ch; }}
.stApp .cc-home-note a {{ color: var(--alarm); font-weight: 550; }}

/* ---------- the ask box ---------- */
[data-testid="stBottom"] > div {{ background: linear-gradient(to bottom, rgba(252,252,249,0), var(--page) 30%); }}
[data-testid="stChatInput"] {{ background: var(--surface) !important; border: 1px solid var(--line) !important;
  border-radius: 16px !important; box-shadow: 0 1px 2px rgba(39,26,0,0.04); padding: 0.35rem 0.4rem 0.35rem 0.6rem; }}
[data-testid="stChatInput"]:focus-within {{ border-color: var(--teal-bright) !important; box-shadow: 0 0 0 3px var(--teal-wash); }}
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea {{ background: var(--surface) !important; }}
[data-testid="stChatInput"] textarea {{ font-size: var(--base) !important; color: var(--ink) !important; min-height: 52px; }}
[data-testid="stChatInput"] textarea::placeholder {{ color: #7A8582 !important; }}
[data-testid="stChatInput"] button {{ width: 36px !important; height: 36px !important; border-radius: 9999px !important;
  background: var(--teal-bright) !important; }}
[data-testid="stChatInput"] button svg {{ color: #fff !important; fill: #fff !important; }}
[data-testid="stChatInput"] button:disabled {{ background: var(--surface-2) !important; }}
[data-testid="stChatInput"] button:disabled svg {{ color: #9AA3A0 !important; fill: #9AA3A0 !important; }}

div.st-key-topright {{ flex-wrap: nowrap; }}
div.st-key-topright > div {{ width: auto !important; flex: 0 0 auto; }}

/* suggestion chips */
div.st-key-chips {{ justify-content: center; gap: 0.5rem; margin-top: 0.9rem; }}
div[class*="st-key-chip-"] button {{ min-height: 40px; border-radius: 9999px; border: 1px solid var(--line);
  background: var(--surface); color: var(--ink); padding: 0.35rem 1rem; }}
div[class*="st-key-chip-"] {{ max-width: 100%; }}
div[class*="st-key-chip-"] button {{ max-width: 100%; height: auto; }}
div[class*="st-key-chip-"] button * {{ white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }}
div[class*="st-key-chip-"] button p {{ font-size: calc(var(--base) * 0.82) !important; margin: 0; }}
div[class*="st-key-chip-"] button:hover {{ background: var(--surface-2); border-color: var(--line); color: var(--ink); }}

/* ---------- a turn: question, sources, answer ---------- */
.stApp .cc-q {{ font-size: calc(var(--base) * 1.55); font-weight: 500; letter-spacing: -0.02em; line-height: 1.25;
  color: var(--ink); margin: 1.6rem 0 1.4rem; }}
.stApp .cc-label {{ display: flex; align-items: center; gap: 0.5rem; font-size: calc(var(--base) * 0.95) !important;
  font-weight: 550; color: var(--ink) !important; margin: 0 0 0.7rem; }}
.stApp .cc-label svg {{ color: var(--teal-bright); }}

.stApp .cc-sources {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.5rem; margin: 0 0 1.8rem; }}
.stApp .cc-src {{ background: var(--surface-2); border-radius: 10px; padding: 0.65rem 0.75rem; display: flex;
  flex-direction: column; justify-content: space-between; gap: 0.5rem; min-height: 84px; }}
.stApp .cc-src-title {{ font-size: calc(var(--base) * 0.76) !important; line-height: 1.35; color: var(--ink) !important; margin: 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
.stApp .cc-src-meta {{ display: flex; align-items: center; gap: 0.4rem; font-size: calc(var(--base) * 0.7) !important;
  color: var(--ink-soft) !important; margin: 0; }}
.stApp .cc-num {{ display: inline-flex; align-items: center; justify-content: center; min-width: 1.35em; height: 1.35em;
  border-radius: 9999px; background: var(--surface); color: var(--ink-soft); font-size: 0.9em; font-weight: 550; }}

div[class*="st-key-answer-"] [data-testid="stMarkdownContainer"] p,
div[class*="st-key-answer-"] [data-testid="stMarkdownContainer"] li {{ max-width: 66ch; }}
div[class*="st-key-answer-"] strong {{ font-weight: 600; }}
.stApp .cc-cite {{ display: inline-flex; align-items: center; justify-content: center; min-width: 1.3em; height: 1.3em;
  padding: 0 0.3em; margin: 0 0.1em; border-radius: 9999px; background: var(--surface-2); color: var(--ink-soft);
  font-size: 0.68em; font-weight: 600; vertical-align: 0.15em; line-height: 1; }}

.stApp .cc-turn-end {{ border: 0; border-top: 1px solid var(--line); margin: 1.6rem 0 0.2rem; }}

/* special replies */
div[class*="st-key-alarm-"] {{ background: var(--alarm-wash); border: 1px solid var(--alarm); border-radius: 16px; padding: 1.1rem 1.3rem; }}
div[class*="st-key-alarm-"] p {{ color: #6E1712; font-weight: 550; }}
.stApp .cc-call {{ display: inline-block; background: var(--alarm); color: #fff !important; font-weight: 600;
  text-decoration: none; border-radius: 9999px; padding: 0.55rem 1.3rem; font-size: var(--base); }}
div[class*="st-key-unsure-"] {{ background: var(--surface-2); border-radius: 16px; padding: 1rem 1.3rem; }}

/* related follow-ups: plain rows divided by hairlines */
div[class*="st-key-rel-"] button {{ width: 100%; min-height: 54px; justify-content: space-between; background: transparent;
  border: 0; border-bottom: 1px solid var(--line); border-radius: 0; padding: 0.6rem 0.2rem; color: var(--ink); }}
div[class*="st-key-rel-"] button > div {{ justify-content: flex-start !important; text-align: left; }}
div[class*="st-key-rel-"] button p {{ font-size: calc(var(--base) * 0.95) !important; text-align: left; margin: 0; }}
div[class*="st-key-rel-"] button::after {{ content: "+"; font-size: 1.4rem; font-weight: 400; color: var(--teal-bright); margin-left: 1rem; }}
div[class*="st-key-rel-"] button:hover {{ color: var(--teal); background: transparent; }}
div[class*="st-key-rel-"], div[class*="st-key-rel-"] .stButton, div[class*="st-key-rel-"] .stButton > div {{ width: 100% !important; }}

div.st-key-reset button {{ border-radius: 9999px; border: 1px solid var(--line); background: var(--surface); min-height: 40px; }}
div.st-key-reset button p {{ font-size: calc(var(--base) * 0.82) !important; }}

.stApp .cc-foot {{ font-size: calc(var(--base) * 0.74) !important; color: var(--ink-soft) !important; margin-top: 2.2rem; max-width: 62ch; }}

button:focus-visible, a:focus-visible {{ outline: 2px solid var(--teal-bright) !important; outline-offset: 2px; }}

@media (max-width: 640px) {{
  div.st-key-topright {{ justify-content: flex-start; flex-wrap: wrap; }}
  .stApp .cc-hero {{ margin-top: 10vh; font-size: calc(var(--base) * 1.5); }}
  .stApp .cc-q {{ font-size: calc(var(--base) * 1.3); }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- helpers ----------
def pretty_source(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").strip().capitalize()


def with_citations(text: str) -> str:
    """Escape model output, then turn [1] or [1, 2] into small inline citation pills."""
    safe = html.escape(text, quote=False)

    def pills(m):
        nums = [n.strip() for n in m.group(1).split(",")]
        return "".join(f'<span class="cc-cite">{n}</span>' for n in nums)

    return re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", pills, safe)


def sources_html(sources) -> str:
    cards = "".join(
        f'<div class="cc-src" title="{html.escape(s.get("text", "")[:300])}">'
        f'<p class="cc-src-title">{html.escape(pretty_source(s["source"]))}</p>'
        f'<p class="cc-src-meta"><span class="cc-num">{i}</span>Page {s["page"]}</p></div>'
        for i, s in enumerate(sources, start=1)
    )
    return (
        f'<p class="cc-label">{ICON_SOURCES}Sources</p>'
        f'<div class="cc-sources">{cards}</div>'
        f'<p class="cc-label">{ICON_ANSWER}Answer</p>'
    )


def read_aloud(text: str):
    """Quiet action row under the answer. Browser speech, slowed slightly, citations stripped."""
    spoken = json.dumps(re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", "", text))
    # keep model text from closing the <script> tag
    spoken = spoken.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    embed_html(
        f"""
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@500&display=swap" rel="stylesheet">
        <style>
          body {{ margin: 0; }}
          button {{ display: inline-flex; align-items: center; gap: 8px; height: 38px; padding: 0 14px 0 10px;
            border: 1px solid rgba(39,26,0,0.14); border-radius: 9999px; background: #fff; color: #55625F;
            font: 500 15px 'Inter', system-ui, sans-serif; cursor: pointer; }}
          button:hover {{ background: #F3F3EE; color: #1A2A2E; }}
          button:focus-visible {{ outline: 2px solid #20808D; outline-offset: 2px; }}
        </style>
        <button id="b" aria-label="Read this answer aloud">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
            stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>
          <span id="t">Read aloud</span>
        </button>
        <script>
          const b = document.getElementById('b'), t = document.getElementById('t');
          b.onclick = () => {{
            if (speechSynthesis.speaking) {{ speechSynthesis.cancel(); t.textContent = 'Read aloud'; return; }}
            const u = new SpeechSynthesisUtterance({spoken}); u.rate = 0.9;
            u.onend = () => t.textContent = 'Read aloud';
            t.textContent = 'Stop reading'; speechSynthesis.speak(u);
          }};
        </script>
        """,
        height=44,
    )


def embed_html(markup: str, height: int):
    """st.iframe on newer Streamlit, components.html on older versions."""
    if hasattr(st, "iframe"):
        st.iframe(markup, height=height)
    else:
        components.html(markup, height=height)


def render_reply(idx: int, msg: dict):
    status = msg.get("status")
    if status == "emergency":
        with st.container(key=f"alarm-{idx}"):
            st.markdown(msg["content"])
            st.markdown('<a class="cc-call" href="tel:911">Call 911</a>', unsafe_allow_html=True)
    elif status == "not_grounded":
        with st.container(key=f"unsure-{idx}"):
            st.markdown(msg["content"])
    else:
        if msg.get("sources"):
            st.markdown(sources_html(msg["sources"]), unsafe_allow_html=True)
        with st.container(key=f"answer-{idx}"):
            st.markdown(with_citations(msg["content"]), unsafe_allow_html=True)
            read_aloud(msg["content"])


def ask(q: str):
    st.session_state.pending = q
    st.rerun()


# ---------- top bar ----------
left, right = st.columns([1, 2], vertical_alignment="center")
with left:
    st.markdown(
        '<p class="cc-brand"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 21c-4.5-3-8-6.2-8-10.2A4.8 4.8 0 0 1 12 7.6a4.8 4.8 0 0 1 8 3.2C20 14.8 16.5 18 12 21z"/></svg>'
        "CareCompanion</p>",
        unsafe_allow_html=True,
    )
with right:
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small", key="topright"):
        choice = st.segmented_control(
            "Text size", list(TEXT_SIZES), default=st.session_state.text_size,
            key="text_size_ctl", label_visibility="collapsed",
        )
        st.markdown('<a class="cc-911" href="tel:911">Emergency: 911</a>', unsafe_allow_html=True)
    if choice and choice != st.session_state.text_size:
        st.session_state.text_size = choice
        st.rerun()

# ---------- home: one centered question ----------
typed = None
if is_home:
    st.markdown('<p class="cc-hero">What would help with caregiving today?</p>', unsafe_allow_html=True)
    with st.container(key="home-ask"):
        typed = st.chat_input("Ask about caring for a parent or loved one…", key="ask_home")
    with st.container(horizontal=True, key="chips"):
        for i, q in enumerate(STARTERS):
            if st.button(q, key=f"chip-{i}"):
                ask(q)
    st.markdown(
        '<p class="cc-home-note">Answers come only from trusted caregiving guides and show the page they came from. '
        'If someone is hurt or can\'t breathe, <a href="tel:911">call 911</a> first.</p>',
        unsafe_allow_html=True,
    )

# ---------- conversation ----------
for idx, msg in enumerate(history):
    if msg["role"] == "user":
        if idx > 0:
            st.markdown('<hr class="cc-turn-end">', unsafe_allow_html=True)
        st.markdown(f'<p class="cc-q">{html.escape(msg["content"])}</p>', unsafe_allow_html=True)
    else:
        render_reply(idx, msg)

if history:
    asked = {m["content"] for m in history if m["role"] == "user"}
    related = [q for q in MORE_QUESTIONS if q not in asked][:3]
    if related:
        st.markdown(f'<p class="cc-label" style="margin-top:2rem">{ICON_RELATED}Related</p>', unsafe_allow_html=True)
        for i, q in enumerate(related):
            if st.button(q, key=f"rel-{i}"):
                ask(q)
    st.write("")
    if st.button("Start a new topic", key="reset"):
        st.session_state.history = []
        st.rerun()
    st.markdown(
        '<p class="cc-foot">CareCompanion shares general information from public caregiving guides. '
        "It can't diagnose anything or replace advice from a doctor, nurse, or pharmacist.</p>",
        unsafe_allow_html=True,
    )
    typed = st.chat_input("Ask a follow-up…", key="ask_follow")

question = typed or st.session_state.pending
st.session_state.pending = None

if question:
    if history:
        st.markdown('<hr class="cc-turn-end">', unsafe_allow_html=True)
    st.markdown(f'<p class="cc-q">{html.escape(question)}</p>', unsafe_allow_html=True)
    with st.spinner("Reading the caregiving guides…"):
        prior = [{"role": m["role"], "content": m["content"]} for m in history]
        result = answer(question, history=prior)
    history.append({"role": "user", "content": question})
    history.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"] if result["status"] == "ok" else [],
        "status": result["status"],
    })
    st.rerun()
