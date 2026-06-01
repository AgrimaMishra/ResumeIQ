# =============================================================================
# AI Resume Assistant — Interactive Dashboard
# =============================================================================

import os
import re
import json
import math
import pdfplumber
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openai/gpt-3.5-turbo"

st.set_page_config(
    page_title="ResumeIQ — Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');
*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main{
  background:#080c14!important;color:#c8d6e8!important;font-family:'Syne',sans-serif!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stDecoration"]{display:none}
[data-testid="stSidebar"]{background:#0d1525!important;border-right:1px solid #1e3a5f!important}
[data-testid="stSidebar"] *{color:#8bafd4!important}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#f0a500!important}
[data-testid="stFileUploader"]{background:#0d1525!important;border:2px dashed #1e3a5f!important;border-radius:12px!important;padding:1rem!important}
[data-testid="stFileUploader"]:hover{border-color:#f0a500!important}
.stButton>button{background:linear-gradient(135deg,#f0a500,#e06c00)!important;color:#080c14!important;
  font-family:'Space Mono',monospace!important;font-weight:700!important;font-size:.85rem!important;
  border:none!important;border-radius:6px!important;padding:.6rem 1.4rem!important;
  letter-spacing:.05em!important;transition:transform .15s,box-shadow .15s!important}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(240,165,0,.4)!important}
[data-testid="stTabs"] button{font-family:'Space Mono',monospace!important;font-size:.78rem!important;color:#4a6fa5!important;border-bottom:2px solid transparent!important}
[data-testid="stTabs"] button[aria-selected="true"]{color:#f0a500!important;border-bottom:2px solid #f0a500!important}
textarea{background:#0d1525!important;color:#7a99bb!important;border:1px solid #1e3a5f!important;border-radius:8px!important;font-family:'Space Mono',monospace!important;font-size:.78rem!important}
[data-testid="stExpander"]{background:#0d1525!important;border:1px solid #1e3a5f!important;border-radius:8px!important}
hr{border-color:#1e3a5f!important}
[data-testid="stMetric"]{background:#0d1525;border:1px solid #1e3a5f;border-radius:10px;padding:1rem}
[data-testid="stMetricValue"]{font-family:'Space Mono',monospace!important;color:#f0a500!important;font-size:2rem!important}
[data-testid="stMetricLabel"]{color:#4a6fa5!important}
[data-testid="stSpinner"] p{color:#f0a500!important}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:#080c14}::-webkit-scrollbar-thumb{background:#1e3a5f;border-radius:3px}
</style>
""", unsafe_allow_html=True)


# ── SVG GAUGE ──────────────────────────────────────────────────────────────
def render_gauge(score: int) -> str:
    r = 80; cx = cy = 110
    start_deg, end_deg = 200, 340
    total_deg = end_deg - start_deg

    def polar(cx, cy, r, deg):
        rad = math.radians(deg)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    sx, sy   = polar(cx, cy, r, start_deg)
    ex, ey   = polar(cx, cy, r, end_deg)
    sdeg     = start_deg + (score / 100) * total_deg
    sex, sey = polar(cx, cy, r, sdeg)
    large    = 1 if (sdeg - start_deg) > 180 else 0
    color    = "#22c55e" if score >= 75 else "#f0a500" if score >= 55 else "#ef4444"
    label    = "STRONG"   if score >= 75 else "AVERAGE"  if score >= 55 else "WEAK"

    return f"""<div style="display:flex;justify-content:center;margin:.5rem 0 1rem">
<svg width="220" height="160" viewBox="0 0 220 160" xmlns="http://www.w3.org/2000/svg">
  <defs><filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/>
  <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
  <path d="M {sx:.1f},{sy:.1f} A {r},{r} 0 1,1 {ex:.1f},{ey:.1f}"
        fill="none" stroke="#1e3a5f" stroke-width="14" stroke-linecap="round"/>
  <path d="M {sx:.1f},{sy:.1f} A {r},{r} 0 {large},1 {sex:.1f},{sey:.1f}"
        fill="none" stroke="{color}" stroke-width="14" stroke-linecap="round" filter="url(#glow)"/>
  <text x="{cx}" y="{cy+8}" text-anchor="middle"
        font-family="Space Mono,monospace" font-size="32" font-weight="700" fill="{color}">{score}</text>
  <text x="{cx}" y="{cy+30}" text-anchor="middle"
        font-family="Syne,sans-serif" font-size="11" fill="#4a6fa5" letter-spacing="2">ATS SCORE</text>
  <text x="{cx}" y="{cy+48}" text-anchor="middle"
        font-family="Space Mono,monospace" font-size="10" font-weight="700"
        fill="{color}" letter-spacing="3">{label}</text>
</svg></div>"""


# ── SKILL BAR ──────────────────────────────────────────────────────────────
def skill_bar(label: str, pct: int, color: str = "#f0a500") -> str:
    return (f'<div style="margin:.45rem 0">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-family:Space Mono,monospace;font-size:.72rem;color:#8bafd4;margin-bottom:4px">'
            f'<span>{label}</span><span style="color:{color}">{pct}%</span></div>'
            f'<div style="background:#1e3a5f;border-radius:4px;height:7px;overflow:hidden">'
            f'<div style="height:100%;width:{pct}%;background:{color};border-radius:4px;'
            f'box-shadow:0 0 8px {color}66"></div></div></div>')


# ── KEYWORD CHIP ───────────────────────────────────────────────────────────
def keyword_chip(word: str, found: bool) -> str:
    bg = "#0f2a1a" if found else "#1a0f0f"
    clr = "#22c55e" if found else "#ef4444"
    icon = "✓" if found else "✗"
    return (f'<span style="display:inline-block;margin:3px;padding:3px 10px;'
            f'background:{bg};color:{clr};border:1px solid {clr}44;border-radius:20px;'
            f'font-family:Space Mono,monospace;font-size:.7rem">{icon} {word}</span>')


# ── CARD ───────────────────────────────────────────────────────────────────
def card(title: str, content: str, accent: str = "#f0a500") -> str:
    return (f'<div style="background:#0d1525;border:1px solid #1e3a5f;'
            f'border-left:3px solid {accent};border-radius:8px;padding:1.1rem 1.3rem;margin:.6rem 0">'
            f'<div style="font-family:Space Mono,monospace;font-size:.7rem;'
            f'color:{accent};letter-spacing:2px;margin-bottom:.6rem">{title}</div>'
            f'<div style="font-size:.88rem;color:#c8d6e8;line-height:1.65">{content}</div></div>')


# ── PARSE AI RESPONSE ──────────────────────────────────────────────────────
def parse_response(text: str) -> dict:
    result = {"score": 0, "strengths": [], "weaknesses": [],
              "suggestions": [], "skills": {}, "keywords": [], "raw": text}

    m = re.search(r"ATS Score[:\s]+(\d+)", text, re.IGNORECASE)
    if m:
        result["score"] = int(m.group(1))

    def bullets(section):
        m2 = re.search(rf"{section}.*?\n(.*?)(?=\n[A-Z]|\Z)", text, re.DOTALL | re.IGNORECASE)
        if not m2:
            return []
        return [i.strip() for i in re.findall(r"[-*]\s*(.+)", m2.group(1)) if i.strip()]

    result["strengths"]   = bullets("Strengths")
    result["weaknesses"]  = bullets("Weaknesses")
    result["suggestions"] = bullets("Suggestions")

    skill_map = {
        "Leadership":      ["lead","manag","direct","supervis","head"],
        "Communication":   ["communicat","present","report","collaborat"],
        "Technical":       ["python","java","sql","cloud","engineer","develop"],
        "Problem Solving": ["analyz","solv","optim","debug","design"],
        "Impact":          ["increas","reduc","improv","achiev","deliver","launch"],
    }
    lower = text.lower()
    for skill, hints in skill_map.items():
        hits = sum(1 for h in hints if h in lower)
        result["skills"][skill] = min(95, 30 + hits * 13)

    for kw in ["Python","SQL","Leadership","Agile","Communication","Management",
               "Data Analysis","Cloud","Machine Learning","Project Management",
               "Problem Solving","Teamwork"]:
        result["keywords"].append((kw, kw.lower() in lower))

    return result


# ── CALL OPENROUTER ────────────────────────────────────────────────────────
def call_openrouter(resume_text: str, status_el) -> str:
    if not OPENROUTER_API_KEY:
        raise EnvironmentError("OPENROUTER_API_KEY not set in .env")

    MAX = 3500
    chunk = resume_text[:MAX] + ("\n[truncated]" if len(resume_text) > MAX else "")
    prompt = (
        "You are an expert ATS analyst. Analyse the resume below and respond in EXACTLY this format:\n\n"
        "ATS Score: <0-100>\n\nStrengths:\n- <point>\n- <point>\n- <point>\n\n"
        "Weaknesses:\n- <point>\n- <point>\n- <point>\n\n"
        "Suggestions:\n- <point>\n- <point>\n- <point>\n- <point>\n\n"
        f"Resume:\n{chunk}"
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://resumeiq.app",
        "X-Title": "ResumeIQ Dashboard",
    }
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": True}

    collected = []
    resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                         headers=headers, json=payload, stream=True, timeout=90)
    resp.raise_for_status()

    for line in resp.iter_lines():
        if not line:
            continue
        raw = line.decode("utf-8")
        if raw.startswith("data: "):
            raw = raw[6:]
        if raw.strip() == "[DONE]":
            break
        try:
            delta = json.loads(raw)["choices"][0]["delta"].get("content", "")
            if delta:
                collected.append(delta)
                status_el.markdown(f"⏳ Analysing… **{sum(len(c) for c in collected)}** chars received")
        except Exception:
            continue

    status_el.empty()
    return "".join(collected)


# ===========================================================================
# SIDEBAR
# ===========================================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0 .5rem">
      <span style="font-family:'Space Mono',monospace;font-size:1.4rem;font-weight:700;color:#f0a500;letter-spacing:3px">RESUME IQ</span><br>
      <span style="font-size:.72rem;color:#4a6fa5;letter-spacing:2px">ATS INTELLIGENCE PLATFORM</span>
    </div>""", unsafe_allow_html=True)
    st.divider()
    st.markdown("### 📋 How It Works")
    for n, desc in [("01","Upload your PDF resume"),("02","Text is extracted automatically"),
                    ("03","AI analyses ATS compatibility"),("04","Review your dashboard")]:
        st.markdown(
            f'<div style="display:flex;gap:10px;align-items:flex-start;margin:.5rem 0">'
            f'<span style="font-family:Space Mono,monospace;font-size:.7rem;color:#f0a500;'
            f'background:#1a1200;border:1px solid #f0a50044;border-radius:4px;padding:1px 7px;'
            f'white-space:nowrap">{n}</span>'
            f'<span style="font-size:.82rem;color:#8bafd4">{desc}</span></div>',
            unsafe_allow_html=True,
        )
    st.divider()
    st.markdown("### ⚙️ Settings")
    show_raw  = st.toggle("Show raw AI response",    value=False)
    show_text = st.toggle("Show extracted PDF text", value=True)
    st.divider()
    st.markdown("""
    <div style="font-size:.72rem;color:#2e4a6a;text-align:center;line-height:1.8">
      Built with ❤️ using Streamlit<br>OpenRouter API · PDFPlumber<br><br>
      <a href="https://linkedin.com/in/agrima-mishra" style="color:#4a6fa5;text-decoration:none">linkedin.com/in/agrima-mishra</a>
    </div>""", unsafe_allow_html=True)


# ===========================================================================
# HEADER
# ===========================================================================
st.markdown("""
<div style="border-bottom:1px solid #1e3a5f;padding-bottom:1.2rem;margin-bottom:1.5rem">
  <h1 style="font-family:'Space Mono',monospace;font-size:1.6rem;color:#f0a500;margin:0;letter-spacing:3px">
    ◈ RESUME IQ
    <span style="font-size:.7rem;color:#4a6fa5;background:#0d1525;border:1px solid #1e3a5f;
                 border-radius:4px;padding:2px 8px;vertical-align:middle;margin-left:12px;letter-spacing:1px">
      ATS DASHBOARD v2.0
    </span>
  </h1>
  <p style="color:#4a6fa5;margin:.3rem 0 0;font-size:.85rem">
    Upload your resume · Get instant ATS intelligence · Land more interviews
  </p>
</div>""", unsafe_allow_html=True)

# API key guard
if not OPENROUTER_API_KEY:
    st.markdown(card("⛔ CONFIGURATION ERROR",
        "OPENROUTER_API_KEY not found. Create a <code>.env</code> file and add:<br>"
        "<code>OPENROUTER_API_KEY=your_key_here</code><br><br>"
        'Get a free key at <a href="https://openrouter.ai" style="color:#f0a500">openrouter.ai</a>',
        "#ef4444"), unsafe_allow_html=True)
    st.stop()

# ===========================================================================
# UPLOAD
# ===========================================================================
col_up, col_info = st.columns([2, 1], gap="large")
with col_up:
    st.markdown('<p style="font-family:Space Mono,monospace;font-size:.72rem;color:#4a6fa5;letter-spacing:2px;margin-bottom:.4rem">STEP 01 — UPLOAD RESUME</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Drop your PDF here", type=["pdf"], label_visibility="collapsed")
with col_info:
    st.markdown("""
    <div style="background:#0d1525;border:1px solid #1e3a5f;border-radius:8px;padding:1rem">
      <div style="font-family:Space Mono,monospace;font-size:.65rem;color:#4a6fa5;letter-spacing:2px;margin-bottom:.6rem">QUICK TIPS</div>
      <ul style="font-size:.78rem;color:#8bafd4;margin:0;padding-left:1.1rem;line-height:1.9">
        <li>PDF format only</li><li>Selectable text required</li>
        <li>1–3 pages works best</li><li>English language only</li>
      </ul>
    </div>""", unsafe_allow_html=True)

if uploaded_file is None:
    st.markdown('<div style="text-align:center;padding:3rem 0;color:#2e4a6a;font-family:Space Mono,monospace;font-size:.8rem;letter-spacing:2px">── AWAITING RESUME UPLOAD ──</div>', unsafe_allow_html=True)
    st.stop()

# Extract text
with st.spinner("Reading PDF…"):
    extracted = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    extracted += t + "\n"
        if not extracted.strip():
            st.error("No readable text found. Is this a scanned PDF?"); st.stop()
    except Exception as e:
        st.error(f"PDF extraction failed: {e}"); st.stop()

word_count = len(extracted.split())
st.markdown(
    f'<div style="background:#0f2a1a;border:1px solid #22c55e44;border-radius:8px;'
    f'padding:.6rem 1rem;margin:.8rem 0;font-family:Space Mono,monospace;font-size:.75rem;color:#22c55e">'
    f'✓ PDF parsed — {word_count:,} words · {len(extracted):,} characters · {uploaded_file.name}</div>',
    unsafe_allow_html=True,
)

if show_text:
    with st.expander("📄 Extracted Resume Text", expanded=False):
        st.text_area("", extracted, height=180, label_visibility="collapsed")

st.divider()

# ===========================================================================
# ANALYSE BUTTON
# ===========================================================================
st.markdown('<p style="font-family:Space Mono,monospace;font-size:.72rem;color:#4a6fa5;letter-spacing:2px;margin-bottom:.4rem">STEP 02 — RUN ANALYSIS</p>', unsafe_allow_html=True)
col_btn, col_note = st.columns([1, 3])
with col_btn:
    run = st.button("🚀 ANALYSE RESUME", use_container_width=True)
with col_note:
    st.markdown('<span style="font-size:.78rem;color:#2e4a6a">Analysis takes ~15 seconds · Uses OpenRouter GPT-3.5-turbo</span>', unsafe_allow_html=True)

if not run:
    st.stop()

# ===========================================================================
# CALL AI
# ===========================================================================
status_ph = st.empty()
with st.spinner("Connecting to AI…"):
    try:
        ai_text = call_openrouter(extracted, status_ph)
    except EnvironmentError as e:
        st.error(str(e)); st.stop()
    except requests.exceptions.Timeout:
        st.error("Request timed out after 90 s. Try again."); st.stop()
    except Exception as e:
        st.error(f"API error: {e}"); st.stop()

data = parse_response(ai_text)

# ===========================================================================
# DASHBOARD
# ===========================================================================
st.markdown('<div style="font-family:Space Mono,monospace;font-size:.72rem;color:#4a6fa5;letter-spacing:2px;margin:1rem 0 .4rem">STEP 03 — YOUR DASHBOARD</div>', unsafe_allow_html=True)
st.divider()

# Gauge + metrics
top_left, top_right = st.columns([1, 2], gap="large")
with top_left:
    st.markdown(render_gauge(data["score"]), unsafe_allow_html=True)
with top_right:
    m1, m2, m3 = st.columns(3)
    m1.metric("Strengths Found",  len(data["strengths"]))
    m2.metric("Weaknesses Found", len(data["weaknesses"]))
    m3.metric("Action Items",     len(data["suggestions"]))
    score = data["score"]
    bar_color = "#22c55e" if score >= 75 else "#f0a500" if score >= 55 else "#ef4444"
    st.markdown(
        f'<div style="margin-top:.8rem">'
        f'<div style="font-family:Space Mono,monospace;font-size:.65rem;color:#4a6fa5;letter-spacing:2px;margin-bottom:5px">ATS COMPATIBILITY</div>'
        f'<div style="background:#1e3a5f;border-radius:6px;height:10px;overflow:hidden">'
        f'<div style="height:100%;width:{score}%;background:{bar_color};border-radius:6px;box-shadow:0 0 10px {bar_color}88"></div></div>'
        f'<div style="font-family:Space Mono,monospace;font-size:.7rem;color:{bar_color};margin-top:4px">{score}/100</div></div>',
        unsafe_allow_html=True,
    )

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊  Skill Radar","✅  Strengths","⚠️  Weaknesses & Fixes","🔑  Keywords"])

with tab1:
    st.markdown('<div style="font-family:Space Mono,monospace;font-size:.68rem;color:#4a6fa5;letter-spacing:2px;margin-bottom:.8rem">DETECTED SKILL SIGNALS</div>', unsafe_allow_html=True)
    colors = ["#f0a500","#22c55e","#3b82f6","#a855f7","#ef4444"]
    st.markdown("".join(skill_bar(s, p, colors[i % 5]) for i, (s, p) in enumerate(data["skills"].items())), unsafe_allow_html=True)
    st.markdown('<div style="font-size:.72rem;color:#2e4a6a;font-family:Space Mono,monospace;margin-top:1rem">* Scores estimated from keyword frequency in your resume.</div>', unsafe_allow_html=True)

with tab2:
    if data["strengths"]:
        for s in data["strengths"]:
            st.markdown(card("◆ STRENGTH", s, "#22c55e"), unsafe_allow_html=True)
    else:
        st.info("No strengths detected.")

with tab3:
    col_w, col_s = st.columns(2, gap="medium")
    with col_w:
        st.markdown('<div style="font-family:Space Mono,monospace;font-size:.68rem;color:#ef4444;letter-spacing:2px;margin-bottom:.6rem">CRITICAL WEAKNESSES</div>', unsafe_allow_html=True)
        for w in data["weaknesses"]:
            st.markdown(card("▲ ISSUE", w, "#ef4444"), unsafe_allow_html=True)
        if not data["weaknesses"]:
            st.info("No weaknesses detected.")
    with col_s:
        st.markdown('<div style="font-family:Space Mono,monospace;font-size:.68rem;color:#3b82f6;letter-spacing:2px;margin-bottom:.6rem">ACTIONABLE FIXES</div>', unsafe_allow_html=True)
        for i, sg in enumerate(data["suggestions"], 1):
            st.markdown(card(f"FIX {i:02d}", sg, "#3b82f6"), unsafe_allow_html=True)
        if not data["suggestions"]:
            st.info("No suggestions found.")

with tab4:
    st.markdown('<div style="font-family:Space Mono,monospace;font-size:.68rem;color:#4a6fa5;letter-spacing:2px;margin-bottom:.6rem">ATS KEYWORD PRESENCE CHECK</div>', unsafe_allow_html=True)
    found_count = sum(1 for _, f in data["keywords"] if f)
    st.markdown(f'<div style="margin-bottom:.8rem;font-family:Space Mono,monospace;font-size:.75rem;color:#8bafd4">Found <span style="color:#22c55e">{found_count}</span> / {len(data["keywords"])} common ATS keywords</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="line-height:2.2">{"".join(keyword_chip(kw, f) for kw, f in data["keywords"])}</div>', unsafe_allow_html=True)

if show_raw:
    st.divider()
    with st.expander("🤖 Raw AI Response", expanded=False):
        st.text_area("", ai_text, height=300, label_visibility="collapsed")

st.divider()
st.markdown("""
<div style="text-align:center;font-size:.72rem;color:#2e4a6a;font-family:'Space Mono',monospace;padding:.5rem 0">
  RESUME IQ · Built with ❤️ by
  <a href="https://linkedin.com/in/agrima-mishra" style="color:#4a6fa5;text-decoration:none">Agrima Mishra</a>
  · Powered by Streamlit &amp; OpenRouter
</div>""", unsafe_allow_html=True)
