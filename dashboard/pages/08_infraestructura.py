"""
L'Infrastructure — Estado del Sistema
Monitoreo de tokens, errores, latencia y accesos de Ana.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from dashboard.auth import require_auth, touch_session
from dashboard.components.api_client import get_client
from dashboard.components.styles import inject_css
from dashboard.config import get_dashboard_settings

st.set_page_config(page_title="Infraestructura · SGAI", page_icon="🔧", layout="wide")
inject_css()
require_auth()
touch_session()

settings = get_dashboard_settings()
client = get_client()

st.title("🔧 L'Infrastructure")
st.caption("Estado del sistema, consumo de tokens y audit trail de Ana")

# ── Health Check ──────────────────────────────────────────────────────────────
st.subheader("Estado del Sistema")
try:
    health = client.get("/health").json()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_color = "🟢" if health.get("status") == "healthy" else "🟡"
        st.metric("SGAI API", f"{status_color} {health.get('status', 'unknown')}")
    with col2:
        uptime_h = round(health.get("uptime_seconds", 0) / 3600, 1)
        st.metric("Uptime", f"{uptime_h}h")
    with col3:
        ana = health.get("ana_connectivity", "unknown")
        ana_color = "🟢" if ana == "ok" else "🔴"
        st.metric("Ana Webhook", f"{ana_color} {ana}")
    with col4:
        tokens = health.get("tokens_today", 0)
        st.metric("Tokens Hoy", f"{tokens:,}", delta=None)
    
    db_status = health.get("database", {})
    if db_status.get("status") == "connected":
        st.success(f"✅ Base de datos conectada — {db_status.get('tables', '?')} tablas")
    else:
        st.error(f"❌ Base de datos: {db_status}")
except Exception as e:
    st.error(f"No se pudo obtener el estado del sistema: {e}")

st.divider()

# ── Consumo de Tokens ──────────────────────────────────────────────────────────
st.subheader("Consumo de Tokens LLM")
period = st.selectbox("Período", ["24h", "7d", "30d"], index=1)

try:
    usage = client.get(
        "/api/v1/admin/llm-usage",
        params={"period": period},
        headers={"X-Ana-Key": settings.__dict__.get("ana_api_key", "")}
    )
    if usage.status_code == 200:
        data = usage.json()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Requests", data.get("total_requests", 0))
        with col2:
            st.metric("Tokens Input", f"{data.get('total_tokens_input', 0):,}")
        with col3:
            st.metric("Tokens Output", f"{data.get('total_tokens_output', 0):,}")
        with col4:
            success_rate = data.get("success_rate", 1.0)
            color = "normal" if success_rate >= 0.95 else "inverse"
            st.metric("Success Rate", f"{success_rate:.1%}", delta=None)

        # Por modelo
        by_model = data.get("by_model", [])
        if by_model:
            df = pd.DataFrame(by_model)
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Circuit breakers
        cb = data.get("circuit_breaker_status", {})
        if cb:
            st.caption("Circuit Breakers")
            for model, status in cb.items():
                icon = "🔴" if "open" in status else "🟢"
                st.write(f"{icon} {model}: {status}")
    else:
        st.warning(f"Admin endpoint respondió {usage.status_code} — verificá ANA_API_KEY")
except Exception as e:
    st.warning(f"No se pudo obtener uso LLM: {e}")

st.divider()

# ── Últimos Accesos de Ana ──────────────────────────────────────────────────────
st.subheader("Últimos Accesos de Ana")
try:
    access = client.get(
        "/api/v1/admin/ana-access-log",
        params={"limit": 10},
        headers={"X-Ana-Key": settings.__dict__.get("ana_api_key", "")}
    )
    if access.status_code == 200:
        logs = access.json()
        if logs:
            df = pd.DataFrame(logs)
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%d/%m %H:%M")
            df = df[["timestamp", "method", "endpoint", "response_code", "response_time_ms"]]
            df.columns = ["Timestamp", "Método", "Endpoint", "Código", "Tiempo (ms)"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Sin accesos registrados aún")
    else:
        st.warning(f"Access log respondió {access.status_code}")
except Exception as e:
    st.warning(f"No se pudo obtener access log: {e}")

st.divider()

# ── Info del sistema ──────────────────────────────────────────────────────────
st.caption(f"Versión SGAI: {health.get('version', '?')} | Entorno: {health.get('environment', '?')} | Última actualización: {datetime.now().strftime('%H:%M:%S')}")
