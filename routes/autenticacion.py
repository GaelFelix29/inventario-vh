from flask import flash, redirect, render_template, request, session, url_for

from database.usuarios import (
    actualizar_password,
    obtener_usuario,
    obtener_usuario_id,
    verificar_password,
)


def registrar_rutas_autenticacion(
    app,
    login_required,
    registrar_movimiento,
    es_url_interna,
):
    """Registra acceso, seguridad de cuenta y cierre de sesión."""

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if "usuario_id" in session:
            if session.get("debe_cambiar_password", False):
                return redirect(url_for("cambiar_password_obligatorio"))
            next_page = session.pop("next_url", None)
            if es_url_interna(next_page):
                return redirect(next_page)
            return redirect(url_for("inicio"))

        if request.method == "POST":
            usuario = request.form.get("usuario", "").strip()
            password = request.form.get("password", "")
            datos = obtener_usuario(usuario)

            if datos and verificar_password(password, datos.password):
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
                    modulo="Login",
                )

                if session["debe_cambiar_password"]:
                    flash(
                        "Debes crear una contraseña nueva para continuar.",
                        "warning",
                    )
                    return redirect(
                        url_for("cambiar_password_obligatorio")
                    )

                flash(f"Bienvenido {datos.nombre}", "success")
                if es_url_interna(next_page):
                    return redirect(next_page)
                return redirect(url_for("inicio"))

            flash("Usuario o contraseña incorrectos.", "danger")

        return render_template("login.html")

    @app.route(
        "/cambiar-password-obligatorio",
        methods=["GET", "POST"],
    )
    def cambiar_password_obligatorio():
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        if not session.get("debe_cambiar_password", False):
            return redirect(url_for("inicio"))

        usuario_actual = obtener_usuario_id(session["usuario_id"])
        if not usuario_actual:
            session.clear()
            flash("No fue posible encontrar tu cuenta.", "danger")
            return redirect(url_for("login"))

        if request.method == "POST":
            password_nuevo = request.form.get("password_nuevo", "")
            confirmar = request.form.get("confirmar_password", "")
            if len(password_nuevo) < 10:
                flash(
                    "La contraseña debe tener al menos 10 caracteres.",
                    "danger",
                )
                return render_template("cambiar_password_obligatorio.html")
            if password_nuevo != confirmar:
                flash("Las contraseñas no coinciden.", "danger")
                return render_template("cambiar_password_obligatorio.html")
            if verificar_password(password_nuevo, usuario_actual["password"]):
                flash(
                    "La nueva contraseña debe ser diferente a la contraseña "
                    "temporal.",
                    "danger",
                )
                return render_template("cambiar_password_obligatorio.html")

            try:
                actualizar_password(session["usuario_id"], password_nuevo)
            except ValueError as error:
                flash(str(error), "danger")
                return render_template("cambiar_password_obligatorio.html")

            session["debe_cambiar_password"] = False
            session.modified = True
            registrar_movimiento(
                usuario=session["nombre"],
                accion=(
                    "Cambió la contraseña temporal por una contraseña personal"
                ),
                modulo="Seguridad",
                referencia=str(session["usuario_id"]),
            )
            flash("Tu contraseña fue actualizada correctamente.", "success")
            return redirect(url_for("inicio"))

        return render_template("cambiar_password_obligatorio.html")

    @app.before_request
    def verificar_cambio_password_obligatorio():
        rutas_libres = {
            "static",
            "login",
            "logout",
            "cambiar_password_obligatorio",
        }
        if request.endpoint in rutas_libres or "usuario_id" not in session:
            return None

        usuario_actual = obtener_usuario_id(session["usuario_id"])
        if not usuario_actual or not usuario_actual.activo:
            session.clear()
            flash("Tu cuenta ya no está disponible.", "warning")
            return redirect(url_for("login"))

        debe_cambiar = bool(usuario_actual.debe_cambiar_password)
        session["debe_cambiar_password"] = debe_cambiar
        if debe_cambiar:
            return redirect(url_for("cambiar_password_obligatorio"))
        return None

    @app.route("/logout")
    @login_required
    def logout():
        registrar_movimiento(
            usuario=session["nombre"],
            accion="Cerró sesión",
            modulo="Login",
        )
        session.clear()
        flash("Sesión cerrada correctamente.", "info")
        return redirect(url_for("login"))
