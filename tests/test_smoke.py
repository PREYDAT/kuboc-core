"""Smoke tests — verifica que todos los módulos cargan sin error."""
import importlib


MODULOS = [
    'kuboc_core',
    'kuboc_core.auth',
    'kuboc_core.config',
    'kuboc_core.db',
    'kuboc_core.migrations',
    'kuboc_core.permisos',
    'kuboc_core.projects',
    'kuboc_core.templates',
]


def test_todos_los_modulos_importan():
    for mod in MODULOS:
        m = importlib.import_module(mod)
        assert m is not None, f'no se pudo importar {mod}'


def test_version_definida():
    import kuboc_core
    assert hasattr(kuboc_core, '__version__')
    assert kuboc_core.__version__, 'version vacía'


def test_migrations_schema_sql_es_lista_no_vacia():
    """SCHEMA_SQL debe contener al menos las tablas del core."""
    from kuboc_core import migrations
    assert isinstance(migrations.SCHEMA_SQL, list)
    assert len(migrations.SCHEMA_SQL) > 0


def test_migrations_sql_son_strings_create_table():
    from kuboc_core import migrations
    # Al menos una sentencia CREATE TABLE
    has_create = any('CREATE TABLE' in s.upper() for s in migrations.SCHEMA_SQL if isinstance(s, str))
    assert has_create, 'SCHEMA_SQL sin CREATE TABLE'


def test_migrations_incluye_tabla_proyectos():
    from kuboc_core import migrations
    sql_join = ' '.join(s for s in migrations.SCHEMA_SQL if isinstance(s, str)).lower()
    assert 'proyectos' in sql_join


def test_migrations_incluye_tabla_usuarios():
    from kuboc_core import migrations
    sql_join = ' '.join(s for s in migrations.SCHEMA_SQL if isinstance(s, str)).lower()
    assert 'usuarios_global' in sql_join or 'usuarios' in sql_join
