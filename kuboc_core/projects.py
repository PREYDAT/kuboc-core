"""Módulo de proyectos y permisos multi-tenant.

Expone:
- list_for_user(usuario_id) → list[dict]      proyectos del usuario
- get(proyecto_id) → dict | None              detalle de un proyecto
- get_cuentas(proyecto_id) → list[dict]       cuentas del proyecto (ej. DYDIMA/KUBOC)
- get_categorias(proyecto_id) → list[dict]    categorías válidas
- user_has_role(usuario_id, proyecto_id, rol_min='visor', sistema=None) → bool
- crear_proyecto(codigo, nombre, tipo_indole, plantilla=None, creado_por=None)
- asignar_usuario(usuario_id, proyecto_id, rol, sistemas=None, asignado_por=None)
"""
import logging
from typing import Optional

from kuboc_core.db import get_conn

logger = logging.getLogger(__name__)


# Jerarquía de roles — un rol "superior" incluye los permisos del inferior
ROL_JERARQUIA = {
    'admin': 4,
    'administrador': 4,         # alias
    'admin_proyecto': 4,        # alias
    'contador': 3,
    'supervisor': 3,
    'operador': 2,
    'visor': 1,
    'consulta': 1,              # alias
}


def list_for_user(usuario_id: int, solo_activos: bool = True) -> list[dict]:
    """Devuelve los proyectos a los que el usuario tiene acceso con su rol en cada uno."""
    sql = """
        SELECT p.*, upr.rol, upr.sistemas
        FROM usuario_proyecto_rol upr
        INNER JOIN proyectos p ON p.id = upr.proyecto_id
        WHERE upr.usuario_id = %s
    """
    if solo_activos:
        sql += " AND p.activo = TRUE"
    sql += " ORDER BY p.nombre"
    with get_conn() as conn:
        rows = conn.execute(sql, (usuario_id,)).fetchall()
    return rows


def get(proyecto_id: int) -> Optional[dict]:
    """Detalle de un proyecto (o None)."""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM proyectos WHERE id = %s", (proyecto_id,)).fetchone()


def get_by_codigo(codigo: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM proyectos WHERE codigo = %s", (codigo,)).fetchone()


def get_cuentas(proyecto_id: int, solo_activas: bool = True) -> list[dict]:
    """Cuentas del proyecto (ej. DYDIMA, KUBOC) con código, nombre, rol, color."""
    sql = "SELECT * FROM proyecto_cuentas WHERE proyecto_id = %s"
    if solo_activas:
        sql += " AND activo = TRUE"
    sql += " ORDER BY orden, codigo"
    with get_conn() as conn:
        return conn.execute(sql, (proyecto_id,)).fetchall()


def get_categorias(proyecto_id: int, solo_activas: bool = True) -> list[dict]:
    """Categorías válidas del proyecto."""
    sql = "SELECT * FROM proyecto_categorias WHERE proyecto_id = %s"
    if solo_activas:
        sql += " AND activo = TRUE"
    sql += " ORDER BY orden, nombre"
    with get_conn() as conn:
        return conn.execute(sql, (proyecto_id,)).fetchall()


def user_has_role(usuario_id: int, proyecto_id: int, rol_min: str = 'visor', sistema: Optional[str] = None) -> bool:
    """Verifica si el usuario tiene rol_min o superior en el proyecto.

    Si `sistema` se pasa, valida que la asignación incluya ese sistema (array `sistemas` NULL = todos).
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT rol, sistemas FROM usuario_proyecto_rol WHERE usuario_id = %s AND proyecto_id = %s",
            (usuario_id, proyecto_id)
        ).fetchone()
    if not row:
        return False
    rol_user = (row.get('rol') or '').lower()
    if ROL_JERARQUIA.get(rol_user, 0) < ROL_JERARQUIA.get(rol_min.lower(), 0):
        return False
    if sistema:
        sistemas = row.get('sistemas')
        if sistemas is not None and sistema not in sistemas:
            return False
    return True


def crear_proyecto(codigo: str, nombre: str, tipo_indole: str,
                   plantilla: Optional[str] = None,
                   moneda_base: str = 'PEN',
                   creado_por: Optional[int] = None,
                   **kwargs) -> int:
    """Crea un proyecto. Si `plantilla` se pasa, aplica las cuentas y categorías del template.

    `kwargs` acepta: color_principal, color_secundario, logo_url, fecha_inicio, fecha_fin, notas,
                    con_contabilidad_detallada, con_tributario_peru.
    """
    campos_extra = ['color_principal', 'color_secundario', 'logo_url', 'fecha_inicio',
                    'fecha_fin', 'notas', 'con_contabilidad_detallada', 'con_tributario_peru']
    extra_cols = [k for k in campos_extra if k in kwargs]
    extra_vals = [kwargs[k] for k in extra_cols]

    cols_sql = ', '.join(['codigo', 'nombre', 'tipo_indole', 'moneda_base', 'creado_por'] + extra_cols)
    placeholders = ', '.join(['%s'] * (5 + len(extra_cols)))
    values = (codigo, nombre, tipo_indole, moneda_base, creado_por, *extra_vals)

    with get_conn() as conn:
        row = conn.execute(
            f"INSERT INTO proyectos ({cols_sql}) VALUES ({placeholders}) RETURNING id",
            values
        ).fetchone()
        proyecto_id = row['id']

    if plantilla:
        from kuboc_core import templates
        templates.aplicar(proyecto_id, plantilla)

    logger.info(f"kuboc_core: proyecto creado id={proyecto_id} codigo={codigo}")
    return proyecto_id


def asignar_usuario(usuario_id: int, proyecto_id: int, rol: str,
                    sistemas: Optional[list[str]] = None,
                    asignado_por: Optional[int] = None) -> None:
    """Asigna/actualiza rol de un usuario en un proyecto."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO usuario_proyecto_rol (usuario_id, proyecto_id, rol, sistemas, asignado_por)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (usuario_id, proyecto_id)
               DO UPDATE SET rol = EXCLUDED.rol, sistemas = EXCLUDED.sistemas,
                             asignado_por = EXCLUDED.asignado_por, asignado_en = NOW()""",
            (usuario_id, proyecto_id, rol, sistemas, asignado_por)
        )
