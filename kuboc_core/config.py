"""Configuración centralizada del kuboc-core.

Lee de variables de entorno. Usa dotenv si hay .env en CWD.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Cargar .env del cwd primero, luego del home del paquete
    for p in (Path.cwd() / '.env', Path(__file__).parent.parent / '.env'):
        if p.exists():
            load_dotenv(p, override=False)
            break
except ImportError:
    pass


DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
"""URL de Postgres. Ej: postgresql://user:pass@host:port/dbname"""

KUBOC_CORE_SECRET = os.environ.get('KUBOC_CORE_SECRET', '').strip()
"""Secreto para firmar sesiones (itsdangerous). DEBE ser el mismo en todos los sistemas."""

SESSION_COOKIE_NAME = os.environ.get('KUBOC_COOKIE_NAME', 'kuboc_session')
"""Nombre de la cookie de sesión cross-sistema."""

SESSION_TTL_HOURS = int(os.environ.get('KUBOC_SESSION_TTL_HOURS', '12'))
"""Duración de sesión en horas."""

PIN_INTENTOS_MAX = 5
"""Intentos fallidos antes de bloqueo temporal."""

PIN_BLOQUEO_MINUTOS = 15
"""Minutos de bloqueo tras agotar intentos."""


def validar():
    """Valida que la config mínima esté presente. Raise ValueError si falta algo."""
    faltan = []
    if not DATABASE_URL:
        faltan.append('DATABASE_URL')
    if not KUBOC_CORE_SECRET:
        faltan.append('KUBOC_CORE_SECRET')
    if faltan:
        raise ValueError(
            f"kuboc-core: faltan variables de entorno: {', '.join(faltan)}. "
            f"Definilas en .env o en el deploy."
        )
