"""Módulo de autenticación centralizada para la suite KUBOC.

Expone:
- hash_pin(pin) → str
- login(username, pin, ip=None, user_agent=None) → dict user | None
- create_session(usuario_id, sistema) → token str
- validate_session(token) → dict session | None
- logout(token)
- logout_all(usuario_id) → int (sesiones cerradas)
- signed_token(payload) / verify_signed(token)   (para compatibilidad con itsdangerous)
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from kuboc_core import config
from kuboc_core.db import get_conn

logger = logging.getLogger(__name__)

_serializer: Optional[URLSafeTimedSerializer] = None


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        config.validar()
        _serializer = URLSafeTimedSerializer(config.KUBOC_CORE_SECRET, salt='kuboc-core-v1')
    return _serializer


def hash_pin(pin: str) -> str:
    """SHA-256 de un PIN. Mismo algoritmo que todos los sistemas actuales."""
    return hashlib.sha256((pin or '').encode('utf-8')).hexdigest()


def _row_to_user(row: dict) -> dict:
    """Serializa una fila de usuarios_global al formato estándar."""
    return {
        'id': row['id'],
        'username': row['username'],
        'nombre_completo': row.get('nombre_completo'),
        'email': row.get('email'),
        'telegram_id': row.get('telegram_id'),
        'rol_global': row.get('rol_global', 'usuario'),
        'activo': bool(row.get('activo', True)),
    }


def login(username: str, pin: str, ip: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[dict]:
    """Valida credenciales. Retorna dict del usuario o None.

    Maneja bloqueo tras config.PIN_INTENTOS_MAX fallos consecutivos.
    """
    if not username or not pin:
        return None
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios_global WHERE lower(username) = lower(%s)",
            (username.strip(),)
        ).fetchone()
        if not row:
            return None
        if not row.get('activo'):
            return None
        if row.get('bloqueado_hasta') and row['bloqueado_hasta'] > now:
            return None

        if row['pin_hash'] != hash_pin(pin):
            # Incrementar intentos fallidos
            intentos = int(row.get('intentos_fallidos') or 0) + 1
            bloqueo = None
            if intentos >= config.PIN_INTENTOS_MAX:
                bloqueo = now + timedelta(minutes=config.PIN_BLOQUEO_MINUTOS)
                intentos = 0  # reset tras bloquear
            conn.execute(
                "UPDATE usuarios_global SET intentos_fallidos = %s, bloqueado_hasta = %s WHERE id = %s",
                (intentos, bloqueo, row['id'])
            )
            return None

        # Login OK
        conn.execute(
            "UPDATE usuarios_global SET intentos_fallidos = 0, bloqueado_hasta = NULL, ultimo_login = NOW() WHERE id = %s",
            (row['id'],)
        )
        conn.execute(
            "INSERT INTO audit_log (usuario_id, sistema, accion, ip) VALUES (%s, %s, %s, %s)",
            (row['id'], 'core', 'LOGIN_OK', ip)
        )
        return _row_to_user(row)


def create_session(usuario_id: int, sistema: str = 'hub', proyecto_activo_id: Optional[int] = None,
                   ip: Optional[str] = None, user_agent: Optional[str] = None) -> str:
    """Crea una sesión y devuelve el token (guardar en cookie kuboc_session).

    El token es aleatorio y se valida contra la tabla sessions. No codifica claims.
    Esto permite logout global (borrando la fila) con validación inmediata.
    """
    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(hours=config.SESSION_TTL_HOURS)
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sessions (token, usuario_id, proyecto_activo_id, sistema_origen, expira_en, ip, user_agent)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (token, usuario_id, proyecto_activo_id, sistema, expira, ip, (user_agent or '')[:200])
        )
    return token


def validate_session(token: Optional[str]) -> Optional[dict]:
    """Valida un token de sesión. Retorna dict con datos de sesión + usuario o None.

    Renueva automáticamente ultima_actividad (throttle de 60s para no escribir en cada request).
    """
    if not token:
        return None
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        row = conn.execute(
            """SELECT s.*, u.username, u.nombre_completo, u.rol_global, u.activo as user_activo
               FROM sessions s
               INNER JOIN usuarios_global u ON u.id = s.usuario_id
               WHERE s.token = %s""",
            (token,)
        ).fetchone()
        if not row:
            return None
        if row['expira_en'] <= now:
            return None
        if not row.get('user_activo'):
            return None

        # Throttle de ultima_actividad (60s)
        ultima = row.get('ultima_actividad')
        if not ultima or (now - ultima).total_seconds() > 60:
            conn.execute("UPDATE sessions SET ultima_actividad = NOW() WHERE token = %s", (token,))

        return {
            'token': token,
            'usuario_id': row['usuario_id'],
            'username': row['username'],
            'nombre_completo': row.get('nombre_completo'),
            'rol_global': row.get('rol_global'),
            'proyecto_activo_id': row.get('proyecto_activo_id'),
            'sistema_origen': row.get('sistema_origen'),
            'expira_en': row['expira_en'],
        }


def switch_proyecto(token: str, proyecto_id: int) -> bool:
    """Cambia el proyecto activo de una sesión existente."""
    with get_conn() as conn:
        r = conn.execute(
            "UPDATE sessions SET proyecto_activo_id = %s WHERE token = %s",
            (proyecto_id, token)
        )
        return r.rowcount > 0


def logout(token: str) -> bool:
    """Cierra una sesión específica."""
    with get_conn() as conn:
        r = conn.execute("DELETE FROM sessions WHERE token = %s", (token,))
        return r.rowcount > 0


def logout_all(usuario_id: int) -> int:
    """Cierra todas las sesiones de un usuario. Útil tras cambio de PIN."""
    with get_conn() as conn:
        r = conn.execute("DELETE FROM sessions WHERE usuario_id = %s", (usuario_id,))
        return r.rowcount


def purge_expired_sessions() -> int:
    """Limpia sesiones expiradas. Llamar periódicamente (cron)."""
    with get_conn() as conn:
        r = conn.execute("DELETE FROM sessions WHERE expira_en <= NOW()")
        return r.rowcount


# ── Compatibilidad con firma itsdangerous (para cookies cross-domain sin BD) ──

def signed_token(payload: dict) -> str:
    """Firma un payload y devuelve un token. Útil para cookies stateless."""
    return _get_serializer().dumps(payload)


def verify_signed(token: str, max_age_seconds: Optional[int] = None) -> Optional[dict]:
    """Verifica y decodifica un token firmado. None si inválido/expirado."""
    if not token:
        return None
    try:
        max_age = max_age_seconds if max_age_seconds is not None else config.SESSION_TTL_HOURS * 3600
        return _get_serializer().loads(token, max_age=max_age)
    except SignatureExpired:
        return None
    except BadSignature:
        return None
