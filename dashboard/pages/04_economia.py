"""
La Cave — Economía y Precios
Precios actuales, tendencias, anomalías, costos históricos.
"""

import streamlit as st
import pandas as pd

from dashboard.auth import require_auth, touch_session
from dashboard.components.styles import inject_css
from dashboard.components.api_client import get_client
from dashboard.components.charts import bar_chart, line_chart
from dashboard.config import get_dashboard_settings

st.set_page_config(page_title="Economía · SGAI", page_icon="⚜", layout="wide")
inject_css()
require_auth()
touch_session()

cfg = get_dashboard_settings()

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Cinzel',serif;font-size:0.58rem;color:rgba(201,168,76,0.6);
    text-transform:uppercase;letter-spacing:0.28em;margin-bottom:0.5rem;">La Cave</div>
""", unsafe_allow_html=True)
st.markdown("# Economía y Precios")
st.markdown('<p class="page-subtitle">La inteligencia de mercado — inflación, fuentes y tendencias</p>',
            unsafe_allow_html=True)
st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────

with get_client() as client:
    alive       = client.is_api_reachable()
    prices      = client.get_current_prices() if alive else []
    ingredients = client.get_ingredients() if alive else []
    plan_hist   = client.get_plan_history(cfg.sgai_user_id) if alive else []

if not alive:
    st.warning("API no disponible.")
    st.stop()

# ── KPIs ─────────────────────────────────────────────────────────────────────

_source_map = {"manual": "✋ Manual", "sepa": "🏛 SEPA", "scraping": "🌐 Scraping", "seed": "📦 Seed"}
_conf_colors = {"manual": "green", "sepa": "blue", "scraping": "gray", "seed": "gray"}

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ingredientes con Precio", str(len(prices)))
manual_count = sum(1 for p in prices if p.get("source") == "manual")
k2.metric("Precios Manuales", str(manual_count))
sepa_count = sum(1 for p in prices if p.get("source") == "sepa")
k3.metric("Precios SEPA", str(sepa_count))
avg_conf = sum(p.get("confidence", 0) for p in prices) / max(len(prices), 1)
k4.metric("Confianza Promedio", f"{avg_conf:.0%}")

st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Tabla de precios ──────────────────────────────────────────────────────────

st.markdown("## Precios Actuales")

if prices:
    # Enriquecer con nombres de ingredientes
    ing_map = {i["id"]: i["name"] for i in ingredients if "id" in i and "name" in i}

    # Filtros
    col_f1, col_f2 = st.columns([1, 3])
    with col_f1:
        source_filter = st.selectbox(
            "Filtrar por fuente",
            ["Todas", "Manual", "SEPA", "Scraping", "Seed"],
            label_visibility="collapsed",
        )

    rows = []
    for p in prices:
        source = p.get("source", "—")
        if source_filter != "Todas" and source.lower() != source_filter.lower():
            continue

        ing_id = p.get("ingredient_id", "?")
        name = ing_map.get(ing_id, f"Ing. #{ing_id}")
        conf = p.get("confidence", 0)
        rows.append({
            "Ingrediente": name.capitalize(),
            "Precio (ARS)": f"$ {p.get('price_ars', 0):,.0f}",
            "Fuente": _source_map.get(source, source),
            "Confianza": f"{conf:.0%}",
            "Fecha": p.get("date", "—"),
            "Tienda": p.get("store", "—"),
        })

    if rows:
        df_p = pd.DataFrame(rows)
        st.dataframe(df_p, use_container_width=True, height=300)
    else:
        st.caption("Sin precios para el filtro seleccionado.")

    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

    # ── Top 10 más caros ──
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("## Los Más Caros")
        sorted_prices = sorted(prices, key=lambda x: x.get("price_ars", 0), reverse=True)[:10]
        df_top = pd.DataFrame([{
            "ing": ing_map.get(p["ingredient_id"], f"#{p['ingredient_id']}").capitalize(),
            "ars": p.get("price_ars", 0),
        } for p in sorted_prices])
        if not df_top.empty:
            fig = bar_chart(df_top, x="ing", y="ars",
                            title="Top 10 ingredientes por precio (ARS)",
                            horizontal=True, height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown("## Por Fuente")
        source_counts = {}
        for p in prices:
            s = p.get("source", "otro")
            source_counts[s] = source_counts.get(s, 0) + 1

        if source_counts:
            df_src = pd.DataFrame([
                {"fuente": _source_map.get(k, k), "cantidad": v}
                for k, v in source_counts.items()
            ])
            fig2 = bar_chart(df_src, x="fuente", y="cantidad",
                             title="Cantidad de precios por fuente", height=300)
            st.plotly_chart(fig2, use_container_width=True)

else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">💹</div>
        <div class="empty-state-title">Sin precios registrados</div>
        <div class="empty-state-text">
            Registrá precios con /precio en Telegram o corriendo el seed de precios.<br>
            Ejemplo: /precio tomate 1500
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Costos semanales históricos ───────────────────────────────────────────────

if plan_hist:
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
    st.markdown("## Evolución del Costo Semanal")
    df_ph = pd.DataFrame(plan_hist)
    if "week_start" in df_ph.columns and "total_cost_ars" in df_ph.columns:
        df_ph["week_start"] = pd.to_datetime(df_ph["week_start"])
        df_ph = df_ph.sort_values("week_start")
        fig3 = line_chart(df_ph, x="week_start", y="total_cost_ars",
                          title="Costo total del plan por semana (ARS)", height=260)
        st.plotly_chart(fig3, use_container_width=True)
