from flask import abort, flash, redirect, render_template, request, session, url_for

from database.mensajes import (
    enviar_mensaje,
    listar_conversaciones,
    listar_mensajes,
    listar_usuarios_mensajeria,
    marcar_como_leidos,
    obtener_conversacion,
    obtener_o_crear_conversacion,
)


def registrar_rutas_mensajes(app, login_required):
    @app.route("/mensajes")
    @login_required
    def mensajes():
        usuario_id = session["usuario_id"]
        return render_template(
            "mensajes.html",
            conversaciones=listar_conversaciones(usuario_id),
            usuarios=listar_usuarios_mensajeria(usuario_id),
            conversacion=None,
            mensajes_conversacion=[],
        )

    @app.route("/mensajes/<int:conversacion_id>")
    @login_required
    def ver_conversacion(conversacion_id):
        usuario_id = session["usuario_id"]
        conversacion = obtener_conversacion(conversacion_id, usuario_id)
        if not conversacion:
            abort(404)
        marcar_como_leidos(conversacion_id, usuario_id)
        return render_template(
            "mensajes.html",
            conversaciones=listar_conversaciones(usuario_id),
            usuarios=listar_usuarios_mensajeria(usuario_id),
            conversacion=conversacion,
            mensajes_conversacion=(
                listar_mensajes(conversacion_id, usuario_id) or []
            ),
        )

    @app.route("/mensajes/nuevo", methods=["POST"])
    @login_required
    def nueva_conversacion():
        try:
            destinatario_id = int(request.form.get("destinatario_id") or 0)
            conversacion_id = obtener_o_crear_conversacion(
                session["usuario_id"], destinatario_id
            )
            contenido = request.form.get("contenido") or ""
            if contenido.strip():
                enviar_mensaje(
                    conversacion_id, session["usuario_id"], contenido
                )
            return redirect(url_for(
                "ver_conversacion", conversacion_id=conversacion_id
            ))
        except (TypeError, ValueError) as error:
            flash(str(error), "warning")
            return redirect(url_for("mensajes"))

    @app.route("/mensajes/<int:conversacion_id>/enviar", methods=["POST"])
    @login_required
    def enviar_mensaje_route(conversacion_id):
        try:
            enviar_mensaje(
                conversacion_id,
                session["usuario_id"],
                request.form.get("contenido"),
            )
        except PermissionError:
            abort(403)
        except ValueError as error:
            flash(str(error), "warning")
        return redirect(url_for(
            "ver_conversacion", conversacion_id=conversacion_id
        ))
