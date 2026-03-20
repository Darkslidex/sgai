"""
SGAI Dashboard — Le Chef's Console
Entry point. Maneja login y sirve como página de bienvenida.
"""

import streamlit as st

from dashboard.auth import attempt_login, is_authenticated, logout, touch_session
from dashboard.components.styles import LUXURY_CSS, inject_css, section_label_html, gold_rule_html
from dashboard.components.api_client import get_client
from dashboard.config import get_dashboard_settings

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SGAI · Le Chef's Console",
    page_icon="⚜",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ── Sidebar ──────────────────────────────────────────────────────────────────

def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem 1rem 0.5rem; text-align: center;">
            <div style="
                font-family: 'Cinzel', serif;
                font-size: 1.4rem;
                font-weight: 600;
                color: #C9A84C;
                letter-spacing: 0.2em;
            ">⚜ SGAI</div>
            <div style="
                font-family: 'Playfair Display', serif;
                font-style: italic;
                font-size: 0.75rem;
                color: #6B5F47;
                margin-top: 2px;
                letter-spacing: 0.06em;
            ">Le Chef's Console</div>
        </div>
        <div style="
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(201,168,76,0.3), transparent);
            margin: 1rem 0.5rem;
        "></div>
        """, unsafe_allow_html=True)

        if is_authenticated():
            st.markdown("""
            <div style="
                font-family: 'Cinzel', serif;
                font-size: 0.55rem;
                color: #4A3F2F;
                text-transform: uppercase;
                letter-spacing: 0.22em;
                padding: 0 1rem;
                margin-bottom: 0.5rem;
            ">La Carte</div>
            """, unsafe_allow_html=True)

            # Cerrar sesión en sidebar
            st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div style="
                height: 1px;
                background: rgba(201,168,76,0.1);
                margin: 0.5rem 1rem 1rem;
            "></div>
            """, unsafe_allow_html=True)

            if st.button("🔒  Fermer la Session", use_container_width=True):
                logout()


# ── Login Screen ─────────────────────────────────────────────────────────────

def _render_login() -> None:
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("""
        <div style="padding: 4rem 0 2rem; text-align: center;">
            <div style="
                font-size: 3rem;
                margin-bottom: 1.5rem;
                filter: drop-shadow(0 0 20px rgba(201,168,76,0.3));
            ">⚜</div>
            <div style="
                font-family: 'Cinzel', serif;
                font-size: 1.6rem;
                font-weight: 600;
                color: #C9A84C;
                letter-spacing: 0.3em;
                text-transform: uppercase;
                margin-bottom: 0.4rem;
            ">SGAI</div>
            <div style="
                font-family: 'Playfair Display', serif;
                font-style: italic;
                font-size: 1rem;
                color: #6B5F47;
                margin-bottom: 0.2rem;
            ">Le Chef's Console</div>
            <div style="
                font-family: 'Inter', sans-serif;
                font-size: 0.72rem;
                color: #4A3F2F;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin-bottom: 3rem;
            ">Sistema de Gestión Alimenticia Inteligente</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("""
            <div style="
                font-family: 'Cinzel', serif;
                font-size: 0.6rem;
                color: #6B5F47;
                text-transform: uppercase;
                letter-spacing: 0.22em;
                margin-bottom: 1rem;
                text-align: center;
            ">Identificación del Chef</div>
            """, unsafe_allow_html=True)

            username = st.text_input("Usuario", placeholder="chef", label_visibility="collapsed")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••", label_visibility="collapsed")

            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Entrar a la Cocina", use_container_width=True)

            if submitted:
                ok, msg = attempt_login(username, password)
                if ok:
                    st.rerun()
                else:
                    st.markdown(f"""
                    <div style="
                        text-align: center;
                        color: #A86060;
                        font-family: 'Inter', sans-serif;
                        font-size: 0.82rem;
                        margin-top: 0.75rem;
                        padding: 0.75rem;
                        background: rgba(140,60,60,0.08);
                        border: 1px solid rgba(140,60,60,0.2);
                        border-radius: 3px;
                    ">{msg}</div>
                    """, unsafe_allow_html=True)

        st.markdown("""
        <div style="
            text-align: center;
            margin-top: 3rem;
            font-family: 'Playfair Display', serif;
            font-style: italic;
            font-size: 0.8rem;
            color: #3A3025;
        ">"La cocina es el alma del hogar."</div>
        """, unsafe_allow_html=True)


# ── Main Dashboard Home (La Grand Salle) ─────────────────────────────────────

def _render_home() -> None:
    touch_session()
    cfg = get_dashboard_settings()

    # ── Header ──
    st.markdown("""
    <div style="margin-bottom: 0.25rem;">
        <div style="
            font-family: 'Cinzel', serif;
            font-size: 0.6rem;
            color: rgba(201,168,76,0.6);
            text-transform: uppercase;
            letter-spacing: 0.28em;
            margin-bottom: 0.5rem;
        ">La Grand Salle</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("# Le Tableau de Bord")
    st.markdown("""
    <p class="page-subtitle">La vista completa del sistema — todo en un golpe de vista</p>
    """, unsafe_allow_html=True)

    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

    # ── API Status ──
    with get_client() as client:
        alive = client.is_api_reachable()
        profile = client.get_profile(cfg.sgai_user_id) if alive else None
        tdee_data = client.get_tdee(cfg.sgai_user_id) if alive else None
        energy_data = client.get_energy_state(cfg.sgai_user_id) if alive else None
        plan = client.get_active_plan(cfg.sgai_user_id) if alive else None
        pantry = client.get_pantry(cfg.sgai_user_id) if alive else []
        prices = client.get_current_prices() if alive else []
        health_log = client.get_latest_health_log(cfg.sgai_user_id) if alive else None

    if not alive:
        st.markdown("""
        <div class="alert-box alert-warning">
            ⚠️&nbsp;&nbsp;
            <span>API no disponible. Verificá que el servidor SGAI esté corriendo en
            <code style="color:#C9A84C; background:rgba(201,168,76,0.08); padding:1px 6px; border-radius:2px;">
            localhost:8000</code></span>
        </div>
        """, unsafe_allow_html=True)

    # ── KPIs ──
    st.markdown("""
    <div style="
        font-family:'Cinzel',serif; font-size:0.58rem; color:#4A3F2F;
        text-transform:uppercase; letter-spacing:0.22em; margin-bottom:1rem;
    ">Indicadores del Día</div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    # TDEE
    tdee_val = tdee_data.get("tdee", "—") if tdee_data else "—"
    tdee_str = f"{tdee_val:,} kcal" if isinstance(tdee_val, (int, float)) else "—"
    c1.metric("Energía del Día", tdee_str)

    # Plan activo
    plan_str = f"✓ Sem. activa" if plan else "Sin plan"
    plan_cost = f"$ {plan.get('total_cost_ars', 0):,.0f}" if plan else "—"
    c2.metric("Plan Semanal", plan_str, plan_cost)

    # Estado energético
    energy_str = energy_data.get("state", "—") if energy_data else "—"
    _energy_labels = {"NORMAL": "Normal", "LOW": "Baja Energía", "CRITICAL": "Crítico"}
    c3.metric("Estado Energético", _energy_labels.get(energy_str, energy_str))

    # Pantry
    c4.metric("Items en Alacena", f"{len(pantry)} items", f"{len(prices)} con precio")

    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

    # ── Estado del Sistema ──
    st.markdown("""
    <div style="
        font-family:'Cinzel',serif; font-size:0.58rem; color:#4A3F2F;
        text-transform:uppercase; letter-spacing:0.22em; margin-bottom:1rem;
    ">Estado del Sistema</div>
    """, unsafe_allow_html=True)

    s1, s2, s3, s4 = st.columns(4)

    def _status_badge(ok: bool, label: str) -> str:
        icon = "●" if ok else "○"
        color = "#5A9E6F" if ok else "#A86060"
        return f"""
        <div style="
            background: rgba(20,20,20,0.8);
            border: 1px solid rgba(201,168,76,0.12);
            border-radius: 3px;
            padding: 1rem 1.2rem;
            text-align: center;
        ">
            <div style="font-size:1.4rem; color:{color}; margin-bottom:0.4rem;">{icon}</div>
            <div style="
                font-family:'Cinzel',serif; font-size:0.6rem; color:#6B5F47;
                text-transform:uppercase; letter-spacing:0.15em;
            ">{label}</div>
        </div>
        """

    s1.markdown(_status_badge(alive, "API FastAPI"), unsafe_allow_html=True)
    s2.markdown(_status_badge(profile is not None, "Perfil"), unsafe_allow_html=True)
    s3.markdown(_status_badge(bool(plan), "Plan Activo"), unsafe_allow_html=True)
    s4.markdown(_status_badge(bool(prices), "Precios"), unsafe_allow_html=True)

    # ── Navegación rápida ──
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 0.88rem;
        color: #6B5F47;
        text-align: center;
        padding: 1rem 0;
    ">Usá el menú lateral para explorar las secciones del sistema.</div>
    """, unsafe_allow_html=True)


# ── Entry Point ──────────────────────────────────────────────────────────────

_render_sidebar()

if not is_authenticated():
    _render_login()
else:
    _render_home()
