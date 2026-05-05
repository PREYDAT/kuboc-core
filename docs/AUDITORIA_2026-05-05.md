# Auditoría kuboc-core — 2026-05-05

## Contexto

Primera auditoría sistemática del paquete `kuboc-core` como parte del plan
de mejora del ecosistema KUBOC. El objetivo de esta sesión: añadir tests
unitarios, formalizar versionado y CI, sin tocar la API pública.

## Estado encontrado

| Métrica | Valor |
|---|---|
| Archivos `.py` | 10 |
| Líneas de código | ~1,140 |
| Versión | 0.1.0 |
| Tests | 0 |
| Documentación API | parcial (docstrings) |
| CI | sin configurar |
| Stack | Psycopg 3 + itsdangerous + python-dotenv |
| BD | Postgres central |

## Bondades del diseño existente

- **Arquitectura limpia**: módulos bien separados (`auth`, `projects`, `permisos`,
  `templates`, `db`, `migrations`, `config`).
- **Idempotencia en migraciones**: `CREATE TABLE IF NOT EXISTS`, scripts seed.
- **Multi-tenant desde el origen**: tabla `proyectos` + `usuario_proyecto_rol`
  permite que un usuario tenga roles distintos en proyectos distintos.
- **Plantillas embebidas**: facilita crear un proyecto nuevo con cuentas y
  categorías típicas pre-cargadas.
- **Pool de conexiones lazy**: `_init_pool()` con cache de fallo evita re-logs.
- **Graceful degradation**: si la BD no está disponible, los sistemas consumidores
  pueden seguir operando (siguiendo el patrón del system-template).

## Problemas / debilidades detectadas

| Severidad | Problema | Impacto |
|---|---|---|
| 🔴 Alta | **Cero tests automatizados** | Cualquier cambio puede romper auth/permisos sin alertar |
| 🟠 Media | Versión `0.1.0` sin CHANGELOG | Cambios anteriores no rastreables |
| 🟠 Media | Sin CI configurado | No se valida que merges a `main` siguen pasando tests |
| 🟡 Baja | Docstrings de funciones públicas a veces escuetos | Curva de aprendizaje para sistemas consumidores |
| 🟡 Baja | No hay `pytest.ini` ni configuración de tooling | No es obvio cómo correr tests al clonar |
| 🟡 Baja | Sin tests de integración con Postgres real | No hay garantía que migraciones corren limpio |

## Cambios aplicados en esta sesión

### 1. Tests unitarios (`tests/`)

28 tests, todos verdes, agrupados en 4 archivos:

- `tests/test_auth.py` (10 tests):
  - `hash_pin` determinismo, longitud consistente, no-leak del PIN, robustez ante input vacío
  - `signed_token` round-trip, detección de tampering, payloads complejos
  - `verify_signed` rechaza tokens inválidos
- `tests/test_permisos.py` (7 tests):
  - Estructura de `NIVEL_ROL`, jerarquía completa (visor < operador < {contador, supervisor} < admin)
  - Consistencia con `projects.ROL_JERARQUIA`
  - Aliases `admin / administrador / admin_proyecto`
- `tests/test_templates.py` (5 tests):
  - PLANTILLAS no vacío, plantilla minera existe
  - Estructura básica, cuentas y categorías consistentes
- `tests/test_smoke.py` (6 tests):
  - Imports de los 8 módulos sin error
  - `__version__` definida
  - SCHEMA_SQL contiene `CREATE TABLE` para tablas críticas

Ejecución: `pytest tests/ -v` → **28 passed in 0.16s**

### 2. CHANGELOG.md

Formato Keep a Changelog. Documenta versiones 0.1.0 (inicial) y 0.2.0 (esta).

### 3. CI con GitHub Actions

`.github/workflows/ci.yml`:
- Corre tests en Python 3.11 / 3.12 / 3.13
- Trigger: push a main + pull_request
- Verifica imports después de tests

### 4. Mejoras en `pyproject.toml`

- Bump a versión `0.2.0`
- Sección `[project.optional-dependencies] test = ["pytest>=7.0"]`
- `[tool.pytest.ini_options]` con marker `integration` para futuros tests con BD real

### 5. Bump de `__version__` en `kuboc_core/__init__.py`

`0.1.0` → `0.2.0` (refleja añadidos sin cambios incompatibles).

## Pendientes para próximas sesiones

- [ ] Tests de integración con Postgres real (marker `@pytest.mark.integration`).
  Requiere fixture de BD efímera (pytest-postgresql o docker compose).
- [ ] Documentación de API en `docs/API.md` con ejemplos concretos de uso desde
  un sistema consumidor (firmar token, validar, refrescar).
- [ ] Validación de schema migrations: parser que detecte
  cambios no compatibles entre versiones del schema.
- [ ] Métricas / observabilidad: hook opcional en `db.get_conn` para
  contar queries y detectar N+1.
- [ ] Tests de race conditions en `auth.create_session` y rate limiting.

## Riesgos para los sistemas consumidores

**Cero impacto esperado**. Esta sesión NO toca:

- Schema de BD
- API pública de los módulos
- Plantillas embebidas
- Comportamiento runtime

Los consumidores (Bot-Facturas, Bonanza-Ops, KUBOC-LOGISTICA, kuboc-rrhh, kuboc-hub)
no necesitan ningún cambio.

## Cómo correr los tests

```bash
git clone https://github.com/PREYDAT/kuboc-core.git
cd kuboc-core
pip install -e ".[test]"
export KUBOC_CORE_SECRET="cualquier-string-32-chars"
export DATABASE_URL="postgresql://x:x@x:5432/x"  # no necesita conectar
pytest tests/ -v
```

---

**Auditor**: Claude (asistente IA, sesión Claude Code)
**Ejecutor**: PREYDAT
**Resultado**: 28/28 tests verdes · v0.1.0 → v0.2.0 · CI configurado
