"""Plantillas de proyecto por índole.

Cuando creas un proyecto nuevo eliges una plantilla y se auto-poblan sus cuentas
y categorías típicas. Se pueden editar después desde /admin/proyectos.
"""
import json
import logging
from typing import Optional

from kuboc_core.db import get_conn

logger = logging.getLogger(__name__)


# Plantillas embebidas. Se siembran en BD al correr seed_plantillas().
PLANTILLAS = {
    'mineria_contratista': {
        'nombre': 'Minería Contratista',
        'tipo_indole': 'mineria',
        'descripcion': 'Proyecto minero subterráneo donde somos contratistas (cliente + nosotros).',
        'cuentas': [
            {'codigo': 'TITULAR',     'nombre': 'Titular (cliente)',        'rol_cuenta': 'cliente',     'color': '#1A3C6B', 'orden': 1},
            {'codigo': 'CONTRATISTA', 'nombre': 'Contratista (nosotros)',   'rol_cuenta': 'contratista', 'color': '#5B2C6F', 'orden': 2},
        ],
        'categorias': [
            {'nombre': 'MATERIALES Y HERRAMIENTAS', 'cuenta_default': 'CONTRATISTA', 'color': '#3B82F6', 'icono': 'fa-solid fa-screwdriver-wrench', 'orden': 1},
            {'nombre': 'EQUIPOS',                   'cuenta_default': 'CONTRATISTA', 'color': '#8B5CF6', 'icono': 'fa-solid fa-truck-monster',      'orden': 2},
            {'nombre': 'LOGÍSTICA',                 'cuenta_default': 'TITULAR',     'color': '#F59E0B', 'icono': 'fa-solid fa-truck',              'orden': 3},
            {'nombre': 'INSUMOS OPERATIVOS',        'cuenta_default': 'CONTRATISTA', 'color': '#EF4444', 'icono': 'fa-solid fa-oil-can',            'orden': 4},
            {'nombre': 'GASTOS GENERALES',          'cuenta_default': 'TITULAR',     'color': '#10B981', 'icono': 'fa-solid fa-receipt',            'orden': 5},
            {'nombre': 'MADERA',                    'cuenta_default': 'TITULAR',     'color': '#A16207', 'icono': 'fa-solid fa-tree',               'orden': 6},
        ],
    },

    'mineria_propia': {
        'nombre': 'Minería Propia',
        'tipo_indole': 'mineria',
        'descripcion': 'Operación minera directa, cuenta única.',
        'cuentas': [
            {'codigo': 'OPERACION', 'nombre': 'Operación', 'rol_cuenta': 'unica', 'color': '#1A3C6B', 'orden': 1},
        ],
        'categorias': [
            {'nombre': 'EXPLORACIÓN',      'cuenta_default': 'OPERACION', 'color': '#3B82F6', 'icono': 'fa-solid fa-mountain-sun',       'orden': 1},
            {'nombre': 'EXPLOTACIÓN',      'cuenta_default': 'OPERACION', 'color': '#8B5CF6', 'icono': 'fa-solid fa-helmet-safety',      'orden': 2},
            {'nombre': 'VOLADURA',         'cuenta_default': 'OPERACION', 'color': '#EF4444', 'icono': 'fa-solid fa-bomb',               'orden': 3},
            {'nombre': 'EQUIPOS',          'cuenta_default': 'OPERACION', 'color': '#F59E0B', 'icono': 'fa-solid fa-truck-monster',      'orden': 4},
            {'nombre': 'MANTENIMIENTO',    'cuenta_default': 'OPERACION', 'color': '#10B981', 'icono': 'fa-solid fa-screwdriver-wrench', 'orden': 5},
            {'nombre': 'COMBUSTIBLES',     'cuenta_default': 'OPERACION', 'color': '#DC2626', 'icono': 'fa-solid fa-gas-pump',           'orden': 6},
            {'nombre': 'EPP',              'cuenta_default': 'OPERACION', 'color': '#06B6D4', 'icono': 'fa-solid fa-hard-hat',           'orden': 7},
            {'nombre': 'GEOLOGÍA',         'cuenta_default': 'OPERACION', 'color': '#84CC16', 'icono': 'fa-solid fa-chart-line',         'orden': 8},
            {'nombre': 'LOGÍSTICA',        'cuenta_default': 'OPERACION', 'color': '#A855F7', 'icono': 'fa-solid fa-truck',              'orden': 9},
            {'nombre': 'GASTOS GENERALES', 'cuenta_default': 'OPERACION', 'color': '#14B8A6', 'icono': 'fa-solid fa-receipt',            'orden': 10},
        ],
    },

    'construccion_civil': {
        'nombre': 'Construcción Civil',
        'tipo_indole': 'construccion',
        'descripcion': 'Obra civil (edificaciones, infraestructura).',
        'cuentas': [
            {'codigo': 'CLIENTE',      'nombre': 'Cliente',       'rol_cuenta': 'cliente',     'color': '#1A3C6B', 'orden': 1},
            {'codigo': 'CONSTRUCTORA', 'nombre': 'Constructora',  'rol_cuenta': 'contratista', 'color': '#5B2C6F', 'orden': 2},
        ],
        'categorias': [
            {'nombre': 'CEMENTO Y CONCRETO',  'cuenta_default': 'CONSTRUCTORA', 'color': '#6b7280', 'icono': 'fa-solid fa-cubes-stacked',  'orden': 1},
            {'nombre': 'FIERRO / ACERO',      'cuenta_default': 'CONSTRUCTORA', 'color': '#78716c', 'icono': 'fa-solid fa-industry',        'orden': 2},
            {'nombre': 'ENCOFRADO',           'cuenta_default': 'CONSTRUCTORA', 'color': '#A16207', 'icono': 'fa-solid fa-border-all',      'orden': 3},
            {'nombre': 'MANO DE OBRA',        'cuenta_default': 'CONSTRUCTORA', 'color': '#10B981', 'icono': 'fa-solid fa-people-carry-box','orden': 4},
            {'nombre': 'MAQUINARIA ALQUILADA','cuenta_default': 'CLIENTE',      'color': '#F59E0B', 'icono': 'fa-solid fa-tractor',         'orden': 5},
            {'nombre': 'ACABADOS',            'cuenta_default': 'CONSTRUCTORA', 'color': '#EC4899', 'icono': 'fa-solid fa-paint-roller',    'orden': 6},
            {'nombre': 'PERMISOS Y LICENCIAS','cuenta_default': 'CLIENTE',      'color': '#3B82F6', 'icono': 'fa-solid fa-file-signature',  'orden': 7},
            {'nombre': 'GASTOS GENERALES',    'cuenta_default': 'CONSTRUCTORA', 'color': '#14B8A6', 'icono': 'fa-solid fa-receipt',         'orden': 8},
        ],
    },

    'agropecuario': {
        'nombre': 'Agropecuario',
        'tipo_indole': 'agropecuario',
        'descripcion': 'Actividad agrícola o ganadera.',
        'cuentas': [
            {'codigo': 'PRODUCCION', 'nombre': 'Producción', 'rol_cuenta': 'unica', 'color': '#10B981', 'orden': 1},
        ],
        'categorias': [
            {'nombre': 'SEMILLAS',        'cuenta_default': 'PRODUCCION', 'color': '#84CC16', 'icono': 'fa-solid fa-seedling',           'orden': 1},
            {'nombre': 'FERTILIZANTES',   'cuenta_default': 'PRODUCCION', 'color': '#A16207', 'icono': 'fa-solid fa-leaf',               'orden': 2},
            {'nombre': 'PESTICIDAS',      'cuenta_default': 'PRODUCCION', 'color': '#DC2626', 'icono': 'fa-solid fa-spray-can',          'orden': 3},
            {'nombre': 'MANO DE OBRA',    'cuenta_default': 'PRODUCCION', 'color': '#10B981', 'icono': 'fa-solid fa-people-group',       'orden': 4},
            {'nombre': 'MAQUINARIA',      'cuenta_default': 'PRODUCCION', 'color': '#F59E0B', 'icono': 'fa-solid fa-tractor',            'orden': 5},
            {'nombre': 'RIEGO',           'cuenta_default': 'PRODUCCION', 'color': '#06B6D4', 'icono': 'fa-solid fa-droplet',            'orden': 6},
            {'nombre': 'COSECHA',         'cuenta_default': 'PRODUCCION', 'color': '#F97316', 'icono': 'fa-solid fa-wheat-awn',          'orden': 7},
            {'nombre': 'TRANSPORTE',      'cuenta_default': 'PRODUCCION', 'color': '#8B5CF6', 'icono': 'fa-solid fa-truck',              'orden': 8},
            {'nombre': 'GASTOS GENERALES','cuenta_default': 'PRODUCCION', 'color': '#14B8A6', 'icono': 'fa-solid fa-receipt',            'orden': 9},
        ],
    },
}


def seed_plantillas() -> None:
    """Idempotente: carga las plantillas a BD (si no existen)."""
    with get_conn() as conn:
        for codigo, p in PLANTILLAS.items():
            conn.execute(
                """INSERT INTO plantillas_proyecto (codigo, nombre, tipo_indole, cuentas_json, categorias_json, descripcion)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (codigo) DO UPDATE SET
                        nombre = EXCLUDED.nombre,
                        cuentas_json = EXCLUDED.cuentas_json,
                        categorias_json = EXCLUDED.categorias_json,
                        descripcion = EXCLUDED.descripcion""",
                (codigo, p['nombre'], p['tipo_indole'],
                 json.dumps(p['cuentas']), json.dumps(p['categorias']),
                 p.get('descripcion'))
            )


def aplicar(proyecto_id: int, plantilla_codigo: str) -> None:
    """Aplica una plantilla a un proyecto: crea sus cuentas y categorías."""
    p = PLANTILLAS.get(plantilla_codigo)
    if not p:
        raise ValueError(f"Plantilla desconocida: {plantilla_codigo}")
    with get_conn() as conn:
        for c in p['cuentas']:
            conn.execute(
                """INSERT INTO proyecto_cuentas (proyecto_id, codigo, nombre, rol_cuenta, color, orden)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (proyecto_id, codigo) DO NOTHING""",
                (proyecto_id, c['codigo'], c['nombre'], c['rol_cuenta'], c.get('color'), c.get('orden', 0))
            )
        for cat in p['categorias']:
            conn.execute(
                """INSERT INTO proyecto_categorias (proyecto_id, nombre, cuenta_default, color, icono, orden)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (proyecto_id, nombre) DO NOTHING""",
                (proyecto_id, cat['nombre'], cat.get('cuenta_default'),
                 cat.get('color'), cat.get('icono'), cat.get('orden', 0))
            )
    logger.info(f"kuboc_core: plantilla '{plantilla_codigo}' aplicada a proyecto {proyecto_id}")


def listar_plantillas() -> list[dict]:
    """Lista plantillas disponibles para mostrar en el UI."""
    return [
        {'codigo': k, 'nombre': v['nombre'], 'tipo_indole': v['tipo_indole'],
         'descripcion': v.get('descripcion', ''),
         'n_cuentas': len(v['cuentas']), 'n_categorias': len(v['categorias'])}
        for k, v in PLANTILLAS.items()
    ]
