"""kuboc-core — Librería compartida de la suite KUBOC.

Uso típico desde un sistema consumidor (Facturas, Ops, Logística, RRHH):

    from kuboc_core import auth, projects

    # Al logueo
    user = auth.login(username='JONY', pin='123456')
    if user:
        token = auth.create_session(user_id=user['id'], sistema='facturas')
        # setear cookie kuboc_session con el token

    # En cada request
    session = auth.validate_session(token)
    if not session:
        return redirect('/login')

    # Proyectos del usuario
    mis_proyectos = projects.list_for_user(user_id=session['user_id'])
    activo = projects.get_active(session)
    # filtrar queries con activo['id']
"""
from kuboc_core import auth, projects, templates, db, migrations

__version__ = "0.1.0"
__all__ = ["auth", "projects", "templates", "db", "migrations"]
