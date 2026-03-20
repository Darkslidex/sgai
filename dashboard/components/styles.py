"""
Sistema de diseño SGAI — Estética de restaurante de lujo.

Paleta:
  - Noir       #080808  (fondo OLED)
  - Charcoal   #141414  (fondo secundario)
  - Slate      #1e1e1e  (cards)
  - Gold       #C9A84C  (acento primario — oro 24k)
  - Gold Light #E8C96A  (hover / highlights)
  - Ivory      #F2E8D5  (texto primario — luz de vela)
  - Tan        #A89B7A  (texto secundario)
  - Muted      #6B5F47  (texto sutil / labels)

Tipografía:
  - Cinzel          → labels ceremoniales, sidebar
  - Playfair Display → títulos, valores KPI
  - Inter           → cuerpo, datos
"""

LUXURY_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&family=Cinzel:wght@400;600&display=swap');

/* ── Reset & Base ──────────────────────────────────────────────────── */
* { box-sizing: border-box; }

.stApp {
    background-color: #080808;
    color: #F2E8D5;
    font-family: 'Inter', -apple-system, sans-serif;
}

/* ── Sidebar — Tasting Menu ────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c0c0c 0%, #101010 100%);
    border-right: 1px solid rgba(201, 168, 76, 0.18);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

/* Navigation links */
[data-testid="stSidebarNav"] {
    padding: 0.5rem 0;
}

[data-testid="stSidebarNav"] a {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 400;
    color: #7A6E58 !important;
    letter-spacing: 0.04em;
    padding: 10px 20px !important;
    border-left: 2px solid transparent;
    transition: all 0.25s ease;
    display: block;
    text-decoration: none;
}

[data-testid="stSidebarNav"] a:hover {
    color: #C9A84C !important;
    border-left: 2px solid rgba(201, 168, 76, 0.5);
    background: rgba(201, 168, 76, 0.04);
}

[data-testid="stSidebarNav"] a[aria-current="page"] {
    color: #C9A84C !important;
    border-left: 2px solid #C9A84C;
    background: rgba(201, 168, 76, 0.07);
}

/* ── Main Content ──────────────────────────────────────────────────── */
.main .block-container {
    padding: 2.5rem 3rem 4rem;
    max-width: 1400px;
}

/* ── Typography ────────────────────────────────────────────────────── */
h1 {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 2rem !important;
    font-weight: 600 !important;
    color: #F2E8D5 !important;
    letter-spacing: 0.01em;
    line-height: 1.2;
    margin-bottom: 0.25rem !important;
}

h2 {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 1.3rem !important;
    font-weight: 400 !important;
    color: #C9A84C !important;
    letter-spacing: 0.02em;
}

h3 {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    color: #6B5F47 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.18em !important;
}

p { color: #A89B7A; line-height: 1.7; }

/* ── KPI Cards (HTML components) ──────────────────────────────────── */
.kpi-card {
    background: linear-gradient(145deg, #1a1a1a 0%, #141414 100%);
    border: 1px solid rgba(201, 168, 76, 0.2);
    border-radius: 3px;
    padding: 1.4rem 1.6rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s ease, transform 0.2s ease;
    height: 100%;
}

.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(201,168,76,0.6) 50%, transparent 100%);
}

.kpi-card::after {
    content: '';
    position: absolute;
    bottom: 0; right: 0;
    width: 60px; height: 60px;
    background: radial-gradient(circle, rgba(201,168,76,0.04) 0%, transparent 70%);
    border-radius: 50%;
}

.kpi-card:hover {
    border-color: rgba(201, 168, 76, 0.4);
    transform: translateY(-1px);
}

.kpi-icon {
    font-size: 1.2rem;
    margin-bottom: 0.75rem;
    opacity: 0.7;
}

.kpi-label {
    font-family: 'Cinzel', serif;
    font-size: 0.6rem;
    font-weight: 600;
    color: #6B5F47;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    margin-bottom: 0.6rem;
}

.kpi-value {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    color: #F2E8D5;
    line-height: 1.1;
    margin-bottom: 0.3rem;
}

.kpi-value-sm {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    font-weight: 600;
    color: #F2E8D5;
    line-height: 1.2;
    margin-bottom: 0.3rem;
}

.kpi-sub {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: #6B5F47;
    margin-top: 0.3rem;
}

.kpi-delta {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
    margin-top: 0.4rem;
}

.kpi-delta.up    { color: #5A9E6F; }
.kpi-delta.down  { color: #A86060; }
.kpi-delta.flat  { color: #6B5F47; }

/* ── Dividers ──────────────────────────────────────────────────────── */
.gold-rule {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(201,168,76,0.35), transparent);
    border: none;
    margin: 1.8rem 0;
}

hr {
    border: none !important;
    border-top: 1px solid rgba(201,168,76,0.12) !important;
    margin: 1.5rem 0 !important;
}

/* ── Section Labels (Cinzel) ───────────────────────────────────────── */
.section-label {
    font-family: 'Cinzel', serif;
    font-size: 0.6rem;
    color: rgba(201, 168, 76, 0.7);
    text-transform: uppercase;
    letter-spacing: 0.28em;
    margin-bottom: 1.2rem;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid rgba(201, 168, 76, 0.1);
}

/* Page subtitle */
.page-subtitle {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    font-size: 0.95rem;
    color: #6B5F47;
    margin-bottom: 2rem;
    margin-top: 0;
}

/* ── Status Badges ─────────────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 2px;
    font-family: 'Inter', sans-serif;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    vertical-align: middle;
}

.badge-gold   { background: rgba(201,168,76,0.12); color: #C9A84C;  border: 1px solid rgba(201,168,76,0.25); }
.badge-green  { background: rgba(74,140,92,0.12);  color: #5A9E6F;  border: 1px solid rgba(74,140,92,0.25);  }
.badge-red    { background: rgba(140,58,58,0.12);  color: #C47B7B;  border: 1px solid rgba(140,58,58,0.25);  }
.badge-gray   { background: rgba(107,95,71,0.10);  color: #A89B7A;  border: 1px solid rgba(107,95,71,0.2);   }
.badge-blue   { background: rgba(58,100,140,0.12); color: #7BA8C4;  border: 1px solid rgba(58,100,140,0.25); }

/* ── Alert Boxes ───────────────────────────────────────────────────── */
.alert-box {
    padding: 1rem 1.25rem;
    border-radius: 3px;
    margin: 0.75rem 0;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

.alert-warning {
    background: rgba(180,120,20,0.08);
    border-left: 3px solid rgba(201,168,76,0.5);
    color: #A89B7A;
}

.alert-danger {
    background: rgba(140,40,40,0.08);
    border-left: 3px solid rgba(168,80,80,0.5);
    color: #C47B7B;
}

.alert-success {
    background: rgba(40,100,60,0.08);
    border-left: 3px solid rgba(74,140,92,0.5);
    color: #5A9E6F;
}

.alert-info {
    background: rgba(40,70,120,0.08);
    border-left: 3px solid rgba(58,100,168,0.5);
    color: #7BA8C4;
}

/* ── Streamlit Native Widget Overrides ─────────────────────────────── */

/* Metric containers */
[data-testid="metric-container"] {
    background: linear-gradient(145deg, #1a1a1a, #141414) !important;
    border: 1px solid rgba(201, 168, 76, 0.18) !important;
    border-radius: 3px !important;
    padding: 1.2rem 1.4rem !important;
    transition: border-color 0.3s ease;
}

[data-testid="metric-container"]:hover {
    border-color: rgba(201, 168, 76, 0.35) !important;
}

[data-testid="stMetricValue"] {
    font-family: 'Playfair Display', serif !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #F2E8D5 !important;
}

[data-testid="stMetricLabel"] {
    font-family: 'Cinzel', serif !important;
    font-size: 0.6rem !important;
    font-weight: 600 !important;
    color: #6B5F47 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.15em !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
    font-weight: 500;
}

/* Inputs */
.stTextInput input,
.stNumberInput input,
.stSelectbox select,
.stTextArea textarea {
    background: #141414 !important;
    border: 1px solid rgba(201,168,76,0.2) !important;
    color: #F2E8D5 !important;
    border-radius: 3px !important;
    font-family: 'Inter', sans-serif !important;
}

.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border-color: rgba(201,168,76,0.5) !important;
    box-shadow: 0 0 0 1px rgba(201,168,76,0.2) !important;
}

/* Buttons */
.stButton > button {
    background: transparent !important;
    border: 1px solid rgba(201,168,76,0.4) !important;
    color: #C9A84C !important;
    font-family: 'Cinzel', serif !important;
    font-size: 0.65rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    border-radius: 2px !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.25s ease !important;
}

.stButton > button:hover {
    background: rgba(201,168,76,0.08) !important;
    border-color: #C9A84C !important;
    color: #E8C96A !important;
}

.stButton > button:active {
    background: rgba(201,168,76,0.15) !important;
}

/* Primary button variant */
.stButton > button[kind="primary"] {
    background: rgba(201,168,76,0.12) !important;
    border-color: #C9A84C !important;
}

/* Select box */
.stSelectbox [data-baseweb="select"] > div {
    background: #141414 !important;
    border: 1px solid rgba(201,168,76,0.2) !important;
    color: #F2E8D5 !important;
}

/* Slider */
.stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
    color: #C9A84C !important;
}

/* Toggle */
.stCheckbox [data-testid="stCheckbox"] > label {
    color: #A89B7A !important;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
}

/* ── Tables / DataFrames ───────────────────────────────────────────── */
.stDataFrame {
    border: 1px solid rgba(201,168,76,0.15) !important;
    border-radius: 3px !important;
    overflow: hidden;
}

[data-testid="stTable"] {
    border: 1px solid rgba(201,168,76,0.15);
}

/* ── Tabs ──────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(201,168,76,0.15) !important;
    gap: 0 !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #6B5F47 !important;
    font-family: 'Cinzel', serif !important;
    font-size: 0.62rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    padding: 12px 24px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #A89B7A !important;
}

.stTabs [aria-selected="true"] {
    color: #C9A84C !important;
    border-bottom: 2px solid #C9A84C !important;
    background: transparent !important;
}

/* ── Expander ──────────────────────────────────────────────────────── */
[data-testid="expander"] {
    background: #141414 !important;
    border: 1px solid rgba(201,168,76,0.12) !important;
    border-radius: 3px !important;
}

/* ── Progress bar ──────────────────────────────────────────────────── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #8A6F2E, #C9A84C) !important;
    border-radius: 2px;
}

.stProgress > div > div {
    background: rgba(201,168,76,0.1) !important;
    border-radius: 2px;
}

/* ── Info/warning boxes ────────────────────────────────────────────── */
.stAlert {
    background: #141414 !important;
    border: 1px solid rgba(201,168,76,0.2) !important;
    color: #A89B7A !important;
    border-radius: 3px !important;
}

/* ── Scrollbar ─────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0c0c0c; }
::-webkit-scrollbar-thumb { background: #2d2820; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(201,168,76,0.4); }

/* ── Hide Streamlit Chrome ─────────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* ── Login Page ────────────────────────────────────────────────────── */
.login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 3rem 0;
}

.login-logo {
    text-align: center;
    margin-bottom: 3rem;
}

.login-title {
    font-family: 'Cinzel', serif;
    font-size: 1.4rem;
    font-weight: 600;
    color: #C9A84C;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    text-align: center;
    margin-bottom: 0.3rem;
}

.login-subtitle {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    font-size: 0.9rem;
    color: #6B5F47;
    text-align: center;
    margin-bottom: 2rem;
}

/* ── Empty State ───────────────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 3rem 2rem;
    color: #6B5F47;
}

.empty-state-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    opacity: 0.4;
}

.empty-state-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    color: #A89B7A;
    margin-bottom: 0.5rem;
}

.empty-state-text {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: #5A4F3E;
    line-height: 1.6;
}
</style>
"""


def inject_css() -> None:
    """Inyecta el sistema de diseño luxury en la página actual."""
    import streamlit as st
    st.markdown(LUXURY_CSS, unsafe_allow_html=True)


# ── Helpers de componentes HTML ──────────────────────────────────────────────

def kpi_card_html(
    label: str,
    value: str,
    sub: str = "",
    delta: str = "",
    delta_dir: str = "flat",   # "up" | "down" | "flat"
    icon: str = "",
) -> str:
    """Genera HTML de una tarjeta KPI."""
    icon_html = f'<div class="kpi-icon">{icon}</div>' if icon else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""

    delta_arrow = {"up": "↑", "down": "↓", "flat": "—"}.get(delta_dir, "")
    delta_html = (
        f'<div class="kpi-delta {delta_dir}">{delta_arrow} {delta}</div>'
        if delta else ""
    )

    return f"""
    <div class="kpi-card">
        {icon_html}
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
        {delta_html}
    </div>
    """


def section_label_html(text: str) -> str:
    return f'<div class="section-label">{text}</div>'


def gold_rule_html() -> str:
    return '<div class="gold-rule"></div>'


def badge_html(text: str, variant: str = "gold") -> str:
    return f'<span class="badge badge-{variant}">{text}</span>'


def alert_html(text: str, variant: str = "warning", icon: str = "") -> str:
    icon_str = f"<span>{icon}&nbsp;&nbsp;</span>" if icon else ""
    return f'<div class="alert-box alert-{variant}">{icon_str}<span>{text}</span></div>'


def empty_state_html(title: str, text: str = "", icon: str = "🍽") -> str:
    return f"""
    <div class="empty-state">
        <div class="empty-state-icon">{icon}</div>
        <div class="empty-state-title">{title}</div>
        <div class="empty-state-text">{text}</div>
    </div>
    """
