from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    session,
    flash,
    make_response,
)

from utils.responsive import render_responsive


from user_agents import parse

from flask import redirect, url_for, abort
import re

from database import documentos
from flask import send_from_directory


from flask import jsonify
from respaldos import BASE_DIR, crear_respaldo

import os
import secrets
import warnings
from urllib.parse import urljoin, urlparse

from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import text
from database.conexion import engine

from functools import wraps
from datetime import date, datetime, timedelta


from models.auditoria_model import (
    registrar_movimiento,
    obtener_historial,
    obtener_historial_activo,
    registrar_activo_reciente,
    obtener_activos_recientes,
)

from database.documentos import (
    listar_documentos,
)

from database.solicitudes_baja import (
    obtener_pendientes,
    existe_solicitud_pendiente,
    obtener_traslado_en_proceso,
)

import pandas as pd

# ==========================================
# BASE DE DATOS
# ==========================================

from database.usuarios import (
    obtener_usuario,
    obtener_usuario_id,
    actualizar_password,
    verificar_password,
    actualizar_perfil,
)

from routes.usuarios import registrar_rutas_usuarios
from routes.actividad import registrar_rutas_actividad
from routes.dashboard import registrar_rutas_dashboard
from routes.etiquetas import registrar_rutas_etiquetas
from routes.maquinaria import registrar_rutas_maquinaria
from routes.solicitudes import registrar_rutas_solicitudes
from routes.aduanas import registrar_rutas_aduanas
from routes.documentos import registrar_rutas_documentos
from routes.evidencias import registrar_rutas_evidencias

from database.maquinarias import buscar_activos, obtener_maquinarias_mobile

from database.maquinarias import (
    insertar_maquinaria,
    siguiente_id_activo,
    actualizar_maquinaria,
    obtener_maquinarias,
    obtener_maquinaria,
    baja_desde_solicitud,
    obtener_maquinaria_detalle,
    obtener_activos_vecinos,
    obtener_ubicaciones,
    finalizar_mantenimiento,
    confirmar_recepcion_activo,
    finalizar_mantenimiento_activo,
    obtener_mantenimiento_en_proceso,
    obtener_maquinarias_mobile_filtrado,
    obtener_ubicaciones,
    obtener_contenido_activo,
    vincular_contenido_activo,
    retirar_contenido_activo,
    iniciar_revision_contenido,
    finalizar_revision_contenido,
    obtener_categorias_accesorios,
    actualizar_categoria_accesorio,
    asignar_accesorio_maquinaria,
    liberar_accesorio_maquinaria,
    obtener_asignacion_activa_accesorio,
    obtener_accesorios_asignados_maquinaria,
    obtener_historial_asignaciones_accesorio,
    crear_categoria_y_clasificar_accesorio,
    buscar_maquinarias_asignables,
    reabrir_revision_contenido,

)

from database.aduanas import (
    obtener_aduana,
    crear_registro_aduana_vacio,
    actualizar_aduana,
    estado_expediente_aduanal,
)

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


def abrir_activo(id_activo):

    if es_dispositivo_movil():

        return redirect(url_for("maquinaria_qr", id_activo=id_activo))

    return redirect(url_for("expediente_maquinaria", id_activo=id_activo))


@app.route("/prueba")
@app.route("/prueba")
def prueba():

    user_agent = request.headers.get("User-Agent")

    return f"""
    <h2>{user_agent}</h2>
    <hr>
    {'CELULAR' if es_dispositivo_movil() else 'COMPUTADORA'}
    """


from functools import wraps
from flask import session, request, redirect, url_for


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
# INICIO
# ==========================================================
@app.route("/")
@login_required
def inicio():

    if es_dispositivo_movil():
        return render_template("maquinaria_qr/index.html")

    return render_template("index.html")
# ==========================================================
# LOGIN
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_id" in session:

        if session.get("debe_cambiar_password", False):
            return redirect(
                url_for("cambiar_password_obligatorio")
            )

        next_page = session.pop("next_url", None)

        if es_url_interna(next_page):
            return redirect(next_page)

        return redirect(url_for("inicio"))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        datos = obtener_usuario(usuario)

        if datos and verificar_password(
            password,
            datos.password
        ):
            next_page = session.get("next_url")

            session.clear()
            session.permanent = True

            session["usuario_id"] = datos.id
            session["nombre"] = datos.nombre
            session["usuario"] = datos.usuario
            session["rol"] = datos.rol
            session["avatar"] = datos.avatar or "usuario"

            session["debe_cambiar_password"] = bool(
                datos.debe_cambiar_password
            )

            registrar_movimiento(
                usuario=session["nombre"],
                accion="Inició sesión",
                modulo="Login"
            )

            if session["debe_cambiar_password"]:
                flash(
                    "Debes crear una contraseña nueva para continuar.",
                    "warning"
                )

                return redirect(
                    url_for("cambiar_password_obligatorio")
                )

            flash(
                f"Bienvenido {datos.nombre}",
                "success"
            )

            if es_url_interna(next_page):
                return redirect(next_page)

            return redirect(url_for("inicio"))

        flash(
            "Usuario o contraseña incorrectos.",
            "danger"
        )

    return render_template("login.html")


# ==========================================================
# CAMBIO OBLIGATORIO DE CONTRASEÑA
# ==========================================================

@app.route(
    "/cambiar-password-obligatorio",
    methods=["GET", "POST"]
)
def cambiar_password_obligatorio():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if not session.get(
        "debe_cambiar_password",
        False
    ):
        return redirect(url_for("inicio"))

    usuario_actual = obtener_usuario_id(
        session["usuario_id"]
    )

    if not usuario_actual:
        session.clear()

        flash(
            "No fue posible encontrar tu cuenta.",
            "danger"
        )

        return redirect(url_for("login"))

    if request.method == "POST":
        password_nuevo = request.form.get(
            "password_nuevo",
            ""
        )

        confirmar_password = request.form.get(
            "confirmar_password",
            ""
        )

        if len(password_nuevo) < 10:
            flash(
                "La contraseña debe tener al menos "
                "10 caracteres.",
                "danger"
            )

            return render_template(
                "cambiar_password_obligatorio.html"
            )

        if password_nuevo != confirmar_password:
            flash(
                "Las contraseñas no coinciden.",
                "danger"
            )

            return render_template(
                "cambiar_password_obligatorio.html"
            )

        # Impide conservar la contraseña temporal
        if verificar_password(
            password_nuevo,
            usuario_actual["password"]
        ):
            flash(
                "La nueva contraseña debe ser diferente "
                "a la contraseña temporal.",
                "danger"
            )

            return render_template(
                "cambiar_password_obligatorio.html"
            )

        try:
            actualizar_password(
                session["usuario_id"],
                password_nuevo
            )

        except ValueError as error:
            flash(
                str(error),
                "danger"
            )

            return render_template(
                "cambiar_password_obligatorio.html"
            )

        session["debe_cambiar_password"] = False
        session.modified = True

        registrar_movimiento(
            usuario=session["nombre"],
            accion=(
                "Cambió la contraseña temporal "
                "por una contraseña personal"
            ),
            modulo="Seguridad",
            referencia=str(
                session["usuario_id"]
            )
        )

        flash(
            "Tu contraseña fue actualizada correctamente.",
            "success"
        )

        return redirect(url_for("inicio"))

    return render_template(
        "cambiar_password_obligatorio.html"
    )

@app.before_request
def verificar_cambio_password_obligatorio():
    rutas_libres = {
        "static",
        "login",
        "logout",
        "cambiar_password_obligatorio",
    }

    if request.endpoint in rutas_libres:
        return None

    if "usuario_id" not in session:
        return None

    usuario_actual = obtener_usuario_id(
        session["usuario_id"]
    )

    if not usuario_actual or not usuario_actual.activo:
        session.clear()

        flash(
            "Tu cuenta ya no está disponible.",
            "warning"
        )

        return redirect(url_for("login"))

    debe_cambiar = bool(
        usuario_actual.debe_cambiar_password
    )

    session["debe_cambiar_password"] = debe_cambiar

    if debe_cambiar:
        return redirect(
            url_for("cambiar_password_obligatorio")
        )

    return None
# ==========================================================
# LOGOUT
# ==========================================================


@app.route("/logout")
@login_required
def logout():

    registrar_movimiento(
        usuario=session["nombre"], accion="Cerró sesión", modulo="Login"
    )

    session.clear()

    flash("Sesión cerrada correctamente.", "info")

    return redirect(url_for("login"))


# ==========================================================
# PERFIL
# ==========================================================

@app.route("/perfil")
@login_required
def perfil():

    usuario_actual = obtener_usuario_id(
        session["usuario_id"]
    )

    if not usuario_actual:

        session.clear()

        flash(
            "No fue posible encontrar tu cuenta.",
            "danger"
        )

        return redirect(url_for("login"))

    avatar_actual = next(
        (
            avatar
            for avatar in AVATARES_PERFIL
            if avatar["id"] == (
                usuario_actual["avatar"]
                or "usuario"
            )
        ),
        AVATARES_PERFIL[0]
    )

    if es_dispositivo_movil():

        return render_template(
            "maquinaria_qr/perfil_mobile.html",
            usuario=usuario_actual,
            avatar_actual=avatar_actual,
            pagina="perfil"
        )

    return render_template(
        "perfil.html",
        usuario=usuario_actual,
        avatar_actual=avatar_actual
    )


# ==========================================================
# EDITAR PERFIL
# ==========================================================

AVATARES_PERFIL = [
    {
        "id": "usuario",
        "nombre": "Clásico",
        "icono": "bi-person-fill",
        "clase": "avatar-verde"
    },
    {
        "id": "finanzas",
        "nombre": "Finanzas",
        "icono": "bi-graph-up-arrow",
        "clase": "avatar-azul"
    },
    {
        "id": "mantenimiento",
        "nombre": "Mantenimiento",
        "icono": "bi-tools",
        "clase": "avatar-naranja"
    },
    {
        "id": "administracion",
        "nombre": "Administración",
        "icono": "bi-briefcase-fill",
        "clase": "avatar-morado"
    },
    {
        "id": "seguridad",
        "nombre": "Seguridad",
        "icono": "bi-shield-check",
        "clase": "avatar-rojo"
    },
    {
        "id": "inventario",
        "nombre": "Inventario",
        "icono": "bi-box-seam-fill",
        "clase": "avatar-turquesa"
    },
    {
        "id": "logistica",
        "nombre": "Logística",
        "icono": "bi-truck",
        "clase": "avatar-amarillo"
    },
    {
        "id": "ejecutivo",
        "nombre": "Ejecutivo",
        "icono": "bi-person-badge-fill",
        "clase": "avatar-oscuro"
    }
]

@app.route("/perfil/editar", methods=["GET", "POST"])
@login_required
def editar_perfil():

    usuario_actual = obtener_usuario_id(
        session["usuario_id"]
    )

    if not usuario_actual:

        session.clear()

        flash(
            "No fue posible encontrar tu cuenta.",
            "danger"
        )

        return redirect(url_for("login"))

    def mostrar_formulario():

        plantilla_base = (
            "maquinaria_qr/base_mobile.html"
            if es_dispositivo_movil()
            else "base.html"
        )

        return render_template(
            "editar_perfil.html",
            usuario=usuario_actual,
            avatares=AVATARES_PERFIL,
            plantilla_base=plantilla_base
        )

    if request.method == "POST":

        nombre = (
            request.form.get("nombre") or ""
        ).strip()

        avatar = (
            request.form.get("avatar") or "usuario"
        ).strip().lower()

        password_actual = (
            request.form.get("password_actual") or ""
        )

        password_nuevo = (
            request.form.get("password_nuevo") or ""
        )

        confirmar_password = (
            request.form.get("confirmar_password") or ""
        )

        if not nombre:

            flash(
                "El nombre es obligatorio.",
                "warning"
            )

            return mostrar_formulario()

        if len(nombre) > 150:

            flash(
                "El nombre es demasiado largo.",
                "warning"
            )

            return mostrar_formulario()

        if not verificar_password(
            password_actual,
            usuario_actual["password"]
        ):

            flash(
                "La contraseña actual no es correcta.",
                "danger"
            )

            return mostrar_formulario()

        if password_nuevo:

            if len(password_nuevo) < 10:

                flash(
                    "La contraseña nueva debe tener "
                    "al menos 10 caracteres.",
                    "warning"
                )

                return mostrar_formulario()

            if password_nuevo != confirmar_password:

                flash(
                    "Las contraseñas nuevas no coinciden.",
                    "warning"
                )

                return mostrar_formulario()

        try:

            actualizar_perfil(
                id_usuario=session["usuario_id"],
                nombre=nombre,
                avatar=avatar
            )

            if password_nuevo:

                actualizar_password(
                    session["usuario_id"],
                    password_nuevo
                )

        except ValueError as error:

            flash(
                str(error),
                "warning"
            )

            return mostrar_formulario()

        except Exception as error:

            print(
                "ERROR ACTUALIZANDO PERFIL:",
                error
            )

            flash(
                "No fue posible actualizar el perfil.",
                "danger"
            )

            return mostrar_formulario()

        session["nombre"] = nombre
        session["avatar"] = avatar

        registrar_movimiento(
            usuario=nombre,
            accion="Actualizó su perfil",
            modulo="Usuarios",
            referencia=str(session["usuario_id"])
        )

        flash(
            "Tu perfil fue actualizado correctamente.",
            "success"
        )

        return redirect(url_for("perfil"))

    return mostrar_formulario()


def redirigir_despues_de_contenido(id_activo):

    if request.form.get("origen") == "qr":
        return redirect(url_for("qr_contenido", id_activo=id_activo))

    return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

def redirigir_despues_de_gestionar_accesorio(id_accesorio):

    retorno_id = (
        request.form.get("retorno_id")
        or id_accesorio
    ).strip().upper()

    origen = request.form.get("origen")
    retorno_vista = request.form.get("retorno_vista")

    if origen == "qr":

        if retorno_vista == "contenido":
            return redirect(
                url_for(
                    "qr_contenido",
                    id_activo=retorno_id
                )
            )

        return redirect(
            url_for(
                "maquinaria_qr",
                id_activo=retorno_id
            )
        )

    return redirect(
        url_for(
            "expediente_maquinaria",
            id_activo=retorno_id
        )
    )


def usuario_puede_gestionar_accesorios():

    return session.get("rol") in [
        "Administrador",
        "Mantenimiento"
    ]


@app.route(
    "/accesorios/<id_accesorio>/categoria",
    methods=["POST"]
)
@login_required
def actualizar_categoria_accesorio_route(id_accesorio):

    if not usuario_puede_gestionar_accesorios():

        flash(
            "No tiene permisos para clasificar accesorios.",
            "danger"
        )

        return redirigir_despues_de_gestionar_accesorio(
            id_accesorio
        )

    categoria_id = request.form.get(
        "categoria_accesorio_id"
    )

    try:

        categoria = actualizar_categoria_accesorio(
            id_activo=id_accesorio,
            categoria_accesorio_id=categoria_id,
            usuario=session["nombre"]
        )

    except ValueError as error:

        flash(str(error), "warning")

    except Exception as error:

        print(
            "ERROR ACTUALIZANDO CATEGORÍA "
            "DEL ACCESORIO:",
            error
        )

        flash(
            "No fue posible actualizar la categoría.",
            "danger"
        )

    else:

        flash(
            f"{id_accesorio} fue clasificado como "
            f"{categoria['nombre']}.",
            "success"
        )

    return redirigir_despues_de_gestionar_accesorio(
        id_accesorio
    )


@app.route(
    "/accesorios/<id_accesorio>/asignacion",
    methods=["POST"]
)
@login_required
def asignar_accesorio_maquinaria_route(id_accesorio):

    if not usuario_puede_gestionar_accesorios():

        flash(
            "No tiene permisos para asignar accesorios.",
            "danger"
        )

        return redirigir_despues_de_gestionar_accesorio(
            id_accesorio
        )

    id_maquinaria = request.form.get("id_maquinaria")
    observaciones = request.form.get("observaciones")

    try:

        resultado = asignar_accesorio_maquinaria(
            id_accesorio=id_accesorio,
            id_maquinaria=id_maquinaria,
            usuario=session["nombre"],
            observaciones=observaciones
        )

    except ValueError as error:

        flash(str(error), "warning")

    except Exception as error:

        print(
            "ERROR ASIGNANDO ACCESORIO:",
            error
        )

        flash(
            "No fue posible guardar la asignación.",
            "danger"
        )

    else:

        if resultado["maquinaria_anterior"]:

            flash(
                f"{id_accesorio} cambió de "
                f"{resultado['maquinaria_anterior']} a "
                f"{resultado['id_maquinaria']}.",
                "success"
            )

        else:

            flash(
                f"{id_accesorio} fue asignado a "
                f"{resultado['id_maquinaria']}.",
                "success"
            )

    return redirigir_despues_de_gestionar_accesorio(
        id_accesorio
    )

@app.route(
    "/maquinarias/<id_activo>/revision-contenido/reabrir",
    methods=["POST"]
)
@login_required
def reabrir_revision_contenido_route(id_activo):

    if session.get("rol") not in [
        "Administrador",
        "Mantenimiento"
    ]:

        flash(
            "No tiene permisos para iniciar una nueva revisión.",
            "danger"
        )

        return redirigir_despues_de_contenido(id_activo)

    try:

        reabrir_revision_contenido(
            id_activo=id_activo,
            usuario=session["nombre"]
        )

    except ValueError as error:

        flash(str(error), "warning")

    except Exception as error:

        print(
            "ERROR REABRIENDO REVISIÓN:",
            error
        )

        flash(
            "No fue posible iniciar una nueva revisión.",
            "danger"
        )

    else:

        flash(
            "Se inició una nueva revisión de contenido.",
            "success"
        )

    return redirigir_despues_de_contenido(id_activo)


@app.route(
    "/accesorios/<id_accesorio>/asignacion/liberar",
    methods=["POST"]
)
@login_required
def liberar_accesorio_maquinaria_route(id_accesorio):

    if not usuario_puede_gestionar_accesorios():

        flash(
            "No tiene permisos para liberar accesorios.",
            "danger"
        )

        return redirigir_despues_de_gestionar_accesorio(
            id_accesorio
        )

    try:

        id_maquinaria = liberar_accesorio_maquinaria(
            id_accesorio=id_accesorio,
            usuario=session["nombre"]
        )

    except ValueError as error:

        flash(str(error), "warning")

    except Exception as error:

        print(
            "ERROR LIBERANDO ACCESORIO:",
            error
        )

        flash(
            "No fue posible liberar el accesorio.",
            "danger"
        )

    else:

        flash(
            f"{id_accesorio} fue liberado de "
            f"{id_maquinaria}.",
            "success"
        )

    return redirigir_despues_de_gestionar_accesorio(
        id_accesorio
    )


@app.route("/maquinarias/<id_activo>/revision-contenido/iniciar", methods=["POST"])
@login_required
@roles_required("Administrador", "Mantenimiento")
def iniciar_revision_contenido_route(id_activo):

    try:
        iniciar_revision_contenido(id_activo, session["nombre"])
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash("La revisión de contenido fue iniciada correctamente.", "success")

    return redirigir_despues_de_contenido(id_activo)


@app.route("/maquinarias/<id_activo>/revision-contenido/finalizar", methods=["POST"])
@login_required
@roles_required("Administrador", "Mantenimiento")
def finalizar_revision_contenido_route(id_activo):

    try:
        finalizar_revision_contenido(id_activo, session["nombre"])
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash("La revisión de contenido fue finalizada correctamente.", "success")

    return redirigir_despues_de_contenido(id_activo)


# app.errorhandler(404)
# def pagina_no_encontrada(error):
#     return render_template("error.html"), 404

# @app.errorhandler(500)
# def error_servidor(error):
#     return render_template("error.html"), 500

# @app.errorhandler(Exception)
# def error_general(error):
#     return render_template("error.html"), 500

# ==========================================
# HISTORIAL DE UN ACTIVO
# ==========================================


def obtener_historial_activo(id_activo):

    sql = text("""

        SELECT

            fecha,
            usuario,
            accion,
            modulo

        FROM auditoria

        WHERE referencia = :id

        ORDER BY fecha DESC

    """)

    with engine.connect() as conn:

        return conn.execute(sql, {"id": id_activo}).mappings().all()


@app.route("/buscar-activos")
@login_required
def buscar_activos_ajax():

    texto = request.args.get("q", "").strip()

    if len(texto) < 2:
        return jsonify([])

    activos = buscar_activos(texto)

    return jsonify(
        [
            {
                "id": a["id_activo"],
                "text": a["id_activo"],
                "descripcion": a["descripcion"],
                "categoria": a["categoria"],
                "marca": a["marca"],
                "ubicacion": a["ubicacion"],
            }
            for a in activos
        ]
    )

@app.route("/buscar-maquinarias-asignables")
@login_required
def buscar_maquinarias_asignables_ajax():

    if not usuario_puede_gestionar_accesorios():
        return jsonify([]), 403

    texto = request.args.get("q", "").strip()

    id_accesorio = request.args.get(
        "id_accesorio",
        ""
    ).strip().upper()

    if len(texto) < 2:
        return jsonify([])

    maquinarias = buscar_maquinarias_asignables(
        texto=texto,
        id_accesorio=id_accesorio
    )

    return jsonify(
        [
            {
                "id": maquinaria["id_activo"],
                "descripcion": maquinaria["descripcion"],
                "categoria": maquinaria["categoria"],
                "marca": maquinaria["marca"],
                "modelo": maquinaria["modelo"],
                "serie": maquinaria["numero_serie"],
                "ubicacion": maquinaria["ubicacion"],
            }
            for maquinaria in maquinarias
        ]
    )

@app.route(
    "/accesorios/<id_accesorio>/categoria/crear",
    methods=["POST"]
)
@login_required
def crear_categoria_accesorio_route(id_accesorio):

    if not usuario_puede_gestionar_accesorios():

        flash(
            "No tiene permisos para crear categorías.",
            "danger"
        )

        return redirigir_despues_de_gestionar_accesorio(
            id_accesorio
        )

    nombre = request.form.get("nombre_categoria")
    descripcion = request.form.get(
        "descripcion_categoria"
    )

    try:

        categoria = (
            crear_categoria_y_clasificar_accesorio(
                id_activo=id_accesorio,
                nombre=nombre,
                descripcion=descripcion,
                usuario=session["nombre"]
            )
        )

    except ValueError as error:

        flash(str(error), "warning")

    except Exception as error:

        print(
            "ERROR CREANDO CATEGORÍA DE ACCESORIO:",
            error
        )

        flash(
            "No fue posible crear la categoría.",
            "danger"
        )

    else:

        flash(
            f"Se creó la categoría "
            f"{categoria['nombre']} y se asignó a "
            f"{id_accesorio}.",
            "success"
        )

    return redirigir_despues_de_gestionar_accesorio(
        id_accesorio
    )


@app.route("/respaldos")
@login_required
def vista_respaldos():
    if session.get("rol") != "Administrador":

        flash("No tiene permisos para eliminar documentos.", "danger")

        return redirect(request.referrer or url_for("lista_maquinarias"))

    carpeta = os.path.join(app.root_path, "backups")

    respaldos = []

    if os.path.exists(carpeta):

        for archivo in os.listdir(carpeta):

            if archivo.endswith(".sql"):

                ruta = os.path.join(carpeta, archivo)

                tamano = os.path.getsize(ruta)

                fecha_modificacion = os.path.getmtime(ruta)

                fecha = datetime.fromtimestamp(fecha_modificacion).strftime(
                    "%d/%m/%Y %H:%M"
                )

                respaldos.append(
                    {
                        "archivo": archivo,
                        "fecha": fecha,
                        "tamano": round(tamano / 1024, 2),
                    }
                )

    # Ordenar por fecha de modificación (más reciente primero)
    respaldos.sort(
        key=lambda x: datetime.strptime(x["fecha"], "%d/%m/%Y %H:%M"), reverse=True
    )

    # ===========================
    # KPIs
    # ===========================

    total_respaldos = len(respaldos)

    espacio_total = round(sum(r["tamano"] for r in respaldos), 2)

    ultimo = respaldos[0] if respaldos else None

    return render_template(
        "respaldos.html",
        respaldos=respaldos,
        total_respaldos=total_respaldos,
        espacio_total=espacio_total,
        ultimo=ultimo,
    )


@app.route("/respaldos/crear", methods=["POST"])
@login_required
def crear_respaldo_ajax():

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para eliminar documentos.", "danger")

        return redirect(request.referrer or url_for("lista_maquinarias"))

    try:

        archivo = crear_respaldo()

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Generó respaldo: {archivo}",
            modulo="Respaldos",
        )

        return jsonify({"ok": True, "archivo": archivo})

    except Exception as e:

        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/respaldos/descargar/<nombre>")
@login_required
def descargar_respaldo(nombre):
    if session.get("rol") != "Administrador":

        flash("No tiene permisos para eliminar documentos.", "danger")

        return redirect(request.referrer or url_for("lista_maquinarias"))

    carpeta = os.path.join(app.root_path, "backups")

    return send_from_directory(carpeta, nombre, as_attachment=True)


@app.route("/respaldos/eliminar/<nombre>", methods=["POST"])
@login_required
def eliminar_respaldo(nombre):

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para eliminar documentos.", "danger")

        return redirect(request.referrer or url_for("lista_maquinarias"))

    ruta = os.path.join(app.root_path, "backups", nombre)

    if os.path.exists(ruta):

        os.remove(ruta)

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Eliminó respaldo: {nombre}",
            modulo="Respaldos",
        )

        return jsonify({"ok": True})

    return jsonify({"ok": False}), 404


@app.route("/maquinarias/<id_activo>/confirmar-recepcion", methods=["POST"])
@login_required
def confirmar_recepcion_route(id_activo):

    origen = request.form.get("origen")

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para realizar esta acción.", "danger")

        if origen == "qr":
            return redirect(url_for("maquinaria_qr", id_activo=id_activo))

        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    confirmar_recepcion_activo(id_activo, session["nombre"])

    flash("La maquinaria fue recibida correctamente.", "success")

    if origen == "qr":
        return redirect(url_for("maquinaria_qr", id_activo=id_activo))

    return redirect(url_for("expediente_maquinaria", id_activo=id_activo))


@app.route("/maquinarias/<id_activo>/finalizar-mantenimiento", methods=["POST"])
@login_required
def finalizar_mantenimiento_route(id_activo):

    origen = request.form.get("origen")

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para realizar esta acción.", "danger")

        if origen == "qr":
            return redirect(url_for("maquinaria_qr", id_activo=id_activo))

        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    finalizar_mantenimiento_activo(id_activo, session["nombre"])

    flash("El mantenimiento fue finalizado correctamente.", "success")

    if origen == "qr":
        return redirect(url_for("maquinaria_qr", id_activo=id_activo))

    return redirect(url_for("expediente_maquinaria", id_activo=id_activo))


@app.route("/<id_activo>")
@login_required
def redireccion_qr_antiguo(id_activo):

    if not id_activo.startswith("ACT-"):
        abort(404)

    return redirect(url_for("expediente_maquinaria", id_activo=id_activo))


@app.route("/maquina/<id_activo>")
@login_required
def redireccion_qr_maquina(id_activo):

    return redirect(url_for("expediente_maquinaria", id_activo=id_activo), code=301)


@app.route("/qr/<id_activo>")
@login_required
def maquinaria_qr(id_activo):

    maquinaria = obtener_maquinaria(id_activo)

    if not maquinaria:
        abort(404)

    # ==========================================
    # Guardar activo reciente
    # ==========================================

    registrar_activo_reciente(
        usuario=session["nombre"],
        id_activo=id_activo,
    )

    # ==========================================
    # Información general
    # ==========================================

    aduana = obtener_aduana(id_activo)

    estado = estado_expediente_aduanal(aduana)

    traslado_en_proceso = (
        obtener_traslado_en_proceso(id_activo)
    )

    mantenimiento_en_proceso = (
        obtener_mantenimiento_en_proceso(id_activo)
    )

    # ==========================================
    # Contenido y gestión de accesorios
    # ==========================================

    contenido_activo = []

    es_contenedor = bool(
        maquinaria.get("es_contenedor")
    )

    es_accesorio = (
        not es_contenedor
        and
        (maquinaria.get("categoria") or "")
        .strip()
        .upper()
        == "ACCESORIO"
    )

    categorias_accesorios = []
    asignacion_activa = None
    historial_asignaciones = []
    accesorios_asignados = []

    # Obtener contenido cuando el activo sea contenedor
    if es_contenedor:
        contenido_activo = (
            obtener_contenido_activo(id_activo)
        )

    # Obtener catálogo de categorías
    if es_contenedor or es_accesorio:
        categorias_accesorios = (
            obtener_categorias_accesorios()
        )

    # Obtener la asignación y el historial del accesorio
    if es_accesorio:
        asignacion_activa = (
            obtener_asignacion_activa_accesorio(
                id_activo
            )
        )

        historial_asignaciones = (
            obtener_historial_asignaciones_accesorio(
                id_activo
            )
        )

    # Obtener accesorios asignados a una maquinaria
    elif not es_contenedor:
        accesorios_asignados = (
            obtener_accesorios_asignados_maquinaria(
                id_activo
            )
        )

    # ==========================================
    # Estado visual
    # ==========================================

    estado_ui = {
        "ACTIVO": {
            "clase": "activo",
            "icono": "bi-check-circle-fill",
        },
        "BAJA": {
            "clase": "baja",
            "icono": "bi-x-circle-fill",
        },
        "MANTENIMIENTO": {
            "clase": "mantenimiento",
            "icono": "bi-tools",
        },
        "EN TRASLADO": {
            "clase": "traslado",
            "icono": "bi-truck",
        },
    }.get(
        maquinaria["estado"],
        {
            "clase": "activo",
            "icono": "bi-circle-fill",
        },
    )

    # ==========================================
    # Render
    # ==========================================

    return render_template(
        "maquinaria_qr/inicio.html",
        maquinaria=maquinaria,
        aduana=aduana,
        estado=estado,
        traslado_en_proceso=traslado_en_proceso,
        mantenimiento_en_proceso=mantenimiento_en_proceso,
        contenido_activo=contenido_activo,
        estado_ui=estado_ui,
        id_activo=id_activo,
        pagina="inicio",
        es_contenedor=es_contenedor,
        es_accesorio=es_accesorio,
        categorias_accesorios=categorias_accesorios,
        asignacion_activa=asignacion_activa,
        historial_asignaciones=historial_asignaciones,
        accesorios_asignados=accesorios_asignados,
    )


@app.route("/qr/<id_activo>/contenido")
@login_required
def qr_contenido(id_activo):

    maquinaria = obtener_maquinaria(id_activo)

    if not maquinaria:
        abort(404)

    if maquinaria.get("es_contenedor") != 1:
        flash("Este activo no está marcado como contenedor.", "warning")
        return redirect(url_for("maquinaria_qr", id_activo=id_activo))

    contenido_activo = obtener_contenido_activo(id_activo)
    
    categorias_accesorios = (
        obtener_categorias_accesorios()
    )

    return render_template(
        "maquinaria_qr/contenido.html",
        maquinaria=maquinaria,
        contenido_activo=contenido_activo,
        categorias_accesorios=categorias_accesorios,
        id_activo=id_activo,
        pagina="contenido",
    )


@app.route("/qr/<id_activo>/expediente")
@login_required
def qr_expediente(id_activo):

    maquinaria = obtener_maquinaria(id_activo)

    aduana = obtener_aduana(id_activo)

    estado = estado_expediente_aduanal(aduana)

    documentos = listar_documentos(id_activo)

    documentos_map = {}

    for doc in documentos:
        documentos_map[doc["tipo"]] = doc

    return render_template(
        "maquinaria_qr/expediente.html",
        maquinaria=maquinaria,
        aduana=aduana,
        estado=estado,
        documentos_map=documentos_map,
        pagina="expediente",
        id_activo=id_activo,
    )


@app.route("/m/maquinarias/<id_activo>/movimiento/<tipo>")
@login_required
@roles_required("Administrador", "Mantenimiento")
def formulario_movimiento_mobile(id_activo, tipo):

    maquina = obtener_maquinaria(id_activo)

    if not maquina:
        flash("Activo no encontrado.", "danger")
        return redirect(url_for("dashboard_mobil"))

    titulos = {
        "TRASLADO": "Solicitud de Traslado",
        "MANTENIMIENTO": "Solicitud de Mantenimiento",
        "BAJA": "Solicitud de Baja",
        "REINCORPORACION": "Solicitud de Reactivación",
    }

    if tipo not in titulos:
        abort(404)

    return render_template(
        "maquinaria_qr/formulario_movimiento.html",
        maquina=maquina,
        tipo=tipo,
        titulo=titulos[tipo],
        id_activo=id_activo,
        pagina="movimientos",
    )


@app.route("/m/maquinarias/<id_activo>/movimientos")
@login_required
@roles_required("Administrador", "Mantenimiento")
def movimientos_mobile(id_activo):

    maquina = obtener_maquinaria(id_activo)

    if not maquina:
        flash("Activo no encontrado.", "danger")
        return redirect(url_for("dashboard_mobil"))

    traslado_en_proceso = obtener_traslado_en_proceso(id_activo)

    mantenimiento_en_proceso = obtener_mantenimiento_en_proceso(id_activo)

    solicitud_pendiente = existe_solicitud_pendiente(id_activo)

    return render_template(
        "maquinaria_qr/movimientos_mobile.html",
        maquina=maquina,
        traslado_en_proceso=traslado_en_proceso,
        mantenimiento_en_proceso=mantenimiento_en_proceso,
        solicitud_pendiente=solicitud_pendiente,
        id_activo=id_activo,
        pagina="movimientos",
    )


@app.route("/m/maquinarias/<id_activo>/actividad")
@login_required
def actividad_mobile(id_activo):

    maquinaria = obtener_maquinaria(id_activo)

    if not maquinaria:

        flash("Activo no encontrado.", "danger")
        return redirect(url_for("dashboard_mobil"))

    historial = obtener_historial_activo(id_activo)

    historial_procesado = []

    for evento in historial:

        nuevo = dict(evento)

        accion = nuevo["accion"].upper()

        # ===========================
        # ICONO Y COLOR
        # ===========================

        if "REINCORPORACION" in accion:

            nuevo["icono"] = "bi-arrow-clockwise"
            nuevo["color"] = "success"

        elif "BAJA" in accion:

            nuevo["icono"] = "bi-trash-fill"
            nuevo["color"] = "danger"

        elif "DOCUMENTO" in accion:

            nuevo["icono"] = "bi-file-earmark-text-fill"
            nuevo["color"] = "primary"

        elif "TRASLADO" in accion:

            nuevo["icono"] = "bi-truck"
            nuevo["color"] = "info"

        elif "MANTENIMIENTO" in accion:

            nuevo["icono"] = "bi-tools"
            nuevo["color"] = "warning"

        elif "ADUANA" in accion or "PEDIMENTO" in accion:

            nuevo["icono"] = "bi-folder2-open"
            nuevo["color"] = "secondary"

        else:

            nuevo["icono"] = "bi-clock-history"
            nuevo["color"] = "dark"

        # ===========================
        # FORMATO DE FECHA
        # ===========================

        fecha = nuevo["fecha"]

        if isinstance(fecha, datetime):

            nuevo["fecha_formato"] = fecha.strftime("%d %b · %H:%M")

        else:

            nuevo["fecha_formato"] = str(fecha)

        historial_procesado.append(nuevo)

    return render_template(
        "maquinaria_qr/actividad_mobile.html",
        maquinaria=maquinaria,
        historial=historial_procesado,
        pagina="actividad",
        id_activo=id_activo,
    )

@app.route("/m/maquinarias/cargar")
@login_required
def cargar_maquinarias_mobile():

    offset = int(request.args.get("offset", 0))

    maquinarias = (
        obtener_maquinarias_mobile(limite=20, offset=offset)
        .fillna("")
        .to_dict("records")
    )

    for maquina in maquinarias:

        aduana = obtener_aduana(maquina["id_activo"])

        maquina["expediente"] = estado_expediente_aduanal(aduana)

    return jsonify(maquinarias)


@app.route("/m/maquinarias")
@login_required
def maquinarias_mobile():

    return render_template("maquinaria_qr/maquinarias_mobile.html")


@app.route("/m/maquinarias/api")
@login_required
def api_maquinarias_mobile():

    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    ubicacion = request.args.get("ubicacion", "")
    tipo = request.args.get("tipo", "")

    offset = int(request.args.get("offset", 0))
    limite = 20

    maquinarias = obtener_maquinarias_mobile_filtrado(
        q=q, estado=estado, ubicacion=ubicacion, tipo=tipo, limite=limite, offset=offset
    ).to_dict("records")

    for maquina in maquinarias:

        aduana = obtener_aduana(maquina["id_activo"])
        maquina["expediente"] = estado_expediente_aduanal(aduana)

        # Limpiar TODOS los campos de ESTA maquinaria
        for key, value in list(maquina.items()):

            try:
                if pd.isna(value):
                    maquina[key] = None
                    continue
            except TypeError:
                pass

            if isinstance(value, (datetime, date, pd.Timestamp)):
                maquina[key] = value.strftime("%Y-%m-%d %H:%M:%S")

    return jsonify(maquinarias)


@app.route("/m/maquinarias/ubicaciones")
@login_required
def api_ubicaciones_mobile():

    ubicaciones = obtener_ubicaciones()

    return jsonify(ubicaciones)


@app.route("/m/recientes")
@login_required
def api_activos_recientes():

    recientes = obtener_activos_recientes(session["nombre"])

    return jsonify(recientes)


@app.route(
    "/maquinarias/<id_activo>/contenido/vincular",
    methods=["POST"]
)
@login_required
@roles_required("Administrador", "Mantenimiento")
def vincular_contenido_route(id_activo):

    activo_relacionado = request.form.get(
        "activo_relacionado"
    )

    observaciones = request.form.get(
        "observaciones"
    )

    if not activo_relacionado:

        flash(
            "Debe seleccionar un activo.",
            "warning"
        )

        return redirigir_despues_de_contenido(id_activo)

    if activo_relacionado == id_activo:

        flash(
            "Un activo no puede contenerse a sí mismo.",
            "danger"
        )

        return redirigir_despues_de_contenido(id_activo)

    try:

        vincular_contenido_activo(
            activo_origen=id_activo,
            activo_relacionado=activo_relacionado,
            usuario=session["nombre"],
            observaciones=observaciones
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Vinculó el activo {activo_relacionado} como contenido",
            modulo="Accesorios",
            referencia=id_activo
        )

        flash(
            f"{activo_relacionado} fue agregado al contenido de {id_activo}.",
            "success"
        )

    except Exception as e:

        print("ERROR VINCULANDO CONTENIDO:", e)

        flash(
            "No fue posible vincular el activo. "
            "Verifique que no esté relacionado previamente.",
            "danger"
        )

    return redirigir_despues_de_contenido(id_activo)


@app.route(
    "/maquinarias/<id_activo>/contenido/<int:relacion_id>/retirar",
    methods=["POST"]
)
@login_required
@roles_required("Administrador", "Mantenimiento")
def retirar_contenido_route(id_activo, relacion_id):

    try:
        activo_retirado = retirar_contenido_activo(
            activo_origen=id_activo,
            relacion_id=relacion_id,
            usuario=session["nombre"]
        )
    except ValueError as error:
        flash(str(error), "warning")
    else:
        flash(
            f"{activo_retirado} fue retirado del contenido de {id_activo}.",
            "success"
        )

    return redirigir_despues_de_contenido(id_activo)

@app.route(
    "/maquinarias/<id_activo>/contenido/registrar",
    methods=["POST"]
)
@login_required
@roles_required("Administrador", "Mantenimiento")
def registrar_accesorio_desde_contenido(id_activo):

    nuevo_id = siguiente_id_activo()

    descripcion = (request.form.get("descripcion") or "").strip()
    marca = (request.form.get("marca") or "").strip()
    modelo = (request.form.get("modelo") or "").strip()
    numero_serie = (request.form.get("numero_serie") or "").strip()
    ubicacion = (request.form.get("ubicacion") or "").strip()
    observaciones = (request.form.get("observaciones") or "").strip()

    if not descripcion:
        flash("La descripción del accesorio es obligatoria.", "warning")
        return redirigir_despues_de_contenido(id_activo)

    # Si no escriben ubicación, heredamos la ubicación del activo origen
    activo_origen = obtener_maquinaria_detalle(id_activo)

    if not activo_origen:
        flash("El activo origen no existe.", "danger")
        return redirigir_despues_de_contenido(id_activo)

    if not ubicacion:
        ubicacion = activo_origen.get("ubicacion") or ""

    datos = {
        "id_activo": nuevo_id,
        "categoria": "ACCESORIO",
        "descripcion": descripcion,
        "cantidad": 1,
        "marca": marca,
        "modelo": modelo,
        "numero_serie": numero_serie,
        "serie_interna": "",
        "proveedor": "",
        "ubicacion": ubicacion,
        "precio_unitario_us": 0,
        "total_us": 0,
        "valor_mx": 0,
        "fecha_alta": None,
        "observaciones": observaciones,
    }

    try:

        insertar_maquinaria(datos)

        vincular_contenido_activo(
            activo_origen=id_activo,
            activo_relacionado=nuevo_id,
            usuario=session["nombre"],
            observaciones=f"Accesorio registrado desde {id_activo}. {observaciones}"
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Registró el accesorio {nuevo_id} desde {id_activo}",
            modulo="Accesorios",
            referencia=nuevo_id
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Vinculó {nuevo_id} como contenido",
            modulo="Accesorios",
            referencia=id_activo
        )

        flash(
            f"Accesorio {nuevo_id} registrado y vinculado correctamente.",
            "success"
        )

    except Exception as e:

        print("ERROR REGISTRANDO ACCESORIO:", e)

        flash(
            "No fue posible registrar el accesorio.",
            "danger"
        )

    return redirigir_despues_de_contenido(id_activo)


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

if __name__ == "__main__":

    app.run(debug=True)
