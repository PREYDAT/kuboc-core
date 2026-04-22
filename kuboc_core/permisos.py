"""Sistema de permisos centralizado — KUBOC Suite.

Matriz 3D: Usuario × Proyecto × Sistema.

Fuentes de verdad:
- `usuarios_global.rol_global` — tipo de cuenta global (admin/usuario)
- `usuario_proyecto_rol.rol` — rol en un proyecto (admin/supervisor/contador/operador/visor)
- `usuario_proyecto_rol.sistemas` — lista de sistemas accesibles en ese proyecto;
  NULL = acceso a TODOS los sistemas del proyecto

ROLES y qué pueden hacer:
- admin        → todo, incluido crear usuarios, config sistema, borrar registros
- supervisor   → crear/editar/eliminar registros; NO crea usuarios ni toca config sistema
- contador     → crear/editar documentos contables, ver todo, exportar; NO elimina, NO crea usuarios
- operador     → crear/editar registros propios, exportar; NO elimina, NO edita ajenos
- visor        → solo ver y exportar; NO modifica nada
"""
from typing import Optional

from kuboc_core.db import get_conn


# ── Jerarquía de roles (rol superior incluye permisos del inferior) ──
NIVEL_ROL = {
    'visor':        1,
    'consulta':     1,   # alias
    'operador':     2,
    'contador':     3,
    'supervisor':   3,
    'admin':        4,
    'administrador': 4,  # alias
    'admin_proyecto': 4, # alias
}


# ── Matriz de acciones → rol mínimo requerido ──
# Las acciones NO listadas aquí se deniegan por default.
ACCIONES = {
    # Lectura
    'ver':                'visor',
    'exportar':           'visor',

    # Creación / edición propia
    'crear':              'operador',
    'editar_propio':      'operador',

    # Edición de ajenos y eliminación
    'editar_ajeno':       'supervisor',
    'eliminar':           'supervisor',
    'invalidar':          'supervisor',
    'anular':             'supervisor',

    # Docs contables (alias de edición para rol contador específico)
    'editar_factura':     'contador',
    'editar_asiento':     'contador',
    'conciliar':          'contador',

    # Administración — solo admin
    'crear_usuario':      'admin',
    'editar_usuario':     'admin',
    'eliminar_usuario':   'admin',
    'config_sistema':     'admin',
    'bootstrap':          'admin',
    'borrar_masivo':      'admin',
    'reset_datos':        'admin',
    'editar_catalogos':   'supervisor',  # artículos, categorías, proveedores maestros
    'eliminar_catalogo':  'admin',

    # Gestión de proyectos (solo admin global)
    'crear_proyecto':     'admin',
    'editar_proyecto':    'admin',
    'archivar_proyecto':  'admin',

    # Planilla (RRHH) — acciones críticas
    'cerrar_planilla':    'contador',
    'firmar_planilla':    'admin',
    'pagar_planilla':     'admin',
}


def nivel(rol: Optional[str]) -> int:
    """Devuelve el nivel numérico de un rol. Rol desconocido = 0."""
    if not rol:
        return 0
    return NIVEL_ROL.get(rol.lower().strip(), 0)


def rol_usuario_en_proyecto(usuario_id: int, proyecto_id: int) -> Optional[str]:
    """Consulta el rol del usuario en un proyecto específico. None si no tiene asignación."""
    if not usuario_id or not proyecto_id:
        return None
    try:
        with get_conn() as conn:
            r = conn.execute(
                "SELECT rol FROM usuario_proyecto_rol WHERE usuario_id=%s AND proyecto_id=%s",
                (usuario_id, proyecto_id)
            ).fetchone()
        return (r['rol'] if r else None)
    except Exception:
        return None


def sistemas_usuario_en_proyecto(usuario_id: int, proyecto_id: int) -> Optional[list]:
    """Lista de sistemas accesibles al usuario en ese proyecto.

    - NULL/None del DB → retorna None → acceso a TODOS los sistemas
    - Array → retorna la lista específica
    - Sin asignación → retorna [] (sin acceso a nada)
    """
    if not usuario_id or not proyecto_id:
        return []
    try:
        with get_conn() as conn:
            r = conn.execute(
                "SELECT sistemas FROM usuario_proyecto_rol WHERE usuario_id=%s AND proyecto_id=%s",
                (usuario_id, proyecto_id)
            ).fetchone()
        if not r:
            return []
        sistemas = r['sistemas']
        # NULL en DB → Python None → "todos"
        if sistemas is None:
            return None
        return list(sistemas)
    except Exception:
        return []


def puede_entrar_a_sistema(usuario_id: int, proyecto_id: int, sistema_codigo: str) -> bool:
    """Verifica que el usuario puede entrar a ese sistema en ese proyecto.

    Reglas:
    - Sin asignación en el proyecto → False
    - sistemas NULL → True (acceso total al proyecto)
    - sistemas lista → True si el sistema está en la lista
    """
    if not sistema_codigo:
        return False
    sistemas = sistemas_usuario_en_proyecto(usuario_id, proyecto_id)
    if sistemas == []:
        return False  # sin asignación
    if sistemas is None:
        return True   # acceso total
    return sistema_codigo in sistemas


def can(
    usuario_id: Optional[int],
    accion: str,
    proyecto_id: Optional[int] = None,
    rol_override: Optional[str] = None,
) -> bool:
    """¿El usuario puede realizar `accion` en este proyecto?

    - Si `rol_override` se pasa, usa ese rol directamente (útil cuando el sistema
      ya cargó el rol del usuario en request.state para no consultar la BD otra vez).
    - Si no, consulta `usuario_proyecto_rol` para obtener el rol.

    Retorna True si el rol del usuario >= rol mínimo requerido para la acción.
    """
    rol_req = ACCIONES.get(accion)
    if not rol_req:
        # Acción no listada = denegada por seguridad (mejor explícito que permisivo)
        return False

    if rol_override:
        rol_user = rol_override
    else:
        if not usuario_id or not proyecto_id:
            return False
        rol_user = rol_usuario_en_proyecto(usuario_id, proyecto_id)
        if not rol_user:
            return False

    return nivel(rol_user) >= nivel(rol_req)


def es_admin(usuario_id: Optional[int], proyecto_id: Optional[int] = None) -> bool:
    """Atajo: el user es admin? (global o en este proyecto)."""
    if not usuario_id:
        return False
    try:
        with get_conn() as conn:
            r = conn.execute(
                "SELECT rol_global FROM usuarios_global WHERE id=%s",
                (usuario_id,)
            ).fetchone()
            if r and r['rol_global'] in ('admin', 'administrador'):
                return True
            if proyecto_id:
                rp = conn.execute(
                    "SELECT rol FROM usuario_proyecto_rol WHERE usuario_id=%s AND proyecto_id=%s",
                    (usuario_id, proyecto_id)
                ).fetchone()
                if rp and rp['rol'] in ('admin', 'administrador', 'admin_proyecto'):
                    return True
    except Exception:
        pass
    return False


def acciones_permitidas(rol: Optional[str]) -> list:
    """Retorna el listado de códigos de acción que un rol puede realizar.

    Útil para construir UI condicional en frontend — pasar el rol del user
    y pre-computar qué botones mostrar.
    """
    if not rol:
        return []
    n = nivel(rol)
    return [accion for accion, rol_req in ACCIONES.items() if nivel(rol_req) <= n]
