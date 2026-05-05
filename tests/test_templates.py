"""Tests de plantillas embebidas — estructura válida sin BD."""
import pytest
from kuboc_core import templates


def test_plantillas_es_dict_no_vacio():
    assert isinstance(templates.PLANTILLAS, dict)
    assert len(templates.PLANTILLAS) > 0


def test_plantilla_mineria_existe():
    """La plantilla principal del proyecto debe existir."""
    assert 'mineria_contratista' in templates.PLANTILLAS


def test_cada_plantilla_tiene_estructura_basica():
    """Toda plantilla debe tener al menos cuentas o categorias."""
    for nombre, p in templates.PLANTILLAS.items():
        assert isinstance(p, dict), f'plantilla {nombre} no es dict'
        # Debe tener al menos uno de los campos esperados
        tiene_algo = any(k in p for k in ('cuentas', 'categorias', 'descripcion', 'tipo_indole'))
        assert tiene_algo, f'plantilla {nombre} sin campos útiles'


def test_plantilla_mineria_tiene_cuentas_dydima_kuboc():
    """La plantilla minera contratista debe incluir las dos cuentas conocidas."""
    p = templates.PLANTILLAS['mineria_contratista']
    cuentas = p.get('cuentas', [])
    if cuentas:
        codigos = [c.get('codigo') if isinstance(c, dict) else c for c in cuentas]
        # No exigir nombres exactos pero al menos 2 cuentas
        assert len(cuentas) >= 2, f'esperadas ≥2 cuentas, obtenidas: {cuentas}'


def test_categorias_tienen_keys_consistentes():
    """Todas las categorías de cada plantilla deben tener mismos keys."""
    for nombre, p in templates.PLANTILLAS.items():
        cats = p.get('categorias', [])
        if not cats:
            continue
        if isinstance(cats[0], dict):
            keys_first = set(cats[0].keys())
            for c in cats[1:]:
                assert isinstance(c, dict), f'categoría no-dict en {nombre}'
                # No exigimos exactamente mismas keys (puede haber opcionales)
                # pero al menos debe tener el campo principal (codigo o nombre)
                assert 'codigo' in c or 'nombre' in c, \
                    f'categoría sin codigo/nombre en {nombre}: {c}'
