"""Tests del sistema de autenticación del Dashboard SGAI."""

import time
from unittest.mock import patch, MagicMock

import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock de streamlit.session_state para tests unitarios."""
    session = {}

    mock_st = MagicMock()
    mock_st.session_state = session
    mock_st.stop = MagicMock(side_effect=SystemExit(0))

    with patch.dict("sys.modules", {"streamlit": mock_st}):
        yield mock_st, session


@pytest.fixture
def mock_settings():
    """Settings de test con contraseña conocida."""
    import bcrypt
    pw_hash = bcrypt.hashpw(b"chef1234", bcrypt.gensalt()).decode()

    settings = MagicMock()
    settings.dashboard_user = "chef"
    settings.dashboard_password_hash = pw_hash
    settings.max_login_attempts = 5
    settings.lockout_minutes = 5
    settings.session_timeout_minutes = 30
    return settings


# ── hash_password / verify_password ──────────────────────────────────────────

def test_hash_and_verify_password():
    """hash_password genera hash que verify_password valida correctamente."""
    from dashboard.auth import hash_password, verify_password
    hashed = hash_password("mi_contraseña_secreta")
    assert verify_password("mi_contraseña_secreta", hashed) is True
    assert verify_password("contraseña_incorrecta", hashed) is False


def test_verify_password_with_wrong_hash():
    """verify_password retorna False con hash malformado sin lanzar excepción."""
    from dashboard.auth import verify_password
    result = verify_password("cualquier_cosa", "hash_invalido")
    assert result is False


# ── attempt_login ─────────────────────────────────────────────────────────────

def test_login_correct_credentials(mock_streamlit, mock_settings):
    """Login con credenciales correctas retorna (True, mensaje)."""
    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth
        # Reload para que use el mock
        ok, msg = auth.attempt_login("chef", "chef1234")

    assert ok is True


def test_login_wrong_username(mock_streamlit, mock_settings):
    """Login con usuario incorrecto retorna (False, mensaje)."""
    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth
        ok, msg = auth.attempt_login("admin", "chef1234")

    assert ok is False
    assert "incorrectas" in msg.lower() or "bloqueado" in msg.lower()


def test_login_wrong_password(mock_streamlit, mock_settings):
    """Login con contraseña incorrecta retorna (False, mensaje)."""
    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth
        ok, msg = auth.attempt_login("chef", "contraseña_mala")

    assert ok is False


def test_login_increments_attempt_counter(mock_streamlit, mock_settings):
    """Intentos fallidos incrementan el contador en session_state."""
    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth
        auth.attempt_login("chef", "mala")
        auth.attempt_login("chef", "mala")

    assert session.get(auth._KEY_ATTEMPTS, 0) == 2


# ── Lockout ───────────────────────────────────────────────────────────────────

def test_lockout_after_max_attempts(mock_streamlit, mock_settings):
    """5 intentos fallidos consecutivos activan el bloqueo de 5 minutos."""
    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth

        for _ in range(mock_settings.max_login_attempts):
            ok, msg = auth.attempt_login("chef", "mal_password")

        # El último debería indicar bloqueo
        assert ok is False
        assert "bloqueado" in msg.lower()


def test_locked_out_blocks_login(mock_streamlit, mock_settings):
    """Después del bloqueo, intentos adicionales son rechazados inmediatamente."""
    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth

        # Activar bloqueo
        session[auth._KEY_LOCKED_AT] = time.time()
        session[auth._KEY_ATTEMPTS] = mock_settings.max_login_attempts

        ok, msg = auth.attempt_login("chef", "chef1234")  # contraseña correcta pero bloqueado

    assert ok is False
    assert "bloqueado" in msg.lower()


def test_lockout_expires_after_cooldown(mock_streamlit, mock_settings):
    """El bloqueo expira después del cooldown — permite nuevos intentos."""
    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth

        # Bloqueo con timestamp vencido (hace 6 minutos)
        session[auth._KEY_LOCKED_AT] = time.time() - (6 * 60)

        locked, remaining = auth.is_locked_out()

    assert locked is False
    assert remaining == 0


# ── Session expiry ────────────────────────────────────────────────────────────

def test_session_expires_after_30_minutes(mock_streamlit, mock_settings):
    """Sesión inactiva por más de 30 minutos → is_authenticated retorna False."""
    from datetime import datetime, timedelta

    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth

        session[auth._KEY_AUTH] = True
        session[auth._KEY_LAST_ACT] = datetime.now() - timedelta(minutes=31)

        result = auth.is_authenticated()

    assert result is False


def test_active_session_is_authenticated(mock_streamlit, mock_settings):
    """Sesión activa reciente → is_authenticated retorna True."""
    from datetime import datetime

    mock_st, session = mock_streamlit

    with patch("dashboard.auth.get_dashboard_settings", return_value=mock_settings):
        from dashboard import auth

        session[auth._KEY_AUTH] = True
        session[auth._KEY_LAST_ACT] = datetime.now()

        result = auth.is_authenticated()

    assert result is True
