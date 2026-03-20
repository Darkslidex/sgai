"""
Le Menu du Chef — Planificación Semanal
Plan activo, distribución diaria, lista de compras, historial.
"""

import streamlit as st
import pandas as pd

from dashboard.auth import require_auth, touch_session
from dashboard.components.styles import inject_css
from dashboard.components.api_client import get_client
from dashboard.components.charts import bar_chart
from dashboard.config import get_dashboard_settings

st.set_page_config(page_title="Planificación · SGAI", page_icon="⚜", layout="wide")
inject_css()
require_auth()
touch_session()

cfg = get_dashboard_settings()

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Cinzel',serif;font-size:0.58rem;color:rgba(201,168,76,0.6);
    text-transform:uppercase;letter-spacing:0.28em;margin-bottom:0.5rem;">Le Menu du Chef</div>
""", unsafe_allow_html=True)
st.markdown("# Planificación Semanal")
st.markdown('<p class="page-subtitle">El menú de la semana — Batch Cooking 1×5</p>',
            unsafe_allow_html=True)
st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────

with get_client() as client:
    alive      = client.is_api_reachable()
    plan       = client.get_active_plan(cfg.sgai_user_id) if alive else None
    plan_hist  = client.get_plan_history(cfg.sgai_user_id) if alive else []

if not alive:
    st.warning("API no disponible.")
    st.stop()

# ── Plan activo ───────────────────────────────────────────────────────────────

if plan:
    week_start = plan.get("week_start", "—")
    total_cost = plan.get("total_cost_ars", 0)
    plan_json  = plan.get("plan_json", {})
    shopping   = plan.get("shopping_list_json", {}).get("items", [])
    cooking_day= plan_json.get("cooking_day", "—")

    # KPIs del plan
    k1, k2, k3 = st.columns(3)
    k1.metric("Semana del", week_start)
    k2.metric("Costo Estimado", f"$ {total_cost:,.0f}")
    k3.metric("Día de Cocción", cooking_day)

    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

    # ── Distribución diaria ──
    col_plan, col_shop = st.columns([1.2, 1])

    with col_plan:
        st.markdown("## Menú de la Semana")
        days = plan_json.get("days", [])
        if days:
            for day in days:
                st.markdown(f"""
                <div style="
                    padding: 0.9rem 1.2rem;
                    border: 1px solid rgba(201,168,76,0.12);
                    border-radius: 3px;
                    margin-bottom: 0.5rem;
                    background: rgba(20,20,20,0.5);
                ">
                    <div style="
                        font-family:'Cinzel',serif;font-size:0.6rem;color:#C9A84C;
                        text-transform:uppercase;letter-spacing:0.18em;margin-bottom:0.5rem;
                    ">{day.get('day','?')}</div>
                    <div style="
                        display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;
                    ">
                        <div>
                            <span style="font-size:0.65rem;color:#4A3F2F;">☀ Almuerzo</span><br>
                            <span style="font-size:0.85rem;color:#F2E8D5;">
                                {day.get('lunch','—')}
                            </span>
                        </div>
                        <div>
                            <span style="font-size:0.65rem;color:#4A3F2F;">🌙 Cena</span><br>
                            <span style="font-size:0.85rem;color:#F2E8D5;">
                                {day.get('dinner','—')}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Sin detalle de días en el plan.")

    with col_shop:
        st.markdown("## Lista de Compras")
        if shopping:
            total = sum(i.get("estimated_price_ars", 0) for i in shopping)
            for item in shopping:
                price = item.get("estimated_price_ars", 0)
                st.markdown(f"""
                <div style="
                    display:flex; justify-content:space-between; align-items:center;
                    padding: 0.5rem 0.8rem;
                    border-bottom: 1px solid rgba(201,168,76,0.06);
                ">
                    <div>
                        <span style="font-size:0.85rem;color:#A89B7A;">
                            {item.get('ingredient_name','?').capitalize()}
                        </span>
                        <span style="font-size:0.72rem;color:#4A3F2F;margin-left:0.5rem;">
                            {item.get('quantity','?')} {item.get('unit','?')}
                        </span>
                    </div>
                    <span style="font-size:0.82rem;color:#C9A84C;">
                        $ {price:,.0f}
                    </span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="
                display:flex;justify-content:space-between;padding:0.75rem 0.8rem;
                border-top:1px solid rgba(201,168,76,0.25);margin-top:0.25rem;
            ">
                <span style="font-family:'Cinzel',serif;font-size:0.65rem;color:#6B5F47;
                    text-transform:uppercase;letter-spacing:0.15em;">Total</span>
                <span style="font-family:'Playfair Display',serif;font-size:1.1rem;color:#C9A84C;">
                    $ {total:,.0f}
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("Sin lista de compras generada.")

    # ── Pasos de preparación ──
    prep_steps = plan_json.get("prep_steps", [])
    if prep_steps:
        st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
        st.markdown("## Guía de Preparación")
        with st.expander("Ver pasos del batch cooking"):
            for i, step in enumerate(prep_steps, 1):
                st.markdown(f"""
                <div style="display:flex;gap:1rem;padding:0.6rem 0;
                    border-bottom:1px solid rgba(201,168,76,0.06);">
                    <span style="
                        font-family:'Cinzel',serif;font-size:0.7rem;color:#C9A84C;
                        min-width:1.5rem;text-align:center;
                    ">{i:02d}</span>
                    <span style="font-size:0.85rem;color:#A89B7A;">{step}</span>
                </div>
                """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <div class="empty-state-title">Sin plan activo</div>
        <div class="empty-state-text">
            Generá tu plan semanal con /plan en Telegram.<br>
            El Chef Ejecutivo (IA) diseñará tu menú Batch Cooking 1×5.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Historial de planes ───────────────────────────────────────────────────────

if plan_hist:
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
    st.markdown("## Historial de Planes")

    df_h = pd.DataFrame(plan_hist)
    if "week_start" in df_h.columns and "total_cost_ars" in df_h.columns:
        df_h["week_start"] = pd.to_datetime(df_h["week_start"])
        df_h = df_h.sort_values("week_start", ascending=False)

        fig = bar_chart(
            df_h.sort_values("week_start").tail(8),
            x="week_start", y="total_cost_ars",
            title="Costo por semana (ARS)", height=240,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df_h[["week_start", "total_cost_ars", "is_active"]].head(10),
            use_container_width=True,
        )
