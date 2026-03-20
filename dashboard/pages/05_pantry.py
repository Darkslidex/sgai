"""
L'Office — Inventario (Pantry)
Estado de la alacena, vencimientos, categorías.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from dashboard.auth import require_auth, touch_session
from dashboard.components.styles import inject_css
from dashboard.components.api_client import get_client
from dashboard.components.charts import donut_chart, bar_chart
from dashboard.config import get_dashboard_settings

st.set_page_config(page_title="Pantry · SGAI", page_icon="⚜", layout="wide")
inject_css()
require_auth()
touch_session()

cfg = get_dashboard_settings()

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style="font-family:'Cinzel',serif;font-size:0.58rem;color:rgba(201,168,76,0.6);
    text-transform:uppercase;letter-spacing:0.28em;margin-bottom:0.5rem;">L'Office</div>
""", unsafe_allow_html=True)
st.markdown("# Inventario · Pantry")
st.markdown('<p class="page-subtitle">La mise en place — lo que está en la despensa</p>',
            unsafe_allow_html=True)
st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────

with get_client() as client:
    alive       = client.is_api_reachable()
    pantry      = client.get_pantry(cfg.sgai_user_id) if alive else []
    ingredients = client.get_ingredients() if alive else []

if not alive:
    st.warning("API no disponible.")
    st.stop()

ing_map = {i["id"]: i for i in ingredients if "id" in i}

# ── KPIs ─────────────────────────────────────────────────────────────────────

now = datetime.utcnow()

expiring_soon = []
expired = []
for item in pantry:
    exp = item.get("expires_at")
    if exp:
        try:
            exp_dt = datetime.fromisoformat(exp.replace("Z", ""))
            days_left = (exp_dt - now).days
            if days_left < 0:
                expired.append(item)
            elif days_left <= 3:
                expiring_soon.append(item)
        except Exception:
            pass

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Items", str(len(pantry)))
k2.metric("Con Fecha de Vencimiento", str(len([p for p in pantry if p.get("expires_at")])))
k3.metric("Próximos a Vencer (3d)", str(len(expiring_soon)))
k4.metric("Vencidos", str(len(expired)))

st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

if not pantry:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">🏪</div>
        <div class="empty-state-title">Alacena vacía</div>
        <div class="empty-state-text">
            Agregá ingredientes con /agregar_pantry en Telegram.<br>
            Ejemplo: /agregar_pantry arroz 2 kg
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Alertas ───────────────────────────────────────────────────────────────────

if expired:
    st.markdown(f"""
    <div class="alert-box alert-danger">
        🚨&nbsp;&nbsp;<span><b>{len(expired)} item(s) vencidos</b> — considerá descartarlos.</span>
    </div>
    """, unsafe_allow_html=True)

if expiring_soon:
    names = ", ".join([
        ing_map.get(item.get("ingredient_id"), {}).get("name", f"#{item.get('ingredient_id')}")
        for item in expiring_soon[:3]
    ])
    st.markdown(f"""
    <div class="alert-box alert-warning">
        ⚠️&nbsp;&nbsp;<span><b>{len(expiring_soon)} item(s)</b> próximos a vencer en 3 días: {names}</span>
    </div>
    """, unsafe_allow_html=True)

# ── Tabla de inventario ───────────────────────────────────────────────────────

col_table, col_charts = st.columns([1.6, 1])

with col_table:
    st.markdown("## Inventario Actual")

    rows = []
    for item in pantry:
        ing_id = item.get("ingredient_id")
        ing = ing_map.get(ing_id, {})
        name = ing.get("name", f"#{ing_id}").capitalize()
        category = ing.get("category", "—")
        qty = item.get("quantity_amount", 0)
        unit = item.get("unit", "?")
        exp = item.get("expires_at", "")

        # Calcular días restantes
        days_str = "—"
        status = "ok"
        if exp:
            try:
                exp_dt = datetime.fromisoformat(exp.replace("Z", ""))
                days = (exp_dt - now).days
                if days < 0:
                    days_str = f"Vencido ({abs(days)}d)"
                    status = "expired"
                elif days <= 3:
                    days_str = f"{days}d ⚠"
                    status = "expiring"
                else:
                    days_str = f"{days}d"
            except Exception:
                days_str = exp[:10]

        rows.append({
            "Ingrediente": name,
            "Categoría": category,
            "Cantidad": f"{qty} {unit}",
            "Vencimiento": days_str,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=400)

with col_charts:
    st.markdown("## Por Categoría")

    categories = {}
    for item in pantry:
        ing = ing_map.get(item.get("ingredient_id"), {})
        cat = ing.get("category", "sin_categoría")
        categories[cat] = categories.get(cat, 0) + item.get("quantity_amount", 1)

    if categories:
        labels = list(categories.keys())
        values = list(categories.values())
        fig = donut_chart(labels, values, title="Distribución del pantry", height=280)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("## Por Almacenamiento")
    storage_types = {}
    for item in pantry:
        ing = ing_map.get(item.get("ingredient_id"), {})
        storage_type = ing.get("storage_type", "otro")
        storage_types[storage_type] = storage_types.get(storage_type, 0) + 1

    if storage_types:
        df_storage = pd.DataFrame([{"tipo": k, "count": v} for k, v in storage_types.items()])
        fig2 = bar_chart(df_storage, x="tipo", y="count", title="Por tipo de almacenamiento", height=220)
        st.plotly_chart(fig2, use_container_width=True)
