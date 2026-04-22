"""Migraciones idempotentes del schema de kuboc-core.

Invocar al iniciar cualquier sistema consumidor (o ejecutar manualmente):

    from kuboc_core import migrations
    migrations.run()
"""
import logging
from kuboc_core.db import get_conn

logger = logging.getLogger(__name__)


SCHEMA_SQL = [
    # ── proyectos ───────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS proyectos (
        id              SERIAL PRIMARY KEY,
        codigo          TEXT NOT NULL UNIQUE,
        nombre          TEXT NOT NULL,
        tipo_indole     TEXT NOT NULL,
        moneda_base     TEXT NOT NULL DEFAULT 'PEN',
        fecha_inicio    DATE,
        fecha_fin       DATE,
        color_principal TEXT DEFAULT '#10B981',
        color_secundario TEXT DEFAULT '#059669',
        logo_url        TEXT,
        notas           TEXT,
        activo          BOOLEAN NOT NULL DEFAULT TRUE,
        con_contabilidad_detallada BOOLEAN NOT NULL DEFAULT FALSE,
        con_tributario_peru BOOLEAN NOT NULL DEFAULT TRUE,
        creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        creado_por      INTEGER
    )
    """,

    # ── proyecto_cuentas (reemplaza DYDIMA/KUBOC hardcoded) ────
    """
    CREATE TABLE IF NOT EXISTS proyecto_cuentas (
        id              SERIAL PRIMARY KEY,
        proyecto_id     INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        codigo          TEXT NOT NULL,
        nombre          TEXT NOT NULL,
        rol_cuenta      TEXT NOT NULL DEFAULT 'otro',
        color           TEXT,
        orden           INTEGER NOT NULL DEFAULT 0,
        activo          BOOLEAN NOT NULL DEFAULT TRUE,
        UNIQUE (proyecto_id, codigo)
    )
    """,

    # ── proyecto_categorias (reemplaza las 6 de minería hardcoded) ─
    """
    CREATE TABLE IF NOT EXISTS proyecto_categorias (
        id              SERIAL PRIMARY KEY,
        proyecto_id     INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        nombre          TEXT NOT NULL,
        codigo_cuenta_contable TEXT,
        cuenta_default  TEXT,
        color           TEXT,
        icono           TEXT,
        orden           INTEGER NOT NULL DEFAULT 0,
        activo          BOOLEAN NOT NULL DEFAULT TRUE,
        UNIQUE (proyecto_id, nombre)
    )
    """,

    # ── usuarios_global (SSO) ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS usuarios_global (
        id              SERIAL PRIMARY KEY,
        username        TEXT NOT NULL UNIQUE,
        pin_hash        TEXT NOT NULL,
        nombre_completo TEXT,
        email           TEXT,
        telegram_id     BIGINT UNIQUE,
        rol_global      TEXT NOT NULL DEFAULT 'usuario',
        activo          BOOLEAN NOT NULL DEFAULT TRUE,
        intentos_fallidos INTEGER NOT NULL DEFAULT 0,
        bloqueado_hasta TIMESTAMPTZ,
        ultimo_login    TIMESTAMPTZ,
        creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_usuarios_global_username ON usuarios_global(lower(username))",

    # ── usuario_proyecto_rol (pivot: un user puede ser admin en P1 y visor en P2) ─
    """
    CREATE TABLE IF NOT EXISTS usuario_proyecto_rol (
        usuario_id      INTEGER NOT NULL REFERENCES usuarios_global(id) ON DELETE CASCADE,
        proyecto_id     INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
        rol             TEXT NOT NULL,
        sistemas        TEXT[] DEFAULT NULL,  -- NULL = todos; sino lista: {facturas, ops, logistica, rrhh}
        asignado_en     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        asignado_por    INTEGER REFERENCES usuarios_global(id),
        PRIMARY KEY (usuario_id, proyecto_id)
    )
    """,

    # ── sessions (store central de tokens — permite logout global) ──
    """
    CREATE TABLE IF NOT EXISTS sessions (
        token           TEXT PRIMARY KEY,
        usuario_id      INTEGER NOT NULL REFERENCES usuarios_global(id) ON DELETE CASCADE,
        proyecto_activo_id INTEGER REFERENCES proyectos(id),
        sistema_origen  TEXT,
        creada_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expira_en       TIMESTAMPTZ NOT NULL,
        ultima_actividad TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        ip              TEXT,
        user_agent      TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sessions_usuario ON sessions(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_expira ON sessions(expira_en)",

    # ── plantillas_proyecto (cuentas + categorías por índole) ─
    """
    CREATE TABLE IF NOT EXISTS plantillas_proyecto (
        id              SERIAL PRIMARY KEY,
        codigo          TEXT NOT NULL UNIQUE,
        nombre          TEXT NOT NULL,
        tipo_indole     TEXT NOT NULL,
        cuentas_json    JSONB NOT NULL,
        categorias_json JSONB NOT NULL,
        descripcion     TEXT
    )
    """,

    # ── audit_log central del core ─────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id              BIGSERIAL PRIMARY KEY,
        fecha           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        usuario_id      INTEGER REFERENCES usuarios_global(id) ON DELETE SET NULL,
        usuario_username TEXT,  -- snapshot por si se borra el user
        proyecto_id     INTEGER REFERENCES proyectos(id) ON DELETE SET NULL,
        sistema         TEXT,
        accion          TEXT NOT NULL,
        detalle         TEXT,
        ip              TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_fecha ON audit_log(fecha DESC)",
    "CREATE INDEX IF NOT EXISTS idx_audit_usuario ON audit_log(usuario_id, fecha DESC)",
]


def run():
    """Ejecuta las migraciones idempotentes. Segura de correr N veces.

    Usa statement_timeout de 5s — si CREATE TABLE IF NOT EXISTS se queda
    esperando un lock (ej. transacción zombie de un deploy anterior),
    aborta y NO bloquea el startup indefinidamente.
    """
    with get_conn() as conn:
        # Fail-fast si hay locks colgados: 5s por statement
        conn.execute("SET statement_timeout = '5s'")
        # lock_timeout específico también — evita esperas largas por locks
        conn.execute("SET lock_timeout = '3s'")
        for stmt in SCHEMA_SQL:
            try:
                conn.execute(stmt)
            except Exception as e:
                # Si un statement falla, log y seguimos — DDL es idempotente y
                # el resto puede aplicarse independientemente.
                logger.warning(f"kuboc_core migration stmt falló (seguimos): {e}")
                conn.rollback()
                continue
        conn.commit()
    logger.info("kuboc_core: migraciones aplicadas")


def reset_dangerous():
    """⚠️ Elimina TODAS las tablas del core. Solo para tests/desarrollo."""
    with get_conn() as conn:
        conn.execute("""
            DROP TABLE IF EXISTS audit_log, sessions, usuario_proyecto_rol,
                                 proyecto_categorias, proyecto_cuentas,
                                 plantillas_proyecto, usuarios_global, proyectos CASCADE
        """)
        conn.commit()
    logger.warning("kuboc_core: TABLAS ELIMINADAS (reset_dangerous)")
