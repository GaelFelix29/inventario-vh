import secrets
import string

from flask import flash, make_response, redirect, render_template, request, session, url_for

from database.usuarios import (
    actualizar_usuario,
    crear_usuario,
    desactivar_usuario,
    establecer_password_temporal,
    obtener_usuario_id,
    obtener_usuarios,
    reactivar_usuario,
)


def generar_password_temporal(longitud=14):
    caracteres = string.ascii_letters + string.digits + "!@#$%*-_"
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%*-_"),
    ]
    password.extend(
        secrets.choice(caracteres)
        for _ in range(longitud - len(password))
    )
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def registrar_rutas_usuarios(app, admin_required, registrar_movimiento):
    """Registra las rutas de usuarios conservando URLs y endpoints existentes."""

    @app.route("/usuarios")
    @admin_required
    def usuarios():
        return render_template("usuarios.html", usuarios=obtener_usuarios())

    @app.route("/m/usuarios")
    @admin_required
    def usuarios_mobile():
        return render_template(
            "maquinaria_qr/usuarios_mobile.html",
            usuarios=obtener_usuarios(),
            pagina="usuarios",
        )

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

    @app.route("/m/usuarios/nuevo", methods=["GET", "POST"])
    @admin_required
    def nuevo_usuario_mobile():
        if request.method == "POST":
            nombre = (request.form.get("nombre") or "").strip()
            usuario = (request.form.get("usuario") or "").strip()
            correo = (request.form.get("correo") or "").strip()
            password = request.form.get("password") or ""
            confirmar = request.form.get("confirmar") or ""
            rol = (request.form.get("rol") or "").strip()

            if password != confirmar:
                flash("Las contraseñas no coinciden.", "danger")
                return redirect(url_for("nuevo_usuario_mobile"))

            crear_usuario(nombre, usuario, correo, password, rol)
            registrar_movimiento(
                usuario=session["nombre"],
                accion=f"Creó el usuario: {usuario}",
                modulo="Usuarios",
                referencia=usuario,
            )
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("usuarios_mobile"))

        return render_template(
            "maquinaria_qr/nuevo_usuario_mobile.html",
            pagina="usuarios",
        )

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
            flash("Usuario actualizado correctamente.", "success")
            return redirect(url_for("usuarios"))

        return render_template("editar_usuario.html", usuario=usuario)

    @app.route("/usuarios/<int:id>/restablecer-password", methods=["POST"])
    @admin_required
    def restablecer_password_usuario(id):
        usuario = obtener_usuario_id(id)
        if not usuario:
            flash("Usuario no encontrado.", "danger")
            return redirect(url_for("usuarios"))

        try:
            password_temporal = generar_password_temporal()
            establecer_password_temporal(id, password_temporal)
            registrar_movimiento(
                usuario=session["nombre"],
                accion=f"Restableció la contraseña del usuario: {usuario.usuario}",
                modulo="Usuarios",
                referencia=str(id),
            )
            respuesta = make_response(
                render_template(
                    "password_temporal.html",
                    usuario=usuario,
                    password_temporal=password_temporal,
                )
            )
            respuesta.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            respuesta.headers["Pragma"] = "no-cache"
            respuesta.headers["Expires"] = "0"
            return respuesta
        except ValueError as error:
            flash(str(error), "danger")
            return redirect(url_for("editar_usuario", id=id))

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
