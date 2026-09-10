from flask import flash, redirect, render_template, request, session, url_for

from database.usuarios import (
    actualizar_password,
    actualizar_perfil,
    obtener_usuario_id,
    verificar_password,
)


AVATARES_PERFIL = [
    {"id": "usuario", "nombre": "Clásico", "icono": "bi-person-fill", "clase": "avatar-verde"},
    {"id": "finanzas", "nombre": "Finanzas", "icono": "bi-graph-up-arrow", "clase": "avatar-azul"},
    {"id": "mantenimiento", "nombre": "Mantenimiento", "icono": "bi-tools", "clase": "avatar-naranja"},
    {"id": "administracion", "nombre": "Administración", "icono": "bi-briefcase-fill", "clase": "avatar-morado"},
    {"id": "seguridad", "nombre": "Seguridad", "icono": "bi-shield-check", "clase": "avatar-rojo"},
    {"id": "inventario", "nombre": "Inventario", "icono": "bi-box-seam-fill", "clase": "avatar-turquesa"},
    {"id": "logistica", "nombre": "Logística", "icono": "bi-truck", "clase": "avatar-amarillo"},
    {"id": "ejecutivo", "nombre": "Ejecutivo", "icono": "bi-person-badge-fill", "clase": "avatar-oscuro"},
]


def registrar_rutas_perfil(
    app,
    login_required,
    registrar_movimiento,
    es_dispositivo_movil,
):
    """Registra la consulta y edición del perfil personal."""

    @app.route("/perfil")
    @login_required
    def perfil():
        usuario_actual = obtener_usuario_id(session["usuario_id"])
        if not usuario_actual:
            session.clear()
            flash("No fue posible encontrar tu cuenta.", "danger")
            return redirect(url_for("login"))

        avatar_actual = next(
            (
                avatar
                for avatar in AVATARES_PERFIL
                if avatar["id"] == (usuario_actual["avatar"] or "usuario")
            ),
            AVATARES_PERFIL[0],
        )
        if es_dispositivo_movil():
            return render_template(
                "maquinaria_qr/perfil_mobile.html",
                usuario=usuario_actual,
                avatar_actual=avatar_actual,
                pagina="perfil",
            )
        return render_template(
            "perfil.html",
            usuario=usuario_actual,
            avatar_actual=avatar_actual,
        )

    @app.route("/perfil/editar", methods=["GET", "POST"])
    @login_required
    def editar_perfil():
        usuario_actual = obtener_usuario_id(session["usuario_id"])
        if not usuario_actual:
            session.clear()
            flash("No fue posible encontrar tu cuenta.", "danger")
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
                plantilla_base=plantilla_base,
            )

        if request.method == "POST":
            nombre = (request.form.get("nombre") or "").strip()
            avatar = (request.form.get("avatar") or "usuario").strip().lower()
            password_actual = request.form.get("password_actual") or ""
            password_nuevo = request.form.get("password_nuevo") or ""
            confirmar = request.form.get("confirmar_password") or ""

            if not nombre:
                flash("El nombre es obligatorio.", "warning")
                return mostrar_formulario()
            if len(nombre) > 150:
                flash("El nombre es demasiado largo.", "warning")
                return mostrar_formulario()
            if not verificar_password(
                password_actual,
                usuario_actual["password"],
            ):
                flash("La contraseña actual no es correcta.", "danger")
                return mostrar_formulario()
            if password_nuevo and len(password_nuevo) < 10:
                flash(
                    "La contraseña nueva debe tener al menos 10 caracteres.",
                    "warning",
                )
                return mostrar_formulario()
            if password_nuevo and password_nuevo != confirmar:
                flash("Las contraseñas nuevas no coinciden.", "warning")
                return mostrar_formulario()

            try:
                actualizar_perfil(
                    id_usuario=session["usuario_id"],
                    nombre=nombre,
                    avatar=avatar,
                )
                if password_nuevo:
                    actualizar_password(session["usuario_id"], password_nuevo)
            except ValueError as error:
                flash(str(error), "warning")
                return mostrar_formulario()
            except Exception as error:
                print("ERROR ACTUALIZANDO PERFIL:", error)
                flash("No fue posible actualizar el perfil.", "danger")
                return mostrar_formulario()

            session["nombre"] = nombre
            session["avatar"] = avatar
            registrar_movimiento(
                usuario=nombre,
                accion="Actualizó su perfil",
                modulo="Usuarios",
                referencia=str(session["usuario_id"]),
            )
            flash("Tu perfil fue actualizado correctamente.", "success")
            return redirect(url_for("perfil"))

        return mostrar_formulario()
