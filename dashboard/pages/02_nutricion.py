"""
Le Corps — Salud y Nutrición
TDEE dinámico, biomarcadores, historial de métricas.
"""

import streamlit as st
import pandas as pd

from dashboard.auth import require_auth, touch_session
from dashboard.components.styles import inject_css
from dashboard.components.api_client import get_client
from dashboard.components.charts import line_chart, bar_chart, gauge_chart, heatmap
from dashboard.config import get_dashboard_settings

st.set_page_config(page_title="Nutrición · SGAI", page_icon="⚜", layout="wide")
inject_css()
require_auth()
touch_session()

cfg = get_dashboard_settings()

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Cinzel',serif;font-size:0.58rem;color:rgba(201,168,76,0.6);
    text-transform:uppercase;letter-spacing:0.28em;margin-bottom:0.5rem;">Le Corps</div>
""", unsafe_allow_html=True)
st.markdown("# Salud y Nutrición")
st.markdown('<p class="page-subtitle">El combustible del chef — energía, sueño y bienestar</p>',
            unsafe_allow_html=True)
st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────

with get_client() as client:
    alive       = client.is_api_reachable()
    tdee_data   = client.get_tdee(cfg.sgai_user_id) if alive else None
    energy_data = client.get_energy_state(cfg.sgai_user_id) if alive else None
    health_logs = client.get_health_logs(cfg.sgai_user_id, days=30) if alive else []
    latest_log  = client.get_latest_health_log(cfg.sgai_user_id) if alive else None
    weekly_avg  = client.get_weekly_avg(cfg.sgai_user_id) if alive else None

if not alive:
    st.warning("API no disponible.")
    st.stop()

# ── TDEE KPIs ────────────────────────────────────────────────────────────────

tdee_val = tdee_data.get("tdee", 0) if tdee_data else 0
activity = tdee_data.get("activity_multiplier", "—") if tdee_data else "—"
goal_m   = tdee_data.get("goal_multiplier", "—") if tdee_data else "—"
bmr      = tdee_data.get("breakdown", {}).get("bmr_kcal", "—") if tdee_data else "—"

k1, k2, k3, k4 = st.columns(4)
k1.metric("TDEE Dinámico", f"{tdee_val:,.0f} kcal" if tdee_val else "—")
k2.metric("BMR Base", f"{bmr} kcal" if bmr != "—" else "—")
k3.metric("Actividad (×)", str(activity))
k4.metric("Objetivo (×)", str(goal_m))

# ── Estado energético ─────────────────────────────────────────────────────────

st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

if energy_data:
    state = energy_data.get("state", "NORMAL")
    hrv   = energy_data.get("hrv") if energy_data else None
    sleep = energy_data.get("sleep_score") if energy_data else None
    stress= energy_data.get("stress_level") if energy_data else None

    _state_colors = {"NORMAL": "#5A9E6F", "LOW": "#C9A84C", "CRITICAL": "#A86060"}
    _state_labels = {"NORMAL": "Normal", "LOW": "Baja Energía", "CRITICAL": "Crítico"}

    color = _state_colors.get(state, "#A89B7A")
    label = _state_labels.get(state, state)

    st.markdown(f"""
    <div style="
        background: rgba(20,20,20,0.6);
        border: 1px solid {color}40;
        border-left: 3px solid {color};
        border-radius: 3px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    ">
        <div style="font-size:2rem;">
            {"✅" if state == "NORMAL" else "⚠️" if state == "LOW" else "🚨"}
        </div>
        <div>
            <div style="font-family:'Cinzel',serif;font-size:0.6rem;color:{color};
                text-transform:uppercase;letter-spacing:0.2em;">Estado Energético</div>
            <div style="font-family:'Playfair Display',serif;font-size:1.3rem;color:#F2E8D5;
                margin:0.2rem 0;">{label}</div>
            <div style="font-size:0.8rem;color:#6B5F47;">
                Basado en HRV, sueño y nivel de estrés (ADR-008)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Gauges biomarcadores ──────────────────────────────────────────────────────

if latest_log:
    g1, g2, g3 = st.columns(3)

    with g1:
        st.markdown("### Sueño")
        sleep_val = latest_log.get("sleep_score") or 0
        fig = gauge_chart(sleep_val, 100, "Score de Sueño", "/100", height=200)
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        st.markdown("### Estrés")
        stress_val = latest_log.get("stress_level") or 0
        fig2 = gauge_chart(stress_val, 10, "Nivel de Estrés", "/10", height=200)
        st.plotly_chart(fig2, use_container_width=True)

    with g3:
        st.markdown("### HRV")
        hrv_val = latest_log.get("hrv") or 0
        fig3 = gauge_chart(hrv_val, 100, "HRV (ms)", " ms", height=200)
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Gráficos históricos ───────────────────────────────────────────────────────

if health_logs:
    df = pd.DataFrame(health_logs)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

    tabs = st.tabs(["Sueño", "Estrés", "HRV", "Tabla completa"])

    with tabs[0]:
        if "sleep_score" in df.columns:
            df_sleep = df[df["sleep_score"].notna()][["date", "sleep_score"]].tail(30)
            if not df_sleep.empty:
                fig = line_chart(df_sleep, "date", "sleep_score",
                                 "Score de Sueño — últimos 30 días", target_line=70, height=280)
                st.plotly_chart(fig, use_container_width=True)
                avg = df_sleep["sleep_score"].mean()
                st.caption(f"Promedio: {avg:.1f}/100")

    with tabs[1]:
        if "stress_level" in df.columns:
            df_stress = df[df["stress_level"].notna()][["date", "stress_level"]].tail(30)
            if not df_stress.empty:
                fig = line_chart(df_stress, "date", "stress_level",
                                 "Nivel de Estrés — últimos 30 días", target_line=5, height=280)
                st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        if "hrv" in df.columns:
            df_hrv = df[df["hrv"].notna()][["date", "hrv"]].tail(30)
            if not df_hrv.empty:
                fig = line_chart(df_hrv, "date", "hrv",
                                 "HRV — últimos 30 días", target_line=40, height=280)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Umbral bajo: < 40 ms → modo baja energía")

    with tabs[3]:
        st.dataframe(
            df.tail(14)[[c for c in ["date", "sleep_score", "stress_level", "hrv", "steps"]
                         if c in df.columns]],
            use_container_width=True,
        )

else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">🫀</div>
        <div class="empty-state-title">Sin registros de salud</div>
        <div class="empty-state-text">
            Registrá tus biomarcadores con /salud en Telegram.<br>
            Ejemplo: /salud sueno:7.5 estres:bajo
        </div>
    </div>
    """, unsafe_allow_html=True)
