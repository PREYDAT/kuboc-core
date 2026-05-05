"""Tests del módulo permisos — jerarquía de roles y matriz de capacidades.

No requieren BD: validan la lógica pura de NIVEL_ROL y constantes.
"""
from kuboc_core import permisos
from kuboc_core import projects


def test_nivel_rol_existe_y_es_dict():
    assert isinstance(permisos.NIVEL_ROL, dict)
    assert len(permisos.NIVEL_ROL) > 0


def test_nivel_rol_admin_es_mayor_que_visor():
    assert permisos.NIVEL_ROL['admin'] > permisos.NIVEL_ROL['visor']


def test_nivel_rol_supervisor_mayor_que_operador():
    assert permisos.NIVEL_ROL['supervisor'] > permisos.NIVEL_ROL['operador']


def test_nivel_rol_contador_supervisor_paralelos():
    """Contador y supervisor son roles paralelos del mismo nivel (capacidades distintas, mismo poder)."""
    assert permisos.NIVEL_ROL['contador'] > permisos.NIVEL_ROL['operador']
    assert permisos.NIVEL_ROL['supervisor'] > permisos.NIVEL_ROL['operador']
    # Ambos son nivel 3 según la implementación actual
    assert permisos.NIVEL_ROL['contador'] == permisos.NIVEL_ROL['supervisor']


def test_jerarquia_completa_ordenada():
    """visor < operador < {contador,supervisor} < admin."""
    assert permisos.NIVEL_ROL['visor'] < permisos.NIVEL_ROL['operador']
    assert permisos.NIVEL_ROL['operador'] < permisos.NIVEL_ROL['contador']
    assert permisos.NIVEL_ROL['operador'] < permisos.NIVEL_ROL['supervisor']
    assert permisos.NIVEL_ROL['contador'] < permisos.NIVEL_ROL['admin']
    assert permisos.NIVEL_ROL['supervisor'] < permisos.NIVEL_ROL['admin']


# ── projects.ROL_JERARQUIA ─────────────────────────────────

def test_projects_rol_jerarquia_consistente_con_permisos():
    """projects.ROL_JERARQUIA debe ordenar admin > resto."""
    j = projects.ROL_JERARQUIA
    assert j['admin'] >= j['contador'] >= j['operador'] >= j['visor']


def test_projects_aliases_admin():
    """admin / administrador / admin_proyecto deben tener mismo nivel."""
    j = projects.ROL_JERARQUIA
    assert j['admin'] == j.get('administrador', j['admin'])
    assert j['admin'] == j.get('admin_proyecto', j['admin'])
