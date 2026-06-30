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
from models.auditoria_model import registrar_movimiento
from functools import wraps
from database.maquinarias import obtener_todas_maquinas, insertar_maquinaria, siguiente_id_activo, actualizar_maquinaria
from database.aduanas import crear_registro_aduana_vacio


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

from database.maquinarias import (
    obtener_maquinarias,
    obtener_maquinaria
)

from database.aduanas import (
    obtener_aduanas
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
# MAQUINARIA
# ==========================================================

@app.route("/maquina/<codigo>")
@login_required
def maquina(codigo):

    df = obtener_maquinaria(codigo)

    if df.empty:
        return "Activo no encontrado", 404

    maquina = df.iloc[0].to_dict()

    return render_template(
        "maquina.html",
        maquina=maquina
    )


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

    return render_template(

        "maquina.html",

        maquinas=maquinas

    )

@app.route("/maquinarias/nuevo", methods=["GET", "POST"])
@login_required
def nueva_maquinaria():

    if request.method == "POST":

        cantidad = int(request.form["cantidad"] or 1)
        precio = float(request.form["precio_unitario"] or 0)
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

    maquina = obtener_maquinaria(id_activo)

    if not maquina:

        flash(
            "El activo no existe.",
            "danger"
        )

        return redirect(url_for("lista_maquinarias"))

    return render_template(
        "expediente_maquinaria.html",
        maquina=maquina
    )

@app.route("/maquinarias/<id_activo>/qr")
@login_required
def qr_maquinaria(id_activo):

    maquina = obtener_maquinaria(id_activo)

    return render_template(
        "qr_maquinaria.html",
        maquina=maquina
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
        precio = float(request.form["precio_unitario"] or 0)
        total = cantidad * precio

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
            "valor_mx": total,
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


# ==========================================================
# SERVIDOR
# ==========================================================

if __name__ == "__main__":

    app.run(debug=True)