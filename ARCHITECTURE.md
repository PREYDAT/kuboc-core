# KUBOC Suite — Architecture

Documento vivo de la arquitectura de la suite KUBOC. Actualizar cuando cambien decisiones estructurales.

## Visión general

KUBOC Suite = **5 repos independientes** que comparten identidad y proyectos vía `kuboc-core` (librería + Postgres central).

```
                    ┌─────────────────────────────────┐
                    │   🏢 KUBOC HUB (portal raíz)    │
                    │   kuboc-hub.railway.app         │
                    │   Login SSO + selector proy.    │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────┴────────────────────┐
                    │   kuboc-core                    │
                    │   Python lib + Postgres Railway │
                    │   tablas: proyectos, usuarios,  │
                    │   sessions, proyecto_cuentas,   │
                    │   proyecto_categorias,          │
                    │   usuario_proyecto_rol,         │
                    │   plantillas_proyecto, audit    │
                    └────────────┬────────────────────┘
                                 │ pip install kuboc-core
         ┌───────────────┬───────┼───────┬───────────────┐
         ▼               ▼       ▼       ▼               ▼
   ┌──────────┐   ┌─────────┐ ┌──────┐ ┌──────────┐ ┌────────┐
   │ Facturas │   │  Ops    │ │Logist│ │  RRHH    │ │  Tpl   │
   │(SQLite)  │   │(SQLite) │ │(SQL) │ │(por      │ │ futuro │
   │          │   │         │ │      │ │  hacer)  │ │        │
   └──────────┘   └─────────┘ └──────┘ └──────────┘ └────────┘
   Railway         Railway    Railway
   proy: Bot       proy: Ops  proy: ALM
```

## Repos y responsabilidades

| Repo | Rol | Deploy | BD |
|------|-----|--------|-----|
| `kuboc-core` | Librería Python + schema Postgres central | no-deploy | Postgres (Railway proyecto **KUBOC SUITE CORE**) |
| `kuboc-hub` | Portal de entrada (SSO + admin global + consolidado) | Railway proyecto **KUBOC SUITE CORE** · servicio `kuboc-hub` | Comparte Postgres del core |
| `Bot-Facturas-Log1` | Registro de gastos + bot Telegram + web contable | Railway proyecto **SERVER BOT FACTURAS PRINCIPAL** | SQLite local + sync al core |
| `Bonanza-Ops` | Reportes operativos mineros (HH, tareas, voladura) | Railway proyecto **SISTEMA OPERACIONES BN** | SQLite local + sync al core |
| `KUBOC-LOGISTICA` | Almacenes, kardex, órdenes de compra | Railway proyecto **SISTEMA LOGISTICO KUBOC ALM** | SQLite local + sync al core |
| `KUBOC-RRHH` (futuro) | Planillas, contratos, asistencia | nuevo deploy | nuevo SQLite + sync |

## Base de datos

### Postgres central (kuboc-core)

| Tabla | Uso |
|-------|-----|
| `proyectos` | id, codigo, nombre, tipo_indole, colores, flags |
| `proyecto_cuentas` | Cuentas de cada proyecto (ej: DYDIMA/KUBOC en Bonanza) |
| `proyecto_categorias` | Categorías válidas por proyecto (minería / agro / construcción) |
| `usuarios_global` | Identidad única SSO |
| `usuario_proyecto_rol` | Pivot: rol por usuario × proyecto |
| `sessions` | Tokens activos cross-sistema |
| `plantillas_proyecto` | 4 plantillas seed: mineria_contratista, mineria_propia, construccion_civil, agropecuario |
| `audit_log` | Log central de acciones |

### SQLite locales (sistemas consumidores)

Cada sistema mantiene su SQLite **con FK blanda** a `proyecto_id` (sin constraint cross-DB):

- `Bot-Facturas-Log1`: `facturas`, `pagos`, `items`, `rendiciones`, `retenciones_detracciones`, etc. — todas con `proyecto_id INTEGER DEFAULT 1`
- `Bonanza-Ops`: `reportes`, `personal`, `avance`, `perforacion`, `voladura`, `compras`, etc.
- `KUBOC-LOGISTICA`: `almacenes`, `articulos`, `stock`, `movimientos`, `requerimientos`, etc.

## Auth flow

### Sin core (modo legacy, default actual)
```
Usuario → login en cualquier sistema → valida tabla usuarios local → cookie local
```

### Con core (modo SSO, `USE_CORE_AUTH=true`)
```
1. Usuario → kuboc-hub/login
2. Hub valida contra core.usuarios_global con PIN
3. Hub escribe cookie `kuboc_session` (HTTPOnly, dominio raíz si shared)
4. Usuario click en sistema satélite → /ir/{sistema}?kt=<token>
5. Sistema satélite llama core.validate_session(token) → sesión válida
6. Sistema usa core.projects para cuentas/categorías dinámicas
```

## Shadow mode (activo hoy en los 3 sistemas)

- `USE_CORE_AUTH=false` → login sigue local
- `CORE_SYNC_USERS=true` → al crear/editar usuario también se refleja en `usuarios_global`
- `bulk_sync_all_users()` corre al startup (idempotente)
- Si el core falla, **el sistema sigue operando normal** (tolerante a fallos)

## Feature flags (env vars)

| Variable | Default | Propósito |
|----------|---------|-----------|
| `USE_CORE_AUTH` | `false` | Activa validación via core en login |
| `CORE_SYNC_USERS` | `true` | Activa shadow-sync de usuarios al core |
| `CORE_DATABASE_URL` | — | URL Postgres del core (Railway inyecta) |
| `KUBOC_CORE_SECRET` | — | Secreto firmas `itsdangerous` — mismo en todos los servicios |
| `BONANZA_PROYECTO_ID` | `1` | Proyecto default cuando aún no hay multi-tenant real |

## Cómo agregar un sistema nuevo a la suite (ej. RRHH)

1. Crear repo nuevo siguiendo la estructura típica (`app/main.py`, `app/auth.py`, etc.)
2. Agregar a `requirements.txt`:
   ```
   kuboc-core @ git+https://github.com/PREYDAT/kuboc-core.git@main
   psycopg[binary]>=3.2.0
   itsdangerous>=2.2.0
   ```
3. Crear `app/core_integration.py` siguiendo el patrón de los otros sistemas:
   - `is_available()`, `status()`, `sync_user_to_core()`, `bulk_sync_all_users()`
   - Feature flags `USE_CORE_AUTH`, `CORE_SYNC_USERS`
4. Hook al startup en `lifespan`: ping + bulk_sync
5. Agregar `proyecto_id INTEGER DEFAULT 1` a tablas transaccionales (migración idempotente)
6. En el admin de usuarios: llamar `sync_user_to_core()` después de insertar/editar
7. Agregar el sistema al catálogo del hub: `kuboc-hub/app/config.py::SISTEMAS`
8. Env vars Railway: `CORE_DATABASE_URL`, `KUBOC_CORE_SECRET` (del proyecto KUBOC SUITE CORE)

## Convenciones

### Roles (jerarquía, mayor incluye menor)
1. `admin` / `admin_proyecto` (4) — control total del proyecto
2. `contador` / `supervisor` (3) — edita y valida
3. `operador` (2) — registra
4. `visor` / `consulta` (1) — solo lectura

Un usuario puede tener rol distinto por proyecto (tabla `usuario_proyecto_rol`).

### Nombres de variables env
- `CORE_*` → kuboc-core
- `URL_*` → URLs de sistemas satélite desde el hub
- `DB_PATH` / `DATABASE_URL` → BD del sistema local (sigue usando)

### Colores oficiales
| Uso | Color | Hex |
|-----|-------|-----|
| Azul corporativo (accent) | `--accent` | `#3B4E7B` |
| Azul medio (hover, tags) | `--accent-light` | `#5B70A0` |
| Azul oscuro (cima logo) | `--accent-dark` | `#2E3E63` |
| Cálido (deltas +) | `--accent-warm` | `#F59E0B` |
| Frío (highlights) | `--accent-cool` | `#14B8A6` |

### Tipografía
- Display: **Geist** (variable 100-900)
- Body: **Inter Tight** (variable 400-700)
- Mono: **JetBrains Mono** (variable 400-600)

## Roadmap histórico

| Fase | Estado | Descripción |
|------|:-:|-------------|
| 0 | ✅ | Backups + repos nuevos + Postgres Railway |
| 1 | ✅ | kuboc-core librería + 8 tablas + 4 plantillas + seed Bonanza |
| 2 | ✅ | kuboc-hub deploy + login + CRUD proyectos/usuarios |
| 3.A-C | ✅ | Bot-Facturas-Log1 con core opcional + shadow sync + proyecto_id |
| 3.D | ⏸️ | Activar `USE_CORE_AUTH=true` tras validar shadow N días |
| 4 | ✅ | Bonanza-Ops con core opcional |
| 5 | ✅ | KUBOC-LOGISTICA con core opcional |
| 6 | ✅ | Dashboard consolidado ejecutivo |
| 7 | ✅ | ARCHITECTURE.md + template RRHH |

## Activación de USE_CORE_AUTH (cuando proceda)

Checklist antes de poner `USE_CORE_AUTH=true` en producción:
- [ ] Shadow sync corriendo al menos 3-5 días sin errores
- [ ] `kuboc-core.usuarios_global` tiene count coincidente con suma de tablas locales
- [ ] Test manual: login en hub → redirigir a sistema satélite → cookie compartida funciona
- [ ] Rollback preparado: volver `USE_CORE_AUTH=false` requiere solo editar env var y restart
- [ ] Comunicar a usuarios que usen su mismo PIN (sync ya lo garantiza)

## Documentos relacionados

- `kuboc-core/README.md` — API de la librería
- `kuboc-hub/README.md` — deploy del portal
- `Bot-Facturas-Log1/CLAUDE.md` — reglas de negocio bot facturas
- `Bonanza-Ops/CLAUDE.md` — reglas de negocio operaciones
- `KUBOC-LOGISTICA/CLAUDE.md` — reglas de negocio almacén
