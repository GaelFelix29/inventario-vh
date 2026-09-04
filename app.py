from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from database.dashboard import obtener_kpis_dashboard, obtener_actividad_dashboard

from utils.responsive import render_responsive

from datetime import datetime


from user_agents import parse

from flask import redirect, url_for, abort
import re

from database import documentos
from supabase_config import supabase

from database.documentos import obtener_documento

from flask import send_from_directory


from flask import jsonify
from respaldos import BASE_DIR, crear_respaldo

import os
import secrets
import warnings
from datetime import timedelta
from urllib.parse import urljoin, urlparse
from datetime import datetime

from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import text
from database.conexion import engine

from functools import wraps
from datetime import date


from models.auditoria_model import (
    registrar_movimiento,
    obtener_historial,
    obtener_historial_activo,
    registrar_activo_reciente,
    obtener_activos_recientes,
)

from database.documentos import (
    RUTA_DOCUMENTOS,
    crear_carpeta_activo,
    guardar_documento_bd,
    listar_documentos,
    eliminar_documento,
)

from database.solicitudes_baja import (
    guardar_solicitud,
    obtener_solicitudes,
    obtener_solicitud,
    obtener_pendientes,
    aprobar_solicitud,
    rechazar_solicitud,
    existe_solicitud_pendiente,
    obtener_traslado_en_proceso,
)

import pandas as pd
import qrcode
import base64

from io import BytesIO

# ==========================================
# BASE DE DATOS
# ==========================================

from database.usuarios import (
    obtener_usuario,
    obtener_usuarios,
    crear_usuario,
    obtener_usuario_id,
    actualizar_usuario,
    actualizar_password,
    desactivar_usuario,
    reactivar_usuario,
    verificar_password,
)

from database.maquinarias import buscar_activos, obtener_maquinarias_mobile

from database.maquinarias import (
    obtener_todas_maquinas,
    insertar_maquinaria,
    siguiente_id_activo,
    actualizar_maquinaria,
    obtener_maquinarias,
    obtener_maquinaria,
    baja_desde_solicitud,
    obtener_maquinarias_select,
    obtener_maquinaria_detalle,
    obtener_activos_vecinos,
    obtener_estadisticas_maquinarias,
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
    obtener_aduanas,
    obtener_aduana,
    crear_registro_aduana_vacio,
    guardar_aduana,
    actualizar_aduana,
    estado_expediente_aduanal,
    obtener_origenes,
    obtener_aduanas_mobile_filtrado,
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

        next_page = session.pop("next_url", None)

        if es_url_interna(next_page):
            return redirect(next_page)

        return redirect(url_for("inicio"))

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        datos = obtener_usuario(usuario)

        if datos and verificar_password(password, datos.password):

            next_page = session.get("next_url")
            session.clear()
            session.permanent = True
            session["usuario_id"] = datos.id
            session["nombre"] = datos.nombre
            session["usuario"] = datos.usuario
            session["rol"] = datos.rol

            flash(f"Bienvenido {datos.nombre}", "success")

            registrar_movimiento(
                usuario=session["nombre"], accion="Inició sesión", modulo="Login"
            )

            if es_url_interna(next_page):
                return redirect(next_page)

            return redirect(url_for("inicio"))

        flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


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

    return render_template(
        "perfil.html",
        usuario={
            "id": session["usuario_id"],
            "nombre": session["nombre"],
            "usuario": session["usuario"],
            "rol": session["rol"],
        },
    )


# ==========================================================
# EDITAR PERFIL
# ==========================================================


@app.route("/perfil/editar", methods=["GET", "POST"])
@login_required
def editar_perfil():

    return render_template("editar_perfil.html")


# ==========================================================
# USUARIOS
# ==========================================================


@app.route("/usuarios")
@admin_required
def usuarios():

    lista = obtener_usuarios()

    return render_template("usuarios.html", usuarios=lista)


# ==========================================================
# NUEVO USUARIO
# ==========================================================


@app.route("/usuarios/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo_usuario():

    if request.method == "POST":

        if request.form["password"] != request.form["confirmar"]:

            flash("Las contraseñas no coinciden.", "danger")

            return redirect(url_for("nuevo_usuario"))

        crear_usuario(
            request.form["nombre"],
            request.form["usuario"],
            request.form["correo"],
            request.form["password"],
            request.form["rol"],
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Creó el usuario: {request.form['usuario']}",
            modulo="Usuarios",
            referencia=str(request.form["usuario"]),
        )

        flash("Usuario creado correctamente.", "success")

        return redirect(url_for("usuarios"))

    return render_template("nuevo_usuario.html")


# ==========================================================
# EDITAR USUARIO
# ==========================================================


@app.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
@admin_required
def editar_usuario(id):

    usuario = obtener_usuario_id(id)

    if not usuario:

        flash("Usuario no encontrado.", "danger")

        return redirect(url_for("usuarios"))

    if request.method == "POST":

        actualizar_usuario(
            id,
            request.form["nombre"],
            request.form["usuario"],
            request.form["correo"],
            request.form["rol"],
            int(request.form["activo"]),
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Actualizó el usuario: {request.form['usuario']}",
            modulo="Usuarios",
            referencia=str(id),
        )

        if request.form["password"] != "":

            actualizar_password(id, request.form["password"])

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Cambió la contraseña del usuario: {request.form['usuario']}",
            modulo="Usuarios",
            referencia=str(id),
        )

        flash("Usuario actualizado correctamente.", "success")

        return redirect(url_for("usuarios"))

    return render_template("editar_usuario.html", usuario=usuario)


# ==========================================================
# DESACTIVAR USUARIO
# ==========================================================


@app.route("/usuarios/desactivar/<int:id>")
@admin_required
def desactivar(id):

    desactivar_usuario(id)

    usuario = obtener_usuario_id(id)

    registrar_movimiento(
        usuario=session["nombre"],
        accion=f"Desactivó el usuario: {usuario.usuario}",
        modulo="Usuarios",
        referencia=str(id),
    )

    flash("Usuario desactivado correctamente.", "warning")

    return redirect(url_for("usuarios"))


# ==========================================================
# REACTIVAR USUARIO
# ==========================================================


@app.route("/usuarios/reactivar/<int:id>")
@admin_required
def reactivar_usuario_route(id):

    reactivar_usuario(id)

    usuario = obtener_usuario_id(id)

    registrar_movimiento(
        usuario=session["nombre"],
        accion=f"Reactivó el usuario: {usuario.usuario}",
        modulo="Usuarios",
        referencia=str(id),
    )

    flash("Usuario reactivado correctamente.", "success")

    return redirect(url_for("usuarios"))


# ==========================================================
# DASHBOARD
# ==========================================================


@app.route("/dashboard")
@login_required
def dashboard():

    return render_template("dashboard.html")


# ==========================================================
# DATOS DASHBOARD
# ==========================================================


@app.route("/dashboard/datos")
@login_required
def dashboard_datos():

    maq = obtener_maquinarias()
    aduana = obtener_aduanas()

    total = len(maq)

    bajas = (maq["estado"] == "BAJA").sum()

    activos = (maq["estado"] == "ACTIVO").sum()

    valor = maq["valor_mx"].fillna(0).sum()

    origen = aduana["origen"].fillna("SIN DATO").value_counts()

    documentacion = aduana["documentacion_completa"].fillna("NO").value_counts()

    top = maq["categoria"].fillna("SIN DATO").value_counts().head(10)

    valor_origen = (
        aduana.merge(maq[["id_activo", "valor_mx"]], on="id_activo", how="left")
        .groupby("origen")["valor_mx"]
        .sum()
    )

    return jsonify(
        {
            "kpi": {
                "total": int(total),
                "activos": int(activos),
                "bajas": int(bajas),
                "valor": float(valor),
            },
            "origen": {
                "labels": origen.index.tolist(),
                "values": origen.values.tolist(),
            },
            "documentacion": {
                "labels": documentacion.index.tolist(),
                "values": documentacion.values.tolist(),
            },
            "top": {"labels": top.index.tolist(), "values": top.values.tolist()},
            "valorOrigen": {
                "labels": valor_origen.index.tolist(),
                "values": valor_origen.values.tolist(),
            },
        }
    )


# ==========================================================
# IMPRIMIR QR
# ==========================================================


@app.route("/imprimir")
@login_required
def imprimir_qr():

    maquinas = obtener_maquinarias()

    return render_template("imprimir-qr.html", maquinas=maquinas.to_dict("records"))


# ==========================================================
# ETIQUETAS
# ==========================================================


@app.route("/etiquetas", methods=["POST"])
@login_required
def etiquetas():

    datos = request.get_json()

    codigos = datos["codigos"]

    maquinas = obtener_maquinarias()

    maquinas = maquinas[maquinas["id_activo"].isin(codigos)]

    etiquetas = []

    for _, fila in maquinas.iterrows():

        url = url_for(
            "expediente_maquinaria", id_activo=fila["id_activo"], _external=True
        )

        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=12,
            border=4,
        )

        qr.add_data(url)

        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()

        img.save(buffer, format="PNG")

        qr64 = base64.b64encode(buffer.getvalue()).decode()

        etiquetas.append(
            {
                "codigo": fila["id_activo"],
                "nombre": fila["descripcion"],
                "estado": "BAJA" if pd.notna(fila["fecha_baja"]) else "ACTIVO",
                "url": url,
                "qr": qr64,
            }
        )

    return render_template("etiquetas.html", etiquetas=etiquetas)


@app.route("/fichas", methods=["POST"])
@login_required
def fichas():

    datos = request.get_json()

    codigos = datos["codigos"]

    maquinas = obtener_maquinarias()

    maquinas = maquinas[maquinas["id_activo"].isin(codigos)]

    fichas = []

    for _, fila in maquinas.iterrows():

        url = url_for(
            "expediente_maquinaria", id_activo=fila["id_activo"], _external=True
        )

        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=12,
            border=4,
        )

        qr.add_data(url)

        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()

        img.save(buffer, format="PNG")

        qr64 = base64.b64encode(buffer.getvalue()).decode()

        fichas.append(
            {
                "codigo": fila["id_activo"],
                "nombre": fila["descripcion"],
                "marca": fila["marca"],
                "modelo": fila["modelo"],
                "serie": fila["numero_serie"],
                "estado": "BAJA" if pd.notna(fila["fecha_baja"]) else "ACTIVO",
                "url": url,
                "qr": qr64,
            }
        )

    return render_template("fichas.html", fichas=fichas)


@app.route("/maquinarias")
@login_required
def lista_maquinarias():

    maquinas = obtener_todas_maquinas()

    estadisticas = obtener_estadisticas_maquinarias()

    ubicaciones = obtener_ubicaciones()

    return render_template(
        "maquina.html",
        maquinas=maquinas,
        estadisticas=estadisticas,
        ubicaciones=ubicaciones,
    )


@app.route("/maquinarias/nuevo", methods=["GET", "POST"])
@login_required
@roles_required("Administrador")
def nueva_maquinaria():

    if request.method == "POST":

        cantidad = int(request.form["cantidad"] or 1)
        precio = float(request.form["precio_unitario_us"] or 0)
        total = cantidad * precio

        datos = {
            "id_activo": request.form["id_activo"],
            "categoria": request.form["categoria"],
            "descripcion": request.form["descripcion"],
            "cantidad": cantidad,
            "marca": request.form["marca"],
            "modelo": request.form["modelo"],
            "numero_serie": request.form["numero_serie"],
            "serie_interna": request.form["serie_interna"],
            "proveedor": request.form["proveedor"],
            "ubicacion": request.form["ubicacion"],
            "precio_unitario_us": precio,
            "total_us": total,
            "valor_mx": total,
            "fecha_alta": request.form["fecha_alta"],
            "observaciones": request.form["observaciones"],
        }

        insertar_maquinaria(datos)

        registrar_movimiento(
            usuario=session["nombre"],
            accion="Registró un nuevo activo",
            modulo="Maquinaria",
            referencia=request.form["id_activo"],
        )

        flash("Activo registrado correctamente.", "success")

        return redirect(url_for("lista_maquinarias"))

    return render_template("nueva_maquinaria.html", siguiente_id=siguiente_id_activo())


@app.route("/maquinarias/<id_activo>")
@login_required
def expediente_maquinaria(id_activo):

    # Si el usuario entra desde un celular o tablet,
    # mostrar automáticamente la interfaz móvil.
    if es_dispositivo_movil():
        return redirect(url_for("maquinaria_qr", id_activo=id_activo))

    maquina = obtener_maquinaria_detalle(id_activo)

    if not maquina:
        flash("El activo no existe.", "danger")
        return redirect(url_for("lista_maquinarias"))

    # ==========================================
    # Contenido / relaciones del activo
    # ==========================================

    contenido_activo = obtener_contenido_activo(id_activo)

    # Prueba temporal
    print("=" * 60)
    print("CONTENIDO DEL ACTIVO:", id_activo)
    print(contenido_activo)
    print("=" * 60)
    
        # ==========================================
    # Categorías y asignaciones de accesorios
    # ==========================================

    es_contenedor = bool(
        maquina.get("es_contenedor")
    )

    es_accesorio = (
        not es_contenedor
        and
        (maquina.get("categoria") or "").strip().upper()
        == "ACCESORIO"
    )

    categorias_accesorios = []
    asignacion_activa = None
    historial_asignaciones = []
    accesorios_asignados = []

    if es_contenedor or es_accesorio:

        categorias_accesorios = (
            obtener_categorias_accesorios()
        )

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

    elif not es_contenedor:

        accesorios_asignados = (
            obtener_accesorios_asignados_maquinaria(
                id_activo
            )
        )

    # ==========================================
    # Guardar activo reciente
    # ==========================================

    registrar_activo_reciente(usuario=session["nombre"], id_activo=id_activo)

    # ==========================================
    # Aduana
    # ==========================================

    aduana = obtener_aduana(id_activo)

    # ==========================================
    # Tipo de expediente
    # ==========================================

    es_nacional = False
    es_importado = False
    es_pendiente = False
    es_sin_clasificar = False
    es_reingreso = False

    if aduana:

        origen = (aduana.get("origen") or "").strip().upper()

        if origen in ["NACIONAL", "MEXICO"]:
            es_nacional = True

        elif origen == "PENDIENTE":
            es_pendiente = True

        elif origen == "NA":
            es_sin_clasificar = True

        elif origen == "REINGRESO":
            es_reingreso = True

        else:
            es_importado = True

    # ==========================================
    # Estado del expediente aduanal
    # ==========================================

    estado_aduana = estado_expediente_aduanal(aduana)

    # ==========================================
    # Historial
    # ==========================================

    historial = obtener_historial_activo(id_activo)

    # ==========================================
    # Navegación anterior / siguiente
    # ==========================================

    vecinos = obtener_activos_vecinos(id_activo)

    # ==========================================
    # Documentos
    # ==========================================

    documentos = listar_documentos(id_activo)

    # ==========================================
    # Traslados
    # ==========================================

    traslado_en_proceso = obtener_traslado_en_proceso(id_activo)

    # ==========================================
    # Mantenimiento
    # ==========================================

    mantenimiento_en_proceso = obtener_mantenimiento_en_proceso(id_activo)

    # ==========================================
    # Debug temporal
    # ==========================================

    print("=" * 60)
    print("ACTIVO:", id_activo)
    print("TRASLADO:", traslado_en_proceso)
    print("=" * 60)

    # ==========================================
    # Render
    # ==========================================

    return render_template(
        "expediente_maquinaria.html",
        maquina=maquina,
        aduana=aduana,
        estado_aduana=estado_aduana,
        historial=historial,
        documentos=documentos,
        traslado_en_proceso=traslado_en_proceso,
        mantenimiento_en_proceso=mantenimiento_en_proceso,
        contenido_activo=contenido_activo,
        anterior=vecinos["anterior"],
        siguiente=vecinos["siguiente"],
        es_nacional=es_nacional,
        es_importado=es_importado,
        es_pendiente=es_pendiente,
        es_sin_clasificar=es_sin_clasificar,
        es_reingreso=es_reingreso,
        es_accesorio=es_accesorio,
        categorias_accesorios=categorias_accesorios,
        asignacion_activa=asignacion_activa,
        historial_asignaciones=historial_asignaciones,
        accesorios_asignados=accesorios_asignados,
    )


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


@app.route("/maquinarias/<id_activo>/imprimir")
@login_required
def imprimir_maquinaria(id_activo):

    maquina = obtener_maquinaria_detalle(id_activo)

    if not maquina:
        flash("El activo no existe.", "danger")
        return redirect(url_for("lista_maquinarias"))

    return render_template("imprimir-qr.html", maquina=maquina)


@app.route("/maquinarias/<id_activo>/qr")
@login_required
def qr_maquinaria(id_activo):

    maquina = obtener_maquinaria_detalle(id_activo)

    if not maquina:
        flash("El activo no existe.", "danger")
        return redirect(url_for("lista_maquinarias"))

    # URL que abrirá el QR
    url = url_for("expediente_maquinaria", id_activo=id_activo, _external=True)

    # Generar QR
    img = qrcode.make(url)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    qr = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return render_template("qr_maquinaria.html", maquina=maquina, qr=qr)


@app.route("/maquinarias/<id_activo>/editar", methods=["GET", "POST"])
@login_required
def editar_maquinaria(id_activo):

    # Solo administrador
    if session.get("rol") != "Administrador":

        flash("No tiene permisos para editar activos.", "danger")

        return redirect(url_for("lista_maquinarias"))

    # Obtener el activo
    maquina = obtener_maquinaria(id_activo)

    if not maquina:

        flash("El activo no existe.", "danger")

        return redirect(url_for("lista_maquinarias"))

    # Guardar cambios
    if request.method == "POST":

        cantidad = int(request.form["cantidad"] or 1)
        precio = float(request.form["precio_unitario_us"] or 0)
        total = float(request.form["total_us"] or 0)
        valor_mx = float(request.form["valor_mx"] or 0)

        datos = {
            "id_activo": id_activo,
            "categoria": request.form["categoria"],
            "descripcion": request.form["descripcion"],
            "cantidad": cantidad,
            "marca": request.form["marca"],
            "modelo": request.form["modelo"],
            "numero_serie": request.form["numero_serie"],
            "serie_interna": request.form["serie_interna"],
            "proveedor": request.form["proveedor"],
            "ubicacion": request.form["ubicacion"],
            "precio_unitario_us": precio,
            "total_us": total,
            "valor_mx": valor_mx,
            "fecha_alta": request.form["fecha_alta"],
            "observaciones": request.form["observaciones"],
        }

        actualizar_maquinaria(datos)

        registrar_movimiento(
            usuario=session["nombre"],
            accion="Actualizó información del activo",
            modulo="Maquinaria",
            referencia=id_activo,
        )

        flash(f"El activo {id_activo} fue actualizado correctamente.", "success")

        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    # Mostrar formulario
    return render_template("nueva_maquinaria.html", maquina=maquina, editar=True)


@app.route("/maquinarias/<id_activo>/solicitud-baja", methods=["POST"])
@login_required
def solicitud_baja(id_activo):

    # Solo Administrador y Mantenimiento
    if session.get("rol") not in ["Administrador", "Mantenimiento"]:

        flash("No tiene permisos para realizar esta acción.", "danger")
        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    maquina = obtener_maquinaria(id_activo)

    if not maquina:

        flash("El activo no existe.", "danger")
        return redirect(url_for("lista_maquinarias"))

    origen = request.form.get("origen", "desktop")

    print("=" * 50)
    print("ORIGEN:", origen)
    print("FORM:", request.form.to_dict())
    print("=" * 50)

    # ---------- ESTA FUNCIÓN VA DENTRO ----------
    def regresar():

        print(">>> regresar()")
        print(">>> origen =", origen)

        if origen in ("mobile", "qr"):

            print(">>> REDIRECCIÓN A MÓVIL")

            return redirect(url_for("maquinaria_qr", id_activo=id_activo))

        print(">>> REDIRECCIÓN A ESCRITORIO")

        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    # ==================================================
    # VALIDACIÓN 1
    # ==================================================

    tipo = request.form["tipo"]

    if maquina["estado"] == "BAJA" and tipo != "REINCORPORACION":

        flash(
            "Este activo ya fue dado de baja y solo puede solicitar una reactivación.",
            "warning",
        )

        return regresar()

    # ==================================================
    # VALIDACIÓN 2
    # ==================================================

    if existe_solicitud_pendiente(id_activo):

        flash("Este activo ya cuenta con una solicitud pendiente.", "warning")

        return regresar()

    datos = {
        "id_activo": id_activo,
        "solicitante": session["nombre"],
        "tipo": tipo,
        "motivo": request.form["motivo"],
        "observaciones": request.form["observaciones"],
        "prioridad": request.form["prioridad"],
        "ubicacion_destino": request.form.get("ubicacion_destino") or None,
        "proveedor_mantenimiento": request.form.get("proveedor_mantenimiento") or None,
        "fecha_estimada_fin": request.form.get("fecha_estimada_fin") or None,
    }

    guardar_solicitud(datos)

    acciones = {
        "BAJA": "Solicitó baja del activo",
        "TRASLADO": "Solicitó traslado del activo",
        "MANTENIMIENTO": "Solicitó mantenimiento del activo",
        "REINCORPORACION": "Solicitó reactivación del activo",
    }

    registrar_movimiento(
        usuario=session["nombre"],
        accion=acciones[tipo],
        modulo="Maquinaria",
        referencia=id_activo,
    )

    flash(
        "La solicitud fue enviada correctamente y está pendiente de aprobación.",
        "success",
    )

    return regresar()


@app.route("/solicitudes-baja")
@login_required
def lista_solicitudes_baja():

    if session.get("rol") != "Administrador":

        flash("No tiene permisos.", "danger")

        return redirect(url_for("dashboard"))

    solicitudes = obtener_solicitudes()

    return render_template(
        "solicitudes_baja.html", solicitudes=solicitudes.to_dict("records")
    )


@app.route("/solicitudes-baja/<int:id>")
@login_required
def ver_solicitud(id):

    if session.get("rol") != "Administrador":

        flash("No tiene permisos.", "danger")

        return redirect(url_for("dashboard"))

    solicitud = obtener_solicitud(id)

    return jsonify(solicitud.to_dict())


@app.route("/solicitudes-baja/<int:id>/aprobar", methods=["POST"])
@login_required
def aprobar_solicitud_route(id):

    if session.get("rol") != "Administrador":

        return jsonify({"ok": False, "error": "No tiene permisos."}), 403

    try:

        data = request.get_json()

        comentario = data.get("comentario", "")

        aprobar_solicitud(id, session["nombre"], comentario)

        return jsonify({"ok": True})

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/solicitudes-baja/<int:id>/rechazar", methods=["POST"])
@login_required
def rechazar_solicitud_route(id):

    if session.get("rol") != "Administrador":

        return jsonify({"ok": False, "error": "No tiene permisos."}), 403

    try:

        data = request.get_json()

        comentario = data.get("comentario", "")

        rechazar_solicitud(id, session["nombre"], comentario)

        return jsonify({"ok": True})

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/aduanas")
@login_required
def lista_aduanas():

    aduanas = obtener_aduanas()

    print(aduanas.head())
    print(aduanas.shape)

    return render_template("aduanas.html", aduanas=aduanas.to_dict("records"))


@app.route("/aduanas/<id_activo>/editar", methods=["GET", "POST"])
@login_required
def editar_aduana(id_activo):

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para editar expedientes aduanales.", "danger")

        return redirect(url_for("lista_aduanas"))

    maquinarias = obtener_maquinarias_select()

    aduana = obtener_aduana(id_activo)

    editar = aduana is not None

    if request.method == "POST":

        guardar_aduana(
            id_activo,
            request.form["factura"],
            request.form["pedimento"],
            request.form["entrada_mtz"],
            request.form["id_imp"],
            request.form["inbond"],
            request.form["origen"],
            request.form["fecha_importacion"],
            request.form.get("kg_bruto"),
            request.form.get("total_bultos"),
            request.form.get("documentacion_completa"),
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion="Actualizó expediente aduanal",
            modulo="Aduanas",
            referencia=id_activo,
        )

        flash("Expediente guardado correctamente.", "success")

        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    if not editar:

        aduana = {
            "id_activo": id_activo,
            "factura": "",
            "pedimento": "",
            "entrada_mtz": "",
            "id_imp": "",
            "inbond": "",
            "origen": "",
            "fecha_importacion": "",
            "kg_bruto": "",
            "total_bultos": "",
            "documentacion_completa": "",
        }

    return render_template(
        "nueva_aduana.html",
        maquinarias=maquinarias.to_dict("records"),
        aduana=aduana,
        editar=editar,
    )


@app.route("/aduanas/nuevo", methods=["GET", "POST"])
@login_required
def nueva_aduana():

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para crear expedientes aduanales.", "danger")

        return redirect(url_for("lista_aduanas"))

    id_activo = request.args.get("id")

    maquinarias = obtener_maquinarias_select()

    if request.method == "POST":

        guardar_aduana(
            request.form["id_activo"],
            request.form["factura"],
            request.form["pedimento"],
            request.form["entrada_mtz"],
            request.form["id_imp"],
            request.form["inbond"],
            request.form["origen"],
            request.form["fecha_importacion"],
            request.form.get("kg_bruto"),
            request.form.get("total_bultos"),
            request.form.get("documentacion_completa"),
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion="Creó expediente aduanal",
            modulo="Aduanas",
            referencia=request.form["id_activo"],
        )

        flash("Expediente aduanal actualizado correctamente.", "success")

        return redirect(url_for("lista_aduanas"))

    aduana = {
        "id_activo": id_activo,
        "factura": "",
        "pedimento": "",
        "entrada_mtz": "",
        "id_imp": "",
        "inbond": "",
        "origen": "",
        "fecha_importacion": "",
    }

    return render_template(
        "nueva_aduana.html",
        maquinarias=maquinarias.to_dict("records"),
        aduana=aduana,
        editar=False,
    )


@app.route("/aduanas/datos/<id_activo>")
@login_required
def datos_aduana(id_activo):

    aduana = obtener_aduana(id_activo)

    if aduana.empty:
        return jsonify({})

    datos = aduana.iloc[0].to_dict()

    if datos.get("fecha_importacion"):
        datos["fecha_importacion"] = str(datos["fecha_importacion"])[:10]

    return jsonify(datos)


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


@app.route("/maquinarias/<id_activo>/documentos", methods=["POST"])
@login_required
def subir_documento(id_activo):

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para subir documentos.", "danger")

        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    archivo = request.files.get("documento")

    tipo_documento = request.form.get("tipo_documento")

    if not archivo or archivo.filename == "":

        flash("Seleccione un archivo.", "warning")

        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    nombre_original = archivo.filename

    nombre_seguro = secure_filename(nombre_original)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    nombre_archivo = f"{id_activo}_{timestamp}_{nombre_seguro}"

    try:

        print("=" * 70)
        print("INICIANDO SUBIDA A SUPABASE")
        print("Activo:", id_activo)
        print("Archivo:", nombre_original)

        archivo_bytes = archivo.read()

        ruta = f"{id_activo}/{nombre_archivo}"

        respuesta = supabase.storage.from_("documentos").upload(
            path=ruta,
            file=archivo_bytes,
            file_options={"content-type": archivo.content_type, "upsert": False},
        )

        print("RESPUESTA UPLOAD:")
        print(respuesta)

        url_pdf = supabase.storage.from_("documentos").get_public_url(ruta)

        print("=" * 70)
        print("TIPO URL:", type(url_pdf))
        print("URL:", url_pdf)
        print("=" * 70)

        # Compatibilidad con distintas versiones del SDK
        if isinstance(url_pdf, dict):
            url_guardar = url_pdf.get("publicUrl") or url_pdf.get("public_url")
        else:
            url_guardar = url_pdf

        guardar_documento_bd(
            id_activo=id_activo,
            nombre_original=nombre_original,
            nombre_archivo=nombre_archivo,
            tipo=tipo_documento,
            tipo_archivo="DOCUMENTO",
            descripcion=request.form.get("descripcion"),
            url=url_guardar,
            public_id=ruta,
            usuario=session["nombre"],
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Subió documento: {nombre_original}",
            modulo="Documentación",
            referencia=id_activo,
        )

        print("DOCUMENTO GUARDADO EN MYSQL")

        flash("Documento subido correctamente.", "success")

    except Exception as e:

        import traceback

        traceback.print_exc()

        print("=" * 70)
        print("ERROR SUBIENDO DOCUMENTO")
        print(e)
        print("=" * 70)

        flash(f"Ocurrió un error al subir el documento: {e}", "danger")

    return redirect(url_for("expediente_maquinaria", id_activo=id_activo))


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


@app.route("/documentos/<int:id_documento>/eliminar", methods=["POST"])
@login_required
def borrar_documento(id_documento):

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para eliminar documentos.", "danger")

        return redirect(request.referrer or url_for("lista_maquinarias"))

    # Obtener información del documento
    doc = obtener_documento(id_documento)

    if not doc:

        flash("Documento no encontrado.", "danger")

        return redirect(request.referrer or url_for("lista_maquinarias"))

    # Eliminar archivo de Supabase
    try:

        if doc["public_id"]:

            print("PUBLIC ID:", repr(doc["public_id"]))

            respuesta = supabase.storage.from_("documentos").remove([doc["public_id"]])

            print("RESPUESTA SUPABASE:", respuesta)

    except Exception as e:

        print("ERROR SUPABASE:", e)

    # Eliminar registro de MySQL
    eliminar_documento(id_documento)

    # Auditoría
    registrar_movimiento(
        usuario=session["nombre"],
        accion="Eliminó documento",
        modulo="Documentación",
        referencia=doc["id_activo"],
    )

    flash("Documento eliminado correctamente.", "success")

    return redirect(url_for("expediente_maquinaria", id_activo=doc["id_activo"]))


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


@app.route("/qr/<id_activo>/documento/<tipo>")
@login_required
def qr_documento(id_activo, tipo):

    documentos = listar_documentos(id_activo)

    print("TIPO SOLICITADO:", tipo)

    for doc in documentos:
        print(doc)

    documento = None

    for doc in documentos:
        if doc["tipo"].lower() == tipo.lower():
            documento = doc
            break

    if not documento:
        abort(404)

    return render_template(
        "maquinaria_qr/documento.html", documento=documento, id_activo=id_activo
    )


@app.route("/m/dashboard")
@login_required
def dashboard_mobil():

    kpis = obtener_kpis_dashboard()

    actividad = obtener_actividad_dashboard()

    return render_template(
        "maquinaria_qr/dashboard_mobil.html", **kpis, actividad=actividad
    )


@app.route("/m/maquinarias/<id_activo>/movimiento/<tipo>")
@login_required
@roles_required("Administrador", "Mantenimiento")
def formulario_movimiento_mobile(id_activo, tipo):

    maquina = obtener_maquinaria(id_activo)

    if not maquina:
        flash("Activo no encontrado.", "danger")
        return redirect(url_for("dashboard_mobile"))

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


from flask import request


def es_movil():

    user_agent = request.user_agent.string.lower()

    palabras = ["android", "iphone", "ipad", "mobile"]

    return any(p in user_agent for p in palabras)


@app.route("/qr/<id_activo>/evidencias")
@login_required
def qr_evidencias(id_activo):

    maquinaria = obtener_maquinaria(id_activo)

    imagenes = listar_documentos(id_activo, "IMAGEN")

    print("=" * 60)
    print(imagenes)
    print(type(imagenes))
    print("=" * 60)

    return render_template(
        "maquinaria_qr/evidencias.html",
        maquinaria=maquinaria,
        imagenes=imagenes,
        id_activo=id_activo,
        pagina="evidencias",
    )


@app.route("/qr/<id_activo>/evidencias", methods=["POST"])
@login_required
def subir_evidencia(id_activo):

    if session.get("rol") != "Administrador":

        flash("No tiene permisos para subir evidencias.", "danger")

        return redirect(url_for("qr_evidencias", id_activo=id_activo))

    archivo = request.files.get("documento")

    if not archivo or archivo.filename == "":

        flash("Seleccione una imagen.", "warning")

        return redirect(url_for("qr_evidencias", id_activo=id_activo))

    try:

        nombre_original = archivo.filename

        nombre_seguro = secure_filename(nombre_original)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        nombre_archivo = f"{id_activo}_{timestamp}_{nombre_seguro}"

        archivo_bytes = archivo.read()

        ruta = f"{id_activo}/{nombre_archivo}"

        supabase.storage.from_("documentos").upload(
            path=ruta,
            file=archivo_bytes,
            file_options={"content-type": archivo.content_type, "upsert": False},
        )

        url_publica = supabase.storage.from_("documentos").get_public_url(ruta)

        if isinstance(url_publica, dict):

            url_guardar = url_publica.get("publicUrl") or url_publica.get("public_url")

        else:

            url_guardar = url_publica

        guardar_documento_bd(
            id_activo=id_activo,
            nombre_original=nombre_original,
            nombre_archivo=nombre_archivo,
            tipo="General",
            tipo_archivo="IMAGEN",
            descripcion=None,
            url=url_guardar,
            public_id=ruta,
            usuario=session["nombre"],
        )

        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Subió evidencia: {nombre_original}",
            modulo="Evidencias",
            referencia=id_activo,
        )

        flash("Evidencia guardada correctamente.", "success")

    except Exception as e:

        flash(str(e), "danger")

    return redirect(url_for("qr_evidencias", id_activo=id_activo))


@app.route("/evidencias/<int:id>/eliminar")
@login_required
def eliminar_evidencia(id):

    if session.get("rol") != "Administrador":

        flash("Sin permisos.", "danger")

        return redirect(request.referrer or url_for("dashboard"))

    try:

        documento = obtener_documento(id)

        if not documento:

            flash("La evidencia no existe.", "warning")

            return redirect(request.referrer)

        # Eliminar archivo de Supabase
        supabase.storage.from_("documentos").remove([documento["public_id"]])

        # Eliminar registro de MySQL
        eliminar_documento(id)

        # Registrar auditoría
        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Eliminó evidencia: {documento['nombre_original']}",
            modulo="Evidencias",
            referencia=documento["id_activo"],
        )

        flash("Evidencia eliminada correctamente.", "success")

        return redirect(url_for("qr_evidencias", id_activo=documento["id_activo"]))

    except Exception as e:

        flash(f"Error al eliminar evidencia: {e}", "danger")

        return redirect(request.referrer)


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


@app.route("/m/aduanas")
@login_required
def aduanas_mobile():

    return render_template("maquinaria_qr/aduanas_mobile.html")


@app.route("/m/aduanas/api")
@login_required
def api_aduanas_mobile():

    q = request.args.get("q", "").strip()
    origen = request.args.get("origen", "")
    tipo = request.args.get("tipo", "")

    offset = int(request.args.get("offset", 0))

    limite = 20

    aduanas = (
        obtener_aduanas_mobile_filtrado(
            q=q, origen=origen, tipo=tipo, limite=limite, offset=offset
        )
        .fillna("")
        .to_dict("records")
    )

    for aduana in aduanas:

        aduana["expediente"] = estado_expediente_aduanal(aduana)

    return jsonify(aduanas)


@app.route("/m/aduanas/origenes")
@login_required
def api_origenes_mobile():

    origenes = obtener_origenes()

    return jsonify(origenes)


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

if __name__ == "__main__":

    app.run(debug=True)
