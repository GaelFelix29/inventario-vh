from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    session,
    flash
)

import cloudinary_config
import cloudinary.uploader
import cloudinary.api

from flask import send_from_directory


from flask import jsonify
from respaldos import BASE_DIR, crear_respaldo

import os
from datetime import datetime

from werkzeug.utils import secure_filename
from sqlalchemy import text
from database.conexion import engine

from functools import wraps
from datetime import date

from models.auditoria_model import (
    registrar_movimiento,
    obtener_historial_activo
)

from database.documentos import (
    RUTA_DOCUMENTOS,
    crear_carpeta_activo,
    guardar_documento_bd,
    listar_documentos,
    eliminar_documento
)

from database.solicitudes_baja import (
    guardar_solicitud,
    obtener_solicitudes,
    obtener_solicitud,
    obtener_pendientes,
    aprobar_solicitud,
    rechazar_solicitud,
    existe_solicitud_pendiente
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
    verificar_password
)

from database.maquinarias import buscar_activos

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
    finalizar_mantenimiento_activo
)

from database.aduanas import (
    obtener_aduanas,
    obtener_aduana,
    crear_registro_aduana_vacio,
    guardar_aduana,
    actualizar_aduana,
    estado_expediente_aduanal
)

# ==========================================
# APP
# ==========================================

app = Flask(__name__)

app.secret_key = "VitalHealth2026"

# ==========================================
# DECORADORES
# ==========================================

def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "usuario_id" not in session:

            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


def admin_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "usuario_id" not in session:

            return redirect(url_for("login"))

        if session.get("rol") != "Administrador":

            flash(
                "No tienes permisos para acceder a esta sección.",
                "danger"
            )

            return redirect(url_for("inicio"))

        return func(*args, **kwargs)

    return wrapper

# ==========================================================
# INICIO
# ==========================================================

@app.route("/")
@login_required
def inicio():

    return render_template("index.html")


# ==========================================================
# LOGIN
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "usuario_id" in session:
        return redirect(url_for("inicio"))

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        datos = obtener_usuario(usuario)

        if datos and verificar_password(password, datos.password):

            session["usuario_id"] = datos.id
            session["nombre"] = datos.nombre
            session["usuario"] = datos.usuario
            session["rol"] = datos.rol

            flash(
                f"Bienvenido {datos.nombre}",
                "success"
            )

            registrar_movimiento(

                usuario=session["nombre"],

                accion="Inició sesión",

                modulo="Login"

            )
        return redirect(url_for("inicio"))

        flash(
            "Usuario o contraseña incorrectos.",
            "danger"
        )

    return render_template("login.html")


# ==========================================================
# LOGOUT
# ==========================================================

@app.route("/logout")
@login_required
def logout():

    session.clear()

    flash(
        "Sesión cerrada correctamente.",
        "info"
    )

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
            "rol": session["rol"]
        }
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

    return render_template(
        "usuarios.html",
        usuarios=lista
    )


# ==========================================================
# NUEVO USUARIO
# ==========================================================

@app.route("/usuarios/nuevo", methods=["GET", "POST"])
@admin_required
def nuevo_usuario():

    if request.method == "POST":

        if request.form["password"] != request.form["confirmar"]:

            flash(
                "Las contraseñas no coinciden.",
                "danger"
            )

            return redirect(url_for("nuevo_usuario"))

        crear_usuario(

            request.form["nombre"],
            request.form["usuario"],
            request.form["correo"],
            request.form["password"],
            request.form["rol"]

        )

        flash(
            "Usuario creado correctamente.",
            "success"
        )

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

        flash(
            "Usuario no encontrado.",
            "danger"
        )

        return redirect(url_for("usuarios"))

    if request.method == "POST":

        actualizar_usuario(

            id,
            request.form["nombre"],
            request.form["usuario"],
            request.form["correo"],
            request.form["rol"],
            int(request.form["activo"])

        )

        if request.form["password"] != "":

            actualizar_password(

                id,
                request.form["password"]

            )

        flash(
            "Usuario actualizado correctamente.",
            "success"
        )

        return redirect(url_for("usuarios"))

    return render_template(
        "editar_usuario.html",
        usuario=usuario
    )


# ==========================================================
# DESACTIVAR USUARIO
# ==========================================================

@app.route("/usuarios/desactivar/<int:id>")
@admin_required
def desactivar(id):

    desactivar_usuario(id)

    flash(
        "Usuario desactivado correctamente.",
        "warning"
    )

    return redirect(url_for("usuarios"))


# ==========================================================
# REACTIVAR USUARIO
# ==========================================================

@app.route("/usuarios/reactivar/<int:id>")
@admin_required
def reactivar_usuario_route(id):

    reactivar_usuario(id)

    flash(
        "Usuario reactivado correctamente.",
        "success"
    )

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
    bajas = maq["fecha_baja"].notna().sum()
    activos = total - bajas
    valor = maq["valor_mx"].fillna(0).sum()

    origen = (
        aduana["origen"]
        .fillna("SIN DATO")
        .value_counts()
    )

    documentacion = (
        aduana["documentacion_completa"]
        .fillna("NO")
        .value_counts()
    )

    top = (
        maq["categoria"]
        .fillna("SIN DATO")
        .value_counts()
        .head(10)
    )

    valor_origen = (
        aduana
        .merge(
            maq[["id_activo", "valor_mx"]],
            on="id_activo",
            how="left"
        )
        .groupby("origen")["valor_mx"]
        .sum()
    )

    return jsonify({

        "kpi":{

            "total": int(total),
            "activos": int(activos),
            "bajas": int(bajas),
            "valor": float(valor)

        },

        "origen":{

            "labels": origen.index.tolist(),
            "values": origen.values.tolist()

        },

        "documentacion":{

            "labels": documentacion.index.tolist(),
            "values": documentacion.values.tolist()

        },

        "top":{

            "labels": top.index.tolist(),
            "values": top.values.tolist()

        },

        "valorOrigen":{

            "labels": valor_origen.index.tolist(),
            "values": valor_origen.values.tolist()

        }

    })  

# ==========================================================
# IMPRIMIR QR
# ==========================================================

@app.route("/imprimir")
@login_required
def imprimir_qr():

    maquinas = obtener_maquinarias()

    return render_template(
        "imprimir-qr.html",
        maquinas=maquinas.to_dict("records")
    )


# ==========================================================
# ETIQUETAS
# ==========================================================

@app.route("/etiquetas", methods=["POST"])
@login_required
def etiquetas():

    datos = request.get_json()

    codigos = datos["codigos"]

    maquinas = obtener_maquinarias()

    maquinas = maquinas[
        maquinas["id_activo"].isin(codigos)
    ]

    etiquetas = []

    for _, fila in maquinas.iterrows():

        url = request.host_url + "maquina/" + fila["id_activo"]

        qr = qrcode.make(url)

        buffer = BytesIO()

        qr.save(buffer, format="PNG")

        qr64 = base64.b64encode(
            buffer.getvalue()
        ).decode()

        etiquetas.append({

            "codigo": fila["id_activo"],

            "nombre": fila["descripcion"],

            "estado":
                "BAJA"
                if pd.notna(fila["fecha_baja"])
                else "ACTIVO",

            "url": url,

            "qr": qr64

        })

    return render_template(

        "etiquetas.html",

        etiquetas=etiquetas

    )

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

        ubicaciones=ubicaciones

    )

@app.route("/maquinarias/nuevo", methods=["GET", "POST"])
@login_required
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
            "observaciones": request.form["observaciones"]

        }

        insertar_maquinaria(datos)

        registrar_movimiento(

            usuario=session["nombre"],
            accion="Registró un nuevo activo",
            modulo="Maquinaria",
            referencia=request.form["id_activo"]

        )

        flash("Activo registrado correctamente.", "success")

        return redirect(url_for("lista_maquinarias"))

    return render_template(
        "nueva_maquinaria.html",
        siguiente_id=siguiente_id_activo()
    )

@app.route("/maquinarias/<id_activo>")
@login_required
def expediente_maquinaria(id_activo):

    maquina = obtener_maquinaria_detalle(id_activo)

    if not maquina:

        flash(
            "El activo no existe.",
            "danger"
        )

        return redirect(
            url_for("lista_maquinarias")
        )

    aduana = obtener_aduana(id_activo)

    # ======================================
    # Tipo de expediente
    # ======================================

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

    estado_aduana = estado_expediente_aduanal(aduana)

    historial = obtener_historial_activo(id_activo)

    vecinos = obtener_activos_vecinos(id_activo)

    documentos = listar_documentos(id_activo)

    return render_template(

        "expediente_maquinaria.html",

        maquina=maquina,

        aduana=aduana,

        estado_aduana=estado_aduana,

        historial=historial,

        documentos=documentos,

        anterior=vecinos["anterior"],

        siguiente=vecinos["siguiente"],

        es_nacional=es_nacional,

        es_importado=es_importado,

        es_pendiente=es_pendiente,

        es_sin_clasificar=es_sin_clasificar,

        es_reingreso=es_reingreso,

    )

@app.route("/maquinarias/<id_activo>/imprimir")
@login_required
def imprimir_maquinaria(id_activo):

    maquina = obtener_maquinaria_detalle(id_activo)

    if not maquina:
        flash(
            "El activo no existe.",
            "danger"
        )
        return redirect(url_for("lista_maquinarias"))

    return render_template(
        "imprimir-qr.html",
        maquina=maquina
    )

@app.route("/maquinarias/<id_activo>/qr")
@login_required
def qr_maquinaria(id_activo):

    maquina = obtener_maquinaria_detalle(id_activo)

    if not maquina:
        flash("El activo no existe.", "danger")
        return redirect(url_for("lista_maquinarias"))

    # URL que abrirá el QR
    url = url_for(
        "expediente_maquinaria",
        id_activo=id_activo,
        _external=True
    )

    # Generar QR
    img = qrcode.make(url)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    qr = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return render_template(
        "qr_maquinaria.html",
        maquina=maquina,
        qr=qr
    )
@app.route("/maquinarias/<id_activo>/editar", methods=["GET", "POST"])
@login_required
def editar_maquinaria(id_activo):

    # Solo administrador
    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para editar activos.",
            "danger"
        )

        return redirect(url_for("lista_maquinarias"))

    # Obtener el activo
    maquina = obtener_maquinaria(id_activo)

    if not maquina:

        flash(
            "El activo no existe.",
            "danger"
        )

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
            "observaciones": request.form["observaciones"]

        }

        actualizar_maquinaria(datos)

        registrar_movimiento(

            usuario=session["nombre"],
            accion="Actualizó información del activo",
            modulo="Maquinaria",
            referencia=id_activo

        )

        flash(
            f"El activo {id_activo} fue actualizado correctamente.",
            "success"
        )

        return redirect(
            url_for("expediente_maquinaria", id_activo=id_activo)
        )

    # Mostrar formulario
    return render_template(

        "nueva_maquinaria.html",

        maquina=maquina,

        editar=True

    )



@app.route("/maquinarias/<id_activo>/solicitud-baja", methods=["POST"])
@login_required
def solicitud_baja(id_activo):

    # Solo Administrador y Mantenimiento
    if session.get("rol") not in ["Administrador", "Mantenimiento"]:

        flash(
            "No tiene permisos para realizar esta acción.",
            "danger"
        )

        return redirect(url_for(
            "expediente_maquinaria",
            id_activo=id_activo
        ))

    maquina = obtener_maquinaria(id_activo)

    if not maquina:

        flash(
            "El activo no existe.",
            "danger"
        )

        return redirect(url_for("lista_maquinarias"))

    # ==================================================
    # VALIDACIÓN 1
    # El activo ya está dado de baja
    # ==================================================

    if maquina["estado"] == "BAJA":

        flash(
            "Este activo ya fue dado de baja y no puede generar otra solicitud.",
            "warning"
        )

        return redirect(
            url_for(
                "expediente_maquinaria",
                id_activo=id_activo
            )
        )

    # ==================================================
    # VALIDACIÓN 2
    # Ya existe una solicitud pendiente
    # ==================================================

    if existe_solicitud_pendiente(id_activo):

        flash(
        "Este activo ya cuenta con una solicitud pendiente.",
        "warning"
        )

        return redirect(
            url_for(
                "expediente_maquinaria",
                id_activo=id_activo
            )
        )

    datos = {

    "id_activo": id_activo,

    "solicitante": session["nombre"],

    "tipo": request.form["tipo"],

    "motivo": request.form["motivo"],

    "observaciones": request.form["observaciones"],

    "prioridad": request.form["prioridad"],

    "ubicacion_destino": request.form.get("ubicacion_destino") or None,

    "proveedor_mantenimiento": request.form.get("proveedor_mantenimiento") or None,

    "fecha_estimada_fin": request.form.get("fecha_estimada_fin") or None
}

    guardar_solicitud(datos)

    tipo = request.form["tipo"]

    acciones = {

    "BAJA": "Solicitó baja del activo",

    "TRASLADO": "Solicitó traslado del activo",

    "MANTENIMIENTO": "Solicitó mantenimiento del activo"

}

    registrar_movimiento(

        usuario=session["nombre"],

        accion=acciones[tipo],

        modulo="Maquinaria",

        referencia=id_activo

    )

    flash(
        "La solicitud fue enviada correctamente y está pendiente de aprobación.",
        "success"
    )

    return redirect(
        url_for(
            "expediente_maquinaria",
            id_activo=id_activo
        )
    )

@app.route("/solicitudes-baja")
@login_required
def lista_solicitudes_baja():

    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos.",
            "danger"
        )

        return redirect(url_for("dashboard"))

    solicitudes = obtener_solicitudes()

    return render_template(
    "solicitudes_baja.html",
    solicitudes=solicitudes.to_dict("records")
)

@app.route("/solicitudes-baja/<int:id>")
@login_required
def ver_solicitud(id):

    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos.",
            "danger"
        )

        return redirect(url_for("dashboard"))

    solicitud = obtener_solicitud(id)

    return jsonify(solicitud.to_dict())

@app.route("/solicitudes-baja/<int:id>/aprobar", methods=["POST"])
@login_required
def aprobar_solicitud_route(id):

    if session.get("rol") != "Administrador":

        return jsonify({
            "ok": False,
            "error": "No tiene permisos."
        }), 403

    try:

        data = request.get_json()

        comentario = data.get("comentario", "")

        aprobar_solicitud(

            id,

            session["nombre"],

            comentario

        )

        return jsonify({

            "ok": True

        })

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({

            "ok": False,

            "error": str(e)

        }), 500



@app.route("/solicitudes-baja/<int:id>/rechazar", methods=["POST"])
@login_required
def rechazar_solicitud_route(id):

    if session.get("rol") != "Administrador":

        return jsonify({
            "ok": False,
            "error": "No tiene permisos."
        }), 403

    try:

        data = request.get_json()

        comentario = data.get("comentario", "")

        rechazar_solicitud(

            id,

            session["nombre"],

            comentario

        )

        return jsonify({

            "ok": True

        })

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({

            "ok": False,

            "error": str(e)

        }), 500


@app.route("/aduanas")
@login_required
def lista_aduanas():

    aduanas = obtener_aduanas()

    print(aduanas.head())
    print(aduanas.shape)

    return render_template(
        "aduanas.html",
        aduanas=aduanas.to_dict("records")
    )


@app.route("/aduanas/<id_activo>/editar", methods=["GET", "POST"])
@login_required
def editar_aduana(id_activo):

    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para editar expedientes aduanales.",
            "danger"
        )

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
            request.form.get("documentacion_completa")

        )

        flash(
            "Expediente guardado correctamente.",
            "success"
        )

        return redirect(
            url_for("expediente_maquinaria", id_activo=id_activo)
        )

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

            "documentacion_completa": ""

        }

    return render_template(

        "nueva_aduana.html",

        maquinarias=maquinarias.to_dict("records"),

        aduana=aduana,

        editar=editar

    )

@app.route("/aduanas/nuevo", methods=["GET", "POST"])
@login_required
def nueva_aduana():

    if session.get("rol") != "Administrador":

        flash(
        "No tiene permisos para crear expedientes aduanales.",
        "danger"
    )

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
            request.form["fecha_importacion"]
        )

        flash(
            "Expediente aduanal actualizado correctamente.",
            "success"
        )

        return redirect(url_for("lista_aduanas"))

    aduana = {
        "id_activo": id_activo,
        "factura": "",
        "pedimento": "",
        "entrada_mtz": "",
        "id_imp": "",
        "inbond": "",
        "origen": "",
        "fecha_importacion": ""
    }

    return render_template(
        "nueva_aduana.html",
        maquinarias=maquinarias.to_dict("records"),
        aduana=aduana,
        editar=False
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

        return conn.execute(

            sql,

            {"id": id_activo}

        ).mappings().all()

@app.route("/maquinarias/<id_activo>/documentos", methods=["POST"])
@login_required
def subir_documento(id_activo):

    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para subir documentos.",
            "danger"
        )

        return redirect(
            url_for("expediente_maquinaria", id_activo=id_activo)
        )

    archivo = request.files.get("documento")

    if not archivo or archivo.filename == "":

        flash(
            "Seleccione un archivo.",
            "warning"
        )

        return redirect(
            url_for("expediente_maquinaria", id_activo=id_activo)
        )

    nombre_original = archivo.filename

    nombre_seguro = secure_filename(nombre_original)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Nombre del archivo (con extensión)
    nombre_archivo = f"{id_activo}_{timestamp}_{nombre_seguro}"

    # Nombre sin extensión para Cloudinary
    nombre_base = os.path.splitext(nombre_archivo)[0]

    try:

        print("=" * 70)
        print("INICIANDO SUBIDA A CLOUDINARY")
        print("Activo:", id_activo)
        print("Archivo:", nombre_original)

        resultado = cloudinary.uploader.upload(

            archivo,

            resource_type="auto",

            folder=f"documentos/{id_activo}",

            public_id=nombre_base,

            overwrite=False

        )

        print("RESULTADO:")
        print(resultado)

        guardar_documento_bd(

            id_activo=id_activo,

            nombre_original=nombre_original,

            nombre_archivo=nombre_archivo,

            tipo=os.path.splitext(nombre_original)[1],

            url=resultado["secure_url"],

            public_id=resultado["public_id"],

            usuario=session["nombre"]

        )

        print("DOCUMENTO GUARDADO EN MYSQL")
        print("=" * 70)

        flash(
            "Documento subido correctamente.",
            "success"
        )

    except Exception:

        import traceback

        print("=" * 70)
        print("ERROR AL SUBIR DOCUMENTO")
        traceback.print_exc()
        print("=" * 70)

        flash(
            "Ocurrió un error al subir el documento.",
            "danger"
        )

    return redirect(
        url_for(
            "expediente_maquinaria",
            id_activo=id_activo
        )
    )

@app.route("/buscar-activos")
@login_required
def buscar_activos_ajax():

    texto = request.args.get("q", "").strip()

    if len(texto) < 2:
        return jsonify([])

    activos = buscar_activos(texto)

    return jsonify([
        {
            "id": a["id_activo"],
            "text": a["id_activo"],

            "descripcion": a["descripcion"],
            "categoria": a["categoria"],
            "marca": a["marca"],
            "ubicacion": a["ubicacion"]
        }
        for a in activos
    ])

@app.route("/respaldos")
@login_required
def vista_respaldos():
    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para eliminar documentos.",
            "danger"
        )

        return redirect(request.referrer or url_for("lista_maquinarias"))

    carpeta = os.path.join(app.root_path, "backups")

    respaldos = []

    if os.path.exists(carpeta):

        for archivo in os.listdir(carpeta):

            if archivo.endswith(".sql"):

                ruta = os.path.join(carpeta, archivo)

                tamano = os.path.getsize(ruta)

                fecha_modificacion = os.path.getmtime(ruta)

                fecha = datetime.fromtimestamp(
                    fecha_modificacion
                ).strftime("%d/%m/%Y %H:%M")

                respaldos.append({

                    "archivo": archivo,

                    "fecha": fecha,

                    "tamano": round(tamano / 1024, 2)

                })

    # Ordenar por fecha de modificación (más reciente primero)
    respaldos.sort(
        key=lambda x: datetime.strptime(x["fecha"], "%d/%m/%Y %H:%M"),
        reverse=True
    )

    # ===========================
    # KPIs
    # ===========================

    total_respaldos = len(respaldos)

    espacio_total = round(
        sum(r["tamano"] for r in respaldos),
        2
    )

    ultimo = respaldos[0] if respaldos else None

    return render_template(

        "respaldos.html",

        respaldos=respaldos,

        total_respaldos=total_respaldos,

        espacio_total=espacio_total,

        ultimo=ultimo

    )


@app.route("/respaldos/crear", methods=["POST"])
@login_required
def crear_respaldo_ajax():
    
    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para eliminar documentos.",
            "danger"
        )

        return redirect(request.referrer or url_for("lista_maquinarias"))

    try:

        archivo = crear_respaldo()

        return jsonify({

            "ok": True,
            "archivo": archivo

        })

    except Exception as e:

        return jsonify({

            "ok": False,
            "error": str(e)

        }), 500
        
@app.route("/respaldos/descargar/<nombre>")
@login_required
def descargar_respaldo(nombre):
    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para eliminar documentos.",
            "danger"
        )

        return redirect(request.referrer or url_for("lista_maquinarias"))

    carpeta = os.path.join(app.root_path, "backups")

    return send_from_directory(
        carpeta,
        nombre,
        as_attachment=True
    )

@app.route("/respaldos/eliminar/<nombre>", methods=["POST"])
@login_required
def eliminar_respaldo(nombre):
    
    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para eliminar documentos.",
            "danger"
        )

        return redirect(request.referrer or url_for("lista_maquinarias"))

    ruta = os.path.join(app.root_path, "backups", nombre)

    if os.path.exists(ruta):

        os.remove(ruta)

        return jsonify({
            "ok": True
        })

    return jsonify({
        "ok": False
    }),404

@app.route("/maquinarias/<id_activo>/confirmar-recepcion", methods=["POST"])
@login_required
def confirmar_recepcion_route(id_activo):

    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para realizar esta acción.",
            "danger"
        )

        return redirect(
            url_for(
                "expediente_maquinaria",
                id_activo=id_activo
            )
        )

    confirmar_recepcion_activo(

        id_activo,

        session["nombre"]

    )

    flash(

        "La maquinaria fue recibida correctamente.",

        "success"

    )

    return redirect(

        url_for(

            "expediente_maquinaria",

            id_activo=id_activo

        )

    )

@app.route("/maquinarias/<id_activo>/finalizar-mantenimiento", methods=["POST"])
@login_required
def finalizar_mantenimiento_route(id_activo):

    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para realizar esta acción.",
            "danger"
        )

        return redirect(
            url_for(
                "expediente_maquinaria",
                id_activo=id_activo
            )
        )

    finalizar_mantenimiento_activo(

        id_activo,

        session["nombre"]

    )

    flash(

        "El mantenimiento fue finalizado correctamente.",

        "success"

    )

    return redirect(

        url_for(

            "expediente_maquinaria",

            id_activo=id_activo

        )

    )
    
@app.route("/documentos/<int:id_documento>/eliminar", methods=["POST"])
@login_required
def borrar_documento(id_documento):

    if session.get("rol") != "Administrador":

        flash(
            "No tiene permisos para eliminar documentos.",
            "danger"
        )

        return redirect(request.referrer or url_for("lista_maquinarias"))

    doc = eliminar_documento(id_documento)

    if not doc:

        flash(
            "Documento no encontrado.",
            "danger"
        )

        return redirect(request.referrer or url_for("lista_maquinarias"))

    try:

        if doc["public_id"]:

            cloudinary.uploader.destroy(
                doc["public_id"],
                resource_type="raw"
            )

    except Exception as e:

        print("Error eliminando en Cloudinary:", e)

    registrar_movimiento(

        usuario=session["nombre"],
        accion="Eliminó documento",
        modulo="Documentación",
        referencia=doc["id_activo"]

    )

    flash(
        "Documento eliminado correctamente.",
        "success"
    )

    return redirect(
        url_for(
            "expediente_maquinaria",
            id_activo=doc["id_activo"]
        )
    )

# ==========================================================
# SERVIDOR
# ==========================================================

if __name__ == "__main__":

    app.run(debug=True)