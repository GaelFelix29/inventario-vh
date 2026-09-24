from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for

from database.mensajes import (
    enviar_mensaje,
    listar_conversaciones,
    listar_mensajes,
    listar_mensajes_nuevos,
    listar_usuarios_mensajeria,
    marcar_como_leidos,
    obtener_conversacion,
    obtener_mensaje,
    obtener_o_crear_conversacion,
)


def registrar_rutas_mensajes(app, login_required, es_dispositivo_movil):
    def contexto_vista():
        movil = es_dispositivo_movil()
        return {
            "base_mensajes": (
                "maquinaria_qr/base_mobile.html" if movil else "base.html"
            ),
            "pagina": "mensajes",
        }

    @app.route("/mensajes")
    @login_required
    def mensajes():
        usuario_id = session["usuario_id"]
        return render_template(
            "mensajes.html",
            **contexto_vista(),
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
            **contexto_vista(),
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

    @app.route("/mensajes/<int:conversacion_id>/actualizar", methods=["POST"])
    @login_required
    def actualizar_conversacion(conversacion_id):
        datos = request.get_json(silent=True) or {}
        try:
            despues_de = max(0, int(datos.get("despues_de") or 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Referencia inválida."}), 400

        filas = listar_mensajes_nuevos(
            conversacion_id, session["usuario_id"], despues_de
        )
        return jsonify({
            "ok": True,
            "mensajes": [_serializar_mensaje(fila) for fila in filas],
        })

    @app.route("/mensajes/<int:conversacion_id>/api/enviar", methods=["POST"])
    @login_required
    def enviar_mensaje_api(conversacion_id):
        datos = request.get_json(silent=True) or {}
        try:
            mensaje_id = enviar_mensaje(
                conversacion_id,
                session["usuario_id"],
                datos.get("contenido"),
            )
            fila = obtener_mensaje(mensaje_id, session["usuario_id"])
            return jsonify({"ok": True, "mensaje": _serializar_mensaje(fila)})
        except PermissionError:
            abort(403)
        except ValueError as error:
            return jsonify({"ok": False, "error": str(error)}), 400


def _serializar_mensaje(fila):
    return {
        "id": fila["id"],
        "remitente_id": fila["remitente_id"],
        "remitente_nombre": fila["remitente_nombre"],
        "contenido": fila["contenido"],
        "enviado_en": fila["enviado_en"].strftime("%d/%m/%Y %H:%M"),
    }
