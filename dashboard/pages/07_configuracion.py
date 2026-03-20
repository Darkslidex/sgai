"""
Les Coulisses — Configuración y Gobernanza
Perfil, preferencias, sistema y gobernanza del bot.
"""

import streamlit as st

from dashboard.auth import require_auth, touch_session
from dashboard.components.styles import inject_css
from dashboard.components.api_client import get_client
from dashboard.config import get_dashboard_settings

st.set_page_config(page_title="Configuración · SGAI", page_icon="⚜", layout="wide")
inject_css()
require_auth()
touch_session()

cfg = get_dashboard_settings()

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Cinzel',serif;font-size:0.58rem;color:rgba(201,168,76,0.6);
    text-transform:uppercase;letter-spacing:0.28em;margin-bottom:0.5rem;">Les Coulisses</div>
""", unsafe_allow_html=True)
st.markdown("# Configuración")
st.markdown('<p class="page-subtitle">Las preferencias y gobernanza del sistema</p>',
            unsafe_allow_html=True)
st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────

with get_client() as client:
    alive       = client.is_api_reachable()
    profile     = client.get_profile(cfg.sgai_user_id) if alive else None
    preferences = client.get_preferences(cfg.sgai_user_id) if alive else []
    system_h    = client.get_system_health() if alive else None

if not alive:
    st.warning("API no disponible.")

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_profile, tab_prefs, tab_gov, tab_system = st.tabs([
    "Perfil", "Preferencias", "Gobernanza", "Sistema"
])

# ── Perfil ────────────────────────────────────────────────────────────────────

with tab_profile:
    st.markdown("### Perfil Nutricional")

    if profile:
        with st.form("form_profile"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Nombre", value=profile.get("name", ""))
                age  = st.number_input("Edad", value=profile.get("age", 30),
                                       min_value=15, max_value=100, step=1)
                weight = st.number_input("Peso (kg)", value=float(profile.get("weight_kg", 70)),
                                         min_value=30.0, max_value=250.0, step=0.5)

            with col2:
                height = st.number_input("Altura (cm)", value=float(profile.get("height_cm", 170)),
                                          min_value=130.0, max_value=230.0, step=1.0)
                activity = st.selectbox(
                    "Nivel de Actividad",
                    ["sedentary", "light", "moderate", "active", "very_active"],
                    index=["sedentary", "light", "moderate", "active", "very_active"].index(
                        profile.get("activity_level", "moderate")
                    ),
                )
                goal = st.selectbox(
                    "Objetivo",
                    ["maintain", "lose", "gain"],
                    index=["maintain", "lose", "gain"].index(profile.get("goal", "maintain")),
                )

            submitted = st.form_submit_button("Guardar Perfil", use_container_width=True)
            if submitted:
                with get_client() as client:
                    result = client.update_profile(cfg.sgai_user_id, {
                        "name": name, "age": age, "weight_kg": weight,
                        "height_cm": height, "activity_level": activity, "goal": goal,
                    })
                if result:
                    st.success("✓ Perfil actualizado correctamente.")
                else:
                    st.error("No se pudo actualizar el perfil.")

        # ── Resumen del perfil actual ──
        _labels = {
            "sedentary": "Sedentario", "light": "Ligero", "moderate": "Moderado",
            "active": "Activo", "very_active": "Muy Activo",
        }
        _goals = {"maintain": "Mantener", "lose": "Bajar peso", "gain": "Subir masa"}

        st.markdown(f"""
        <div style="
            display:grid; grid-template-columns:repeat(3,1fr); gap:1rem;
            margin-top:1.5rem;
        ">
            {_info_box("Nombre", profile.get('name','—'))}
            {_info_box("Edad", f"{profile.get('age','?')} años")}
            {_info_box("Peso / Altura",
              f"{profile.get('weight_kg','?')} kg / {profile.get('height_cm','?')} cm")}
            {_info_box("Actividad", _labels.get(profile.get('activity_level','?'),'?'))}
            {_info_box("Objetivo", _goals.get(profile.get('goal','?'),'?'))}
            {_info_box("Almacenamiento", str(profile.get('max_storage_volume','—')))}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">👤</div>
            <div class="empty-state-title">Sin perfil configurado</div>
            <div class="empty-state-text">Usá /setup en Telegram para crear tu perfil.</div>
        </div>
        """, unsafe_allow_html=True)

# ── Preferencias ──────────────────────────────────────────────────────────────

with tab_prefs:
    st.markdown("### Preferencias Alimentarias")

    if preferences:
        for pref in preferences:
            col_k, col_v, col_del = st.columns([2, 2, 1])
            col_k.markdown(f"**{pref.get('key', '—')}**")
            col_v.markdown(f"`{pref.get('value', '—')}`")
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🥗</div>
            <div class="empty-state-title">Sin preferencias registradas</div>
            <div class="empty-state-text">
                Las preferencias se configuran desde Telegram durante el /setup.<br>
                Ejemplos: sin_gluten, vegetariano, alergia_mani
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Gobernanza ────────────────────────────────────────────────────────────────

with tab_gov:
    st.markdown("### Configuración del Sistema")

    st.markdown("""
    <div style="
        background:rgba(201,168,76,0.04); border:1px solid rgba(201,168,76,0.12);
        border-radius:3px; padding:1.2rem 1.5rem; margin-bottom:1.5rem;
    ">
        <div style="font-family:'Cinzel',serif;font-size:0.6rem;color:#6B5F47;
            text-transform:uppercase;letter-spacing:0.18em;margin-bottom:0.5rem;">Nota</div>
        <div style="font-size:0.82rem;color:#A89B7A;line-height:1.6;">
            La gobernanza del bot se configura a través de las preferencias y el perfil.
            Los ajustes de notificaciones y simplificación automática se implementarán
            en Fase 4B como preferencias de usuario en la API.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        notify = st.toggle("Notificaciones proactivas del bot", value=True)
        weekly_report = st.toggle("Reportes semanales automáticos", value=True)

    with col2:
        simplification = st.slider(
            "Nivel de simplificación automática",
            min_value=1, max_value=5, value=2,
            help="1 = nunca simplificar | 5 = simplificar agresivamente",
        )

    st.caption("Configuración guardada localmente — integración con API en Fase 4B.")

# ── Sistema ───────────────────────────────────────────────────────────────────

with tab_system:
    st.markdown("### Estado del Sistema")

    if system_h:
        status_color = "#5A9E6F" if system_h.get("status") == "ok" else "#A86060"
        st.markdown(f"""
        <div style="
            display:grid; grid-template-columns:repeat(2,1fr); gap:1rem; margin-bottom:1.5rem;
        ">
            {_info_box("Estado API", system_h.get('status','—').upper(), status_color)}
            {_info_box("Versión", system_h.get('version','—'))}
            {_info_box("Base de Datos", "✓ Conectada" if system_h.get('database') else "—")}
            {_info_box("Uptime", system_h.get('uptime','—'))}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-box alert-danger">
            🔴&nbsp;&nbsp;<span>API no disponible — verificá que el servidor SGAI esté corriendo.</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
    st.markdown("### Configuración del Dashboard")

    st.code(f"""
API Base URL : {cfg.api_base_url}
Usuario      : {cfg.dashboard_user}
Timeout      : {cfg.session_timeout_minutes} min
User ID      : {cfg.sgai_user_id}
    """.strip(), language="text")


# ── Helper ───────────────────────────────────────────────────────────────────

def _info_box(label: str, value: str, color: str = "#C9A84C") -> str:
    return f"""
    <div style="
        background:rgba(20,20,20,0.5); border:1px solid rgba(201,168,76,0.1);
        border-radius:3px; padding:0.9rem 1.1rem;
    ">
        <div style="font-family:'Cinzel',serif;font-size:0.58rem;color:#4A3F2F;
            text-transform:uppercase;letter-spacing:0.18em;margin-bottom:0.4rem;">{label}</div>
        <div style="font-family:'Playfair Display',serif;font-size:1rem;color:{color};">
            {value}
        </div>
    </div>
    """
