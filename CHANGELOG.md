# Changelog

Todos los cambios notables a `kuboc-core` se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y este proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [0.2.0] — 2026-05-05

### Añadido
- **Suite de tests unitarios** en `tests/` con pytest. 28 tests cubren:
  - `auth`: hash_pin determinismo, longitud, robustez ante input vacío;
    signed_token round-trip, tampering detectado, payloads complejos.
  - `permisos`: jerarquía NIVEL_ROL (visor < operador < {contador, supervisor} < admin),
    consistencia con `projects.ROL_JERARQUIA`, aliases admin.
  - `templates`: estructura de PLANTILLAS, plantilla mineria_contratista,
    cuentas DYDIMA/KUBOC, consistencia de keys en categorías.
  - `smoke`: imports de todos los módulos, versión definida, schema SQL
    contiene CREATE TABLE para proyectos y usuarios.
- `tests/conftest.py` configura `KUBOC_CORE_SECRET` y `DATABASE_URL` para tests.
- `docs/AUDITORIA_2026-05-05.md` — auditoría inicial.
- `CHANGELOG.md` — este archivo.

### No cambiado
- Schema de BD (compat 100% con 0.1.0).
- API pública de los módulos (`auth`, `projects`, `permisos`, `templates`).
- Plantillas embebidas.

### Notas
- Los tests **no requieren Postgres** — validan lógica pura.
- Para tests de integración con BD real se necesita un Postgres y `pytest -m integration`
  (marca pendiente de implementar).

## [0.1.0] — 2026-04-22

### Versión inicial
- Schema multi-tenant: proyectos, usuarios_global, usuario_proyecto_rol,
  proyecto_cuentas, proyecto_categorias, sessions, audit_log.
- Módulos: `auth`, `projects`, `permisos`, `templates`, `db`, `migrations`, `config`.
- Plantillas embebidas: mineria_contratista (más).
- Estrategia multi-tenant 2 etapas: segmentación por volumen (MVP) + multi-tenant real (futuro).
