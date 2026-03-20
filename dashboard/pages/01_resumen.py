"""
La Grand Salle — Resumen General
KPIs, TDEE trend, costos semanales, vencimientos próximos.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from dashboard.auth import require_auth, touch_session
from dashboard.components.styles import inject_css
from dashboard.components.api_client import get_client
from dashboard.components.charts import line_chart, bar_chart
from dashboard.config import get_dashboard_settings

st.set_page_config(page_title="Resumen · SGAI", page_icon="⚜", layout="wide")
inject_css()
require_auth()
touch_session()

cfg = get_dashboard_settings()

# ── Header ──────────────────────────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Cinzel',serif;font-size:0.58rem;color:rgba(201,168,76,0.6);
    text-transform:uppercase;letter-spacing:0.28em;margin-bottom:0.5rem;">La Grand Salle</div>
""", unsafe_allow_html=True)
st.markdown("# Resumen General")
st.markdown('<p class="page-subtitle">El estado integral del sistema — una mirada de chef</p>',
            unsafe_allow_html=True)
st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────

with get_client() as client:
    alive       = client.is_api_reachable()
    profile     = client.get_profile(cfg.sgai_user_id) if alive else None
    tdee_data   = client.get_tdee(cfg.sgai_user_id) if alive else None
    energy_data = client.get_energy_state(cfg.sgai_user_id) if alive else None
    plan        = client.get_active_plan(cfg.sgai_user_id) if alive else None
    pantry      = client.get_pantry(cfg.sgai_user_id) if alive else []
    health_logs = client.get_health_logs(cfg.sgai_user_id, days=30) if alive else []
    plan_hist   = client.get_plan_history(cfg.sgai_user_id) if alive else []
    system_h    = client.get_system_health() if alive else None

if not alive:
    st.warning("API no disponible — conectá el servidor SGAI.")
    st.stop()

# ── KPIs Row ─────────────────────────────────────────────────────────────────

k1, k2, k3, k4 = st.columns(4)

tdee_val = tdee_data.get("tdee", 0) if tdee_data else 0
k1.metric("TDEE Hoy", f"{tdee_val:,.0f} kcal")

plan_cost = plan.get("total_cost_ars", 0) if plan else 0
plan_week = plan.get("week_start", "—") if plan else "—"
k2.metric("Plan Activo", f"Sem. {plan_week}" if plan else "Sin plan",
          f"$ {plan_cost:,.0f}" if plan else None)

pantry_expiring = [p for p in pantry if p.get("expires_at")]
k3.metric("Alacena", f"{len(pantry)} items", f"{len(pantry_expiring)} con venc.")

_state = energy_data.get("state", "?") if energy_data else "?"
_state_map = {"NORMAL": "✓ Normal", "LOW": "⚠ Baja Energía", "CRITICAL": "🚨 Crítico"}
k4.metric("Estado Energético", _state_map.get(_state, _state))

st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Gráfico TDEE 30 días ──────────────────────────────────────────────────────

st.markdown("## Energía — últimos 30 días")

if health_logs:
    df_h = pd.DataFrame(health_logs)
    df_h = df_h[df_h.get("sleep_score") is not None] if "sleep_score" in df_h.columns else df_h
    if "date" in df_h.columns and len(df_h) > 0:
        df_h["date"] = pd.to_datetime(df_h["date"])
        df_h = df_h.sort_values("date")

        # Simular TDEE basado en sleep_score (proxy visual)
        base_tdee = tdee_val or 2000
        if "sleep_score" in df_h.columns:
            df_h["tdee_est"] = base_tdee * (0.9 + df_h["sleep_score"].fillna(70) / 1000)
        else:
            df_h["tdee_est"] = base_tdee

        fig = line_chart(df_h, x="date", y="tdee_est",
                         title="TDEE estimado (kcal/día)", target_line=base_tdee, height=280)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">📊</div>
        <div class="empty-state-title">Sin datos de salud registrados</div>
        <div class="empty-state-text">Usá /salud en Telegram para registrar métricas diarias.</div>
    </div>
    """, unsafe_allow_html=True)

# ── Costos semanales ─────────────────────────────────────────────────────────

col_l, col_r = st.columns([1.6, 1])

with col_l:
    st.markdown("## Costos — últimas semanas")
    if plan_hist:
        df_p = pd.DataFrame(plan_hist)
        if "week_start" in df_p.columns and "total_cost_ars" in df_p.columns:
            df_p["week_start"] = pd.to_datetime(df_p["week_start"])
            df_p = df_p.sort_values("week_start").tail(8)
            df_p["semana"] = df_p["week_start"].dt.strftime("Sem %d/%m")
            fig2 = bar_chart(df_p, x="semana", y="total_cost_ars",
                             title="Costo semanal (ARS)", height=260)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.caption("Sin datos suficientes de planes anteriores.")
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">💰</div>
            <div class="empty-state-title">Sin historial de planes</div>
            <div class="empty-state-text">Generá tu primer plan con /plan en Telegram.</div>
        </div>
        """, unsafe_allow_html=True)

with col_r:
    st.markdown("## Próximos a Vencer")

    expiring = [p for p in pantry if p.get("expires_at")]
    if expiring:
        soon = []
        threshold = (datetime.utcnow() + timedelta(days=4)).isoformat()
        for item in expiring:
            if item["expires_at"] <= threshold:
                soon.append(item)

        if soon:
            for item in soon[:6]:
                exp_str = item["expires_at"][:10] if item.get("expires_at") else "—"
                st.markdown(f"""
                <div style="
                    display:flex; justify-content:space-between; align-items:center;
                    padding:0.6rem 0.8rem;
                    border-left:2px solid rgba(201,168,76,0.3);
                    margin-bottom:0.4rem;
                    background:rgba(20,20,20,0.5);
                ">
                    <span style="font-size:0.82rem;color:#A89B7A;">
                        Ing. #{item.get('ingredient_id','?')}
                    </span>
                    <span style="font-size:0.78rem;color:#C47B7B;">{exp_str}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="color:#5A9E6F;font-size:0.85rem;padding:1rem;
                border:1px solid rgba(74,140,92,0.2);border-radius:3px;text-align:center;">
                ✓ Todo en orden
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Sin items con fecha de vencimiento registrada.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align:center;color:#3A3025;font-size:0.72rem;
    font-family:'Cinzel',serif;letter-spacing:0.15em;">
    {system_h.get('version','—') if system_h else '—'} &nbsp;·&nbsp;
    {system_h.get('status','—') if system_h else 'offline'}
</div>
""", unsafe_allow_html=True)
