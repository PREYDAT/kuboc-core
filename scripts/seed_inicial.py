"""Seed inicial: aplica migraciones + siembra plantillas + crea Bonanza 2026 base.

Ejecutar UNA VEZ tras crear la BD Postgres:
    python -m scripts.seed_inicial

Es idempotente: correrlo N veces no duplica datos.
"""
import logging
import sys

from kuboc_core import migrations, templates, projects
from kuboc_core.db import get_conn, ping

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('seed')


def main():
    log.info("1/4 — Ping a Postgres")
    if not ping():
        log.error("FALLO: no se pudo conectar. Revisa DATABASE_URL")
        sys.exit(1)

    log.info("2/4 — Aplicando migraciones (crea 8 tablas si no existen)")
    migrations.run()

    log.info("3/4 — Sembrando plantillas de proyecto")
    templates.seed_plantillas()

    log.info("4/4 — Creando proyecto 'Bonanza 2026' si no existe")
    with get_conn() as conn:
        existente = conn.execute("SELECT id FROM proyectos WHERE codigo = %s", ('BONANZA_2026',)).fetchone()
    if existente:
        log.info(f"  ✓ Proyecto Bonanza 2026 ya existe con id={existente['id']}")
        proyecto_id = existente['id']
    else:
        proyecto_id = projects.crear_proyecto(
            codigo='BONANZA_2026',
            nombre='Bonanza 2026 (Acarí · Arequipa)',
            tipo_indole='mineria',
            plantilla='mineria_contratista',
            fecha_inicio='2026-01-01',
            color_principal='#1A3C6B',
            color_secundario='#5B2C6F',
            notas='Proyecto inicial de la suite KUBOC. Contratista KUBOC, cliente DYDIMA.',
        )
        log.info(f"  ✓ Proyecto Bonanza 2026 creado id={proyecto_id}")

    # Resumen
    with get_conn() as conn:
        n_proy = conn.execute("SELECT COUNT(*) AS n FROM proyectos").fetchone()['n']
        n_cuen = conn.execute("SELECT COUNT(*) AS n FROM proyecto_cuentas").fetchone()['n']
        n_cat = conn.execute("SELECT COUNT(*) AS n FROM proyecto_categorias").fetchone()['n']
        n_plt = conn.execute("SELECT COUNT(*) AS n FROM plantillas_proyecto").fetchone()['n']
    log.info(f"═══ RESUMEN ═══")
    log.info(f"  Proyectos: {n_proy}")
    log.info(f"  Cuentas totales: {n_cuen}")
    log.info(f"  Categorías totales: {n_cat}")
    log.info(f"  Plantillas disponibles: {n_plt}")
    log.info("✅ Seed inicial completado")


if __name__ == '__main__':
    main()
