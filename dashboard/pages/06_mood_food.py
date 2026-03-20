"""
L'Harmonie — Mood & Food
Correlación entre estado de ánimo, sueño, estrés y adherencia al plan.
Requiere mínimo 4 semanas de datos.
"""

import streamlit as st
import pandas as pd
import numpy as np

from dashboard.auth import require_auth, touch_session
from dashboard.components.styles import inject_css
from dashboard.components.api_client import get_client
from dashboard.components.charts import scatter_chart, heatmap, line_chart
from dashboard.config import get_dashboard_settings

st.set_page_config(page_title="Mood & Food · SGAI", page_icon="⚜", layout="wide")
inject_css()
require_auth()
touch_session()

cfg = get_dashboard_settings()

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Cinzel',serif;font-size:0.58rem;color:rgba(201,168,76,0.6);
    text-transform:uppercase;letter-spacing:0.28em;margin-bottom:0.5rem;">L'Harmonie</div>
""", unsafe_allow_html=True)
st.markdown("# Mood & Food")
st.markdown('<p class="page-subtitle">La armonía entre el bienestar y la alimentación</p>',
            unsafe_allow_html=True)
st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────

with get_client() as client:
    alive      = client.is_api_reachable()
    health_logs= client.get_health_logs(cfg.sgai_user_id, days=90) if alive else []
    plan_hist  = client.get_plan_history(cfg.sgai_user_id) if alive else []

if not alive:
    st.warning("API no disponible.")
    st.stop()

# ── Verificar suficiencia de datos ────────────────────────────────────────────

MIN_WEEKS = 4

has_enough_data = len(health_logs) >= (MIN_WEEKS * 4) and len(plan_hist) >= MIN_WEEKS

if not has_enough_data:
    weeks_health = len(health_logs) // 4
    weeks_plan   = len(plan_hist)
    weeks_needed = MIN_WEEKS
    progress_val = min(max(weeks_health, weeks_plan) / weeks_needed, 1.0)

    st.markdown(f"""
    <div style="
        max-width:600px; margin:3rem auto; text-align:center;
        padding:3rem 2rem;
        background:rgba(20,20,20,0.5);
        border:1px solid rgba(201,168,76,0.15);
        border-radius:3px;
    ">
        <div style="font-size:2.5rem; margin-bottom:1.5rem; opacity:0.5;">🎭</div>
        <div style="
            font-family:'Cinzel',serif; font-size:0.65rem; color:#C9A84C;
            text-transform:uppercase; letter-spacing:0.22em; margin-bottom:0.75rem;
        ">Cultivando los datos</div>
        <div style="
            font-family:'Playfair Display',serif; font-size:1.2rem; color:#A89B7A;
            margin-bottom:0.5rem;
        ">La armonía se revela con el tiempo</div>
        <div style="
            font-size:0.82rem; color:#4A3F2F; margin-bottom:2rem; line-height:1.7;
        ">
            Se necesitan mínimo <b style="color:#C9A84C;">{weeks_needed} semanas</b> de datos
            para calcular correlaciones significativas.<br>
            Registros de salud disponibles: {weeks_health} sem. |
            Planes completados: {weeks_plan}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.progress(progress_val)
    st.caption(f"Progreso: {progress_val:.0%} — seguí registrando métricas con /salud en Telegram")
    st.stop()

# ── Preparar datos ────────────────────────────────────────────────────────────

df_h = pd.DataFrame(health_logs)
df_h["date"] = pd.to_datetime(df_h["date"])
df_h = df_h.sort_values("date")

# Agrupar por semana
df_h["week"] = df_h["date"].dt.to_period("W").dt.start_time
weekly = df_h.groupby("week").agg({
    col: "mean" for col in ["sleep_score", "stress_level", "hrv"]
    if col in df_h.columns
}).reset_index()

# Merge con historial de planes
df_p = pd.DataFrame(plan_hist)
if "week_start" in df_p.columns:
    df_p["week"] = pd.to_datetime(df_p["week_start"])
    weekly = weekly.merge(
        df_p[["week", "total_cost_ars"]].rename(columns={"total_cost_ars": "costo"}),
        on="week", how="left",
    )

# ── KPIs correlación ──────────────────────────────────────────────────────────

if "sleep_score" in weekly.columns and "stress_level" in weekly.columns:
    clean = weekly.dropna(subset=["sleep_score", "stress_level"])
    if len(clean) >= 3:
        corr_sleep_stress = clean["sleep_score"].corr(clean["stress_level"])
        k1, k2, k3 = st.columns(3)
        k1.metric("Sueño promedio", f"{weekly['sleep_score'].mean():.0f}/100")
        k2.metric("Estrés promedio", f"{weekly['stress_level'].mean():.1f}/10")
        corr_dir = "↑ correlación positiva" if corr_sleep_stress > 0.3 else (
                   "↓ correlación negativa" if corr_sleep_stress < -0.3 else "→ sin correlación fuerte")
        k3.metric("Sueño vs. Estrés", f"{corr_sleep_stress:.2f}", corr_dir)

    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Scatter: Sueño vs Estrés ─────────────────────────────────────────────────

col_l, col_r = st.columns(2)

with col_l:
    st.markdown("## Sueño vs. Estrés")
    if "sleep_score" in weekly.columns and "stress_level" in weekly.columns:
        df_scatter = weekly.dropna(subset=["sleep_score", "stress_level"])
        if not df_scatter.empty:
            fig = scatter_chart(
                df_scatter, x="sleep_score", y="stress_level",
                title="Correlación: calidad de sueño vs. nivel de estrés",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Cada punto = una semana. Mayor sueño debería correlacionar con menor estrés.")

with col_r:
    st.markdown("## Evolución Semanal")
    plot_cols = [c for c in ["sleep_score", "stress_level"] if c in weekly.columns]
    if plot_cols and not weekly.empty:
        fig2 = line_chart(
            weekly.dropna(subset=plot_cols[:1]),
            x="week", y=plot_cols,
            title="Tendencia semanal de biomarcadores",
            height=300,
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── Heatmap correlaciones ─────────────────────────────────────────────────────

st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
st.markdown("## Matriz de Correlación")

corr_cols = [c for c in ["sleep_score", "stress_level", "hrv", "costo"]
             if c in weekly.columns and weekly[c].notna().sum() >= 3]

if len(corr_cols) >= 2:
    corr_matrix = weekly[corr_cols].corr()
    fig3 = heatmap(corr_matrix, title="Correlaciones entre variables clave", height=320)
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Valores cercanos a 1 = correlación positiva fuerte | -1 = inversa | 0 = sin relación")
else:
    st.info("Se necesitan más semanas de datos para calcular la matriz de correlación.")

# ── Tabla resumen semanal ─────────────────────────────────────────────────────

st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
st.markdown("## Historial Semanal Detallado")

display_cols = [c for c in ["week", "sleep_score", "stress_level", "hrv", "costo"]
                if c in weekly.columns]
st.dataframe(
    weekly[display_cols].sort_values("week", ascending=False).head(12),
    use_container_width=True,
)
