"""
Autenticación del Dashboard SGAI.

- bcrypt para hashing de contraseñas.
- Rate limiting: máximo 5 intentos por minuto.
- Bloqueo: 5 minutos después de 5 intentos fallidos.
- Sesión: expiración por 30 minutos de inactividad.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta

import bcrypt
import streamlit as st

from dashboard.config import get_dashboard_settings


# ── Helpers ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Genera un hash bcrypt de la contraseña. Usado para setup inicial."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica contraseña contra hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── Session State Keys ────────────────────────────────────────────────────────

_KEY_AUTH       = "authenticated"
_KEY_LAST_ACT   = "last_activity"
_KEY_ATTEMPTS   = "login_attempts"
_KEY_LOCKED_AT  = "locked_at"


# ── Core Auth Functions ───────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """True si hay sesión activa y no expirada."""
    if not st.session_state.get(_KEY_AUTH, False):
        return False
    last = st.session_state.get(_KEY_LAST_ACT)
    if last is None:
        return False
    cfg = get_dashboard_settings()
    if datetime.now() - last > timedelta(minutes=cfg.session_timeout_minutes):
        _logout()
        return False
    return True


def touch_session() -> None:
    """Actualiza el timestamp de última actividad."""
    st.session_state[_KEY_LAST_ACT] = datetime.now()


def _logout() -> None:
    """Limpia la sesión."""
    for key in [_KEY_AUTH, _KEY_LAST_ACT]:
        st.session_state.pop(key, None)


def logout() -> None:
    """Cierra sesión manualmente."""
    _logout()
    st.rerun()


def is_locked_out() -> tuple[bool, int]:
    """Retorna (está_bloqueado, segundos_restantes)."""
    locked_at = st.session_state.get(_KEY_LOCKED_AT)
    if locked_at is None:
        return False, 0
    cfg = get_dashboard_settings()
    elapsed = time.time() - locked_at
    lockout_secs = cfg.lockout_minutes * 60
    if elapsed < lockout_secs:
        return True, int(lockout_secs - elapsed)
    # Lockout expirado: resetear
    st.session_state.pop(_KEY_LOCKED_AT, None)
    st.session_state[_KEY_ATTEMPTS] = 0
    return False, 0


def attempt_login(username: str, password: str) -> tuple[bool, str]:
    """
    Intenta hacer login.

    Returns:
        (success, message)
    """
    cfg = get_dashboard_settings()

    # ── Verificar lockout ──
    locked, remaining = is_locked_out()
    if locked:
        return False, f"Acceso bloqueado. Reintentar en {remaining // 60}:{remaining % 60:02d}."

    # ── Verificar usuario ──
    if username != cfg.dashboard_user:
        return False, "Credenciales incorrectas."

    # ── Verificar contraseña ──
    if not cfg.dashboard_password_hash:
        # Modo desarrollo: acepta cualquier contraseña si no hay hash configurado
        ok = True
    else:
        ok = verify_password(password, cfg.dashboard_password_hash)

    if ok:
        st.session_state[_KEY_AUTH] = True
        st.session_state[_KEY_LAST_ACT] = datetime.now()
        st.session_state[_KEY_ATTEMPTS] = 0
        st.session_state.pop(_KEY_LOCKED_AT, None)
        return True, "Bienvenido."

    # ── Fallo: incrementar contador ──
    attempts = st.session_state.get(_KEY_ATTEMPTS, 0) + 1
    st.session_state[_KEY_ATTEMPTS] = attempts

    if attempts >= cfg.max_login_attempts:
        st.session_state[_KEY_LOCKED_AT] = time.time()
        return False, f"Demasiados intentos. Bloqueado por {cfg.lockout_minutes} minutos."

    remaining_attempts = cfg.max_login_attempts - attempts
    return False, f"Credenciales incorrectas. Intentos restantes: {remaining_attempts}."


def require_auth() -> None:
    """
    Verifica autenticación. Si no está autenticado, detiene la ejecución
    de la página mostrando un mensaje elegante.
    """
    touch_session() if is_authenticated() else None

    if not is_authenticated():
        st.markdown("""
        <div style="
            text-align: center;
            padding: 4rem 2rem;
            color: #6B5F47;
        ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🔒</div>
            <div style="
                font-family: 'Cinzel', serif;
                font-size: 0.8rem;
                letter-spacing: 0.3em;
                text-transform: uppercase;
                color: #C9A84C;
                margin-bottom: 0.5rem;
            ">Acceso Restringido</div>
            <div style="font-family: 'Playfair Display', serif; font-size: 1.2rem; color: #A89B7A;">
                Iniciá sesión desde la página principal.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
