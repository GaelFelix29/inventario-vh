from flask import (
    abort,
    Flask,
    flash,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)
from user_agents import parse
import os
import secrets
import warnings
from urllib.parse import urljoin, urlparse
from flask_wtf.csrf import CSRFError, CSRFProtect
from functools import wraps
from datetime import timedelta
from models.auditoria_model import registrar_movimiento

# ==========================================
# BASE DE DATOS
# ==========================================

from routes.usuarios import registrar_rutas_usuarios
from routes.actividad import registrar_rutas_actividad
from routes.dashboard import registrar_rutas_dashboard
from routes.etiquetas import registrar_rutas_etiquetas
from routes.maquinaria import registrar_rutas_maquinaria
from routes.solicitudes import registrar_rutas_solicitudes
from routes.aduanas import registrar_rutas_aduanas
from routes.documentos import registrar_rutas_documentos
from routes.evidencias import registrar_rutas_evidencias
from routes.respaldos import registrar_rutas_respaldos
from routes.movimientos_mobile import registrar_rutas_movimientos_mobile
from routes.maquinaria_mobile import registrar_rutas_maquinaria_mobile
from routes.accesorios import registrar_rutas_accesorios
from routes.contenido import registrar_rutas_contenido
from routes.autenticacion import registrar_rutas_autenticacion
from routes.perfil import registrar_rutas_perfil
from routes.inicio import registrar_rutas_inicio

# ==========================================
# APP
# ==========================================

app = Flask(__name__)

secret_key = os.getenv("SECRET_KEY")

if not secret_key:
    if os.getenv("RENDER"):
        raise RuntimeError(
            "Falta la variable de entorno SECRET_KEY en Render."
        )

    secret_key = secrets.token_urlsafe(32)
    warnings.warn(
        "SECRET_KEY no está configurada; se usará una clave temporal local.",
        RuntimeWarning,
    )

app.config.update(
    SECRET_KEY=secret_key,
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

csrf = CSRFProtect(app)


@app.errorhandler(CSRFError)
def manejar_error_csrf(error):
    """Rechaza solicitudes modificadoras sin un token de sesión válido."""

    if request.accept_mimetypes.best == "application/json":
        return jsonify({"ok": False, "error": "Solicitud inválida o vencida."}), 400

    flash(
        "La sesión del formulario venció. Recarga la página e inténtalo nuevamente.",
        "warning",
    )
    return redirect(request.referrer or url_for("inicio"))


def es_url_interna(destino):
    """Permite redirecciones únicamente dentro de esta aplicación."""

    if not destino:
        return False

    host = urlparse(request.host_url)
    url_destino = urlparse(urljoin(request.host_url, destino))

    return (
        url_destino.scheme in ("http", "https")
        and url_destino.netloc == host.netloc
    )


@app.after_request
def agregar_encabezados_seguridad(response):
    """Añade protecciones del navegador sin alterar las vistas existentes."""

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(self), microphone=(), geolocation=()"
    )

    if request.is_secure:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response

# ==========================================
# DECORADORES
# ==========================================


def es_dispositivo_movil():

    user_agent = request.headers.get("User-Agent")

    ua = parse(user_agent)

    return ua.is_mobile or ua.is_tablet

def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "usuario_id" not in session:

            if (
                "next_url" not in session
                and not request.path.startswith("/static/")
                and request.path != "/favicon.ico"
            ):
                session["next_url"] = request.url

            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


def roles_required(*roles_permitidos):
    """Autoriza una operación únicamente a los roles indicados."""

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            if session.get("rol") not in roles_permitidos:
                abort(403)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "usuario_id" not in session:

            return redirect(url_for("login"))

        if session.get("rol") != "Administrador":

            flash("No tienes permisos para acceder a esta sección.", "danger")

            return redirect(url_for("inicio"))

        return func(*args, **kwargs)

    return wrapper

# ==========================================================
# SERVIDOR
# ==========================================================

registrar_rutas_usuarios(app, admin_required, registrar_movimiento)
registrar_rutas_actividad(app, login_required)
registrar_rutas_dashboard(app, login_required)
registrar_rutas_etiquetas(app, login_required)
registrar_rutas_maquinaria(
    app,
    login_required,
    roles_required,
    registrar_movimiento,
    es_dispositivo_movil,
)
registrar_rutas_solicitudes(
    app,
    login_required,
    registrar_movimiento,
)
registrar_rutas_aduanas(app, login_required, registrar_movimiento)
registrar_rutas_documentos(app, login_required, registrar_movimiento)
registrar_rutas_evidencias(app, login_required, registrar_movimiento)
registrar_rutas_respaldos(app, login_required, registrar_movimiento)
registrar_rutas_movimientos_mobile(app, login_required, roles_required)
registrar_rutas_maquinaria_mobile(app, login_required)
registrar_rutas_accesorios(app, login_required)
registrar_rutas_contenido(
    app,
    login_required,
    roles_required,
    registrar_movimiento,
)
registrar_rutas_autenticacion(
    app,
    login_required,
    registrar_movimiento,
    es_url_interna,
)
registrar_rutas_perfil(
    app,
    login_required,
    registrar_movimiento,
    es_dispositivo_movil,
)
registrar_rutas_inicio(app, login_required, es_dispositivo_movil)

if __name__ == "__main__":

    app.run(debug=True)
