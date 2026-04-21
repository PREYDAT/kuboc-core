# kuboc-core

Librería Python compartida de la **suite KUBOC** (Facturas, Operaciones, Logística, RRHH).

## Qué resuelve

Hoy cada sistema de la suite tiene:
- Su propia tabla `usuarios` con su propio login (3 logins distintos)
- Sus propias constantes hardcoded `PROJECT_NAME = 'BONANZA'`, `CONTRATISTA = 'KUBOC'`, `CLIENTE = 'DYDIMA'`
- Su propia lista de categorías de gasto hardcoded

Este paquete centraliza eso en **una BD Postgres compartida** para:
- **SSO** — un solo login, válido en todos los sistemas
- **Multi-proyecto** — una misma instancia maneja N proyectos de cualquier índole
- **Cuentas y categorías dinámicas por proyecto** — via plantillas predefinidas
- **Permisos granulares** — un usuario puede ser admin en un proyecto y visor en otro

## Arquitectura

```
                ┌──────────────────────────────────┐
                │  Postgres central (Railway)      │
                │  proyectos · usuarios_global     │
                │  sessions · usuario_proyecto_rol │
                │  plantillas · proyecto_cuentas   │
                │  proyecto_categorias · audit_log │
                └──────────────┬───────────────────┘
                               │
         ┌─────────────┬───────┴───────┬──────────────┐
         ▼             ▼               ▼              ▼
  ┌──────────┐  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ Facturas │  │   Ops    │   │ Almacén  │   │   RRHH   │
  │(SQLite)  │  │(SQLite)  │   │(SQLite)  │   │(SQLite)  │
  └──────────┘  └──────────┘   └──────────┘   └──────────┘
```

Cada sistema mantiene su SQLite para su data operativa (facturas, tareas, kardex, etc.)
y consulta al core via `pip install kuboc-core` para auth y contexto de proyecto.

## Uso desde un sistema consumidor

```python
from kuboc_core import auth, projects, migrations

# Al arrancar la app — garantiza que el schema del core esté aplicado
migrations.run()

# En tu ruta /login
user = auth.login(username='JONY', pin='123456',
                  ip=request.client.host,
                  user_agent=request.headers.get('user-agent'))
if user:
    token = auth.create_session(
        usuario_id=user['id'],
        sistema='facturas',
        ip=request.client.host,
    )
    response.set_cookie('kuboc_session', token, httponly=True, secure=True, samesite='lax')

# En middleware
session = auth.validate_session(request.cookies.get('kuboc_session'))
if not session:
    return RedirectResponse('/login')

# Obtener proyectos del usuario
mis_proyectos = projects.list_for_user(session['usuario_id'])

# Cuentas y categorías del proyecto activo
cuentas = projects.get_cuentas(session['proyecto_activo_id'])
categorias = projects.get_categorias(session['proyecto_activo_id'])

# Chequear permiso
if projects.user_has_role(session['usuario_id'], proyecto_id,
                          rol_min='operador', sistema='facturas'):
    # autorizado a escribir en este proyecto desde el sistema 'facturas'
    ...
```

## Instalación en otro repo

En el `requirements.txt` del sistema consumidor:

```
kuboc-core @ git+https://github.com/PREYDAT/kuboc-core.git@main
```

O para desarrollo local:

```bash
pip install -e ../kuboc-core
```

## Configuración

Variables de entorno (ver `.env.example`):

- `DATABASE_URL` — Postgres central (Railway lo provee)
- `KUBOC_CORE_SECRET` — secreto para firmar sesiones. **El mismo en todos los sistemas.**
- `KUBOC_COOKIE_NAME` (opcional, default `kuboc_session`)
- `KUBOC_SESSION_TTL_HOURS` (opcional, default `12`)

## Seed inicial

Tras crear la BD Postgres, ejecutar una vez:

```bash
python -m scripts.seed_inicial
```

Esto:
1. Aplica migraciones (crea las 8 tablas)
2. Siembra las 4 plantillas de proyecto (minería contratista, minería propia, construcción, agropecuario)
3. Crea el proyecto `BONANZA_2026` como base

## Plantillas de proyecto disponibles

| Código | Nombre | Uso |
|---|---|---|
| `mineria_contratista` | Minería Contratista | Operación minera donde somos contratistas (cliente + nosotros) |
| `mineria_propia` | Minería Propia | Operación directa, cuenta única |
| `construccion_civil` | Construcción Civil | Obras de edificación / infraestructura |
| `agropecuario` | Agropecuario | Agricultura / ganadería |

Al crear un proyecto con `plantilla='...'` se auto-poblan sus cuentas y categorías.

## Roles

Jerarquía (mayor incluye permisos del menor):

1. **admin** (4) — control total del proyecto
2. **contador / supervisor** (3) — edita, valida, genera reportes
3. **operador** (2) — registra y consulta
4. **visor / consulta** (1) — solo lectura

Un usuario puede tener rol distinto en cada proyecto (tabla `usuario_proyecto_rol`).

## Estado

Versión `0.1.0` — esquema inicial. Adoptado por Bot-Facturas-Log1 en Fase 3 del roadmap.
