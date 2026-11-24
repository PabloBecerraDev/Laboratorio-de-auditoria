"""
Control de acceso basado en roles (A5.15 / A9.4), validado SIEMPRE en servidor.

El modulo de Clientes es, a proposito, el unico que NO complementa este control
de rol con una verificacion a nivel de objeto/registro (ver routes_clientes.py):
esa es la brecha tecnica deliberada usada para la auditoria (control de acceso
granular incompleto, IDOR/BOLA).
"""

from functools import wraps

from flask import abort
from flask_login import current_user


def requires_role(*roles_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.rol not in roles_permitidos:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
