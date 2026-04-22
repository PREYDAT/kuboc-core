"""Conexión a Postgres. Pool simple con psycopg 3.

Uso:
    from kuboc_core.db import get_conn

    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM proyectos").fetchall()
"""
import logging
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from kuboc_core import config

logger = logging.getLogger(__name__)

_pool = None
_pool_init_attempted = False  # evita re-logs de warning en cada request


def _init_pool():
    """Inicializa el pool de conexiones (lazy). Idempotente y cache de fallo."""
    global _pool, _pool_init_attempted
    if _pool is not None:
        return _pool
    if _pool_init_attempted:
        return None  # ya intentado y falló — usar fallback directo sin log
    _pool_init_attempted = True
    config.validar()
    try:
        from psycopg_pool import ConnectionPool
        _pool = ConnectionPool(
            conninfo=config.DATABASE_URL,
            min_size=1,
            max_size=5,
            kwargs={'row_factory': dict_row},
        )
        _pool.open(wait=True, timeout=10)
        logger.info("kuboc_core: pool Postgres listo (min=1, max=5)")
    except ImportError:
        _pool = None
        logger.warning("kuboc_core: psycopg_pool no disponible, usando conexiones directas")
    except Exception as e:
        _pool = None
        logger.warning(f"kuboc_core: pool no se pudo abrir ({e}), usando conexiones directas")
    return _pool


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    """Context manager que yields una conexión Postgres con row_factory=dict_row.

    Commit automático al salir sin excepción, rollback si hay excepción.
    """
    _init_pool()
    if _pool:
        with _pool.connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    else:
        conn = psycopg.connect(config.DATABASE_URL, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def close_pool():
    """Cierra el pool limpiamente. Llamar en shutdown de la app."""
    global _pool
    if _pool is not None:
        try:
            _pool.close()
        except Exception:
            pass
        _pool = None


import atexit
atexit.register(close_pool)


def ping() -> bool:
    """Verifica que Postgres responda."""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"kuboc_core ping fallido: {e}")
        return False
