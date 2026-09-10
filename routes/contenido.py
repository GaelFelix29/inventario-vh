from flask import flash, jsonify, redirect, request, session, url_for

from database.maquinarias import (
    buscar_activos,
    finalizar_revision_contenido,
    iniciar_revision_contenido,
    insertar_maquinaria,
    obtener_maquinaria_detalle,
    reabrir_revision_contenido,
    retirar_contenido_activo,
    siguiente_id_activo,
    vincular_contenido_activo,
)


def registrar_rutas_contenido(
    app,
    login_required,
    roles_required,
    registrar_movimiento,
):
    """Registra la revisión y administración del contenido de activos."""

    def redirigir(id_activo):
        if request.form.get("origen") == "qr":
            return redirect(url_for("qr_contenido", id_activo=id_activo))
        return redirect(
            url_for("expediente_maquinaria", id_activo=id_activo)
        )

    @app.route(
        "/maquinarias/<id_activo>/revision-contenido/reabrir",
        methods=["POST"],
    )
    @login_required
    def reabrir_revision_contenido_route(id_activo):
        if session.get("rol") not in ["Administrador", "Mantenimiento"]:
            flash(
                "No tiene permisos para iniciar una nueva revisión.",
                "danger",
            )
            return redirigir(id_activo)

        try:
            reabrir_revision_contenido(
                id_activo=id_activo,
                usuario=session["nombre"],
            )
        except ValueError as error:
            flash(str(error), "warning")
        except Exception as error:
            print("ERROR REABRIENDO REVISIÓN:", error)
            flash("No fue posible iniciar una nueva revisión.", "danger")
        else:
            flash("Se inició una nueva revisión de contenido.", "success")
        return redirigir(id_activo)

    @app.route(
        "/maquinarias/<id_activo>/revision-contenido/iniciar",
        methods=["POST"],
    )
    @login_required
    @roles_required("Administrador", "Mantenimiento")
    def iniciar_revision_contenido_route(id_activo):
        try:
            iniciar_revision_contenido(id_activo, session["nombre"])
        except ValueError as error:
            flash(str(error), "warning")
        else:
            flash(
                "La revisión de contenido fue iniciada correctamente.",
                "success",
            )
        return redirigir(id_activo)

    @app.route(
        "/maquinarias/<id_activo>/revision-contenido/finalizar",
        methods=["POST"],
    )
    @login_required
    @roles_required("Administrador", "Mantenimiento")
    def finalizar_revision_contenido_route(id_activo):
        try:
            finalizar_revision_contenido(id_activo, session["nombre"])
        except ValueError as error:
            flash(str(error), "warning")
        else:
            flash(
                "La revisión de contenido fue finalizada correctamente.",
                "success",
            )
        return redirigir(id_activo)

    @app.route("/buscar-activos")
    @login_required
    def buscar_activos_ajax():
        texto = request.args.get("q", "").strip()
        if len(texto) < 2:
            return jsonify([])

        return jsonify(
            [
                {
                    "id": activo["id_activo"],
                    "text": activo["id_activo"],
                    "descripcion": activo["descripcion"],
                    "categoria": activo["categoria"],
                    "marca": activo["marca"],
                    "ubicacion": activo["ubicacion"],
                }
                for activo in buscar_activos(texto)
            ]
        )

    @app.route(
        "/maquinarias/<id_activo>/contenido/vincular",
        methods=["POST"],
    )
    @login_required
    @roles_required("Administrador", "Mantenimiento")
    def vincular_contenido_route(id_activo):
        activo_relacionado = request.form.get("activo_relacionado")
        observaciones = request.form.get("observaciones")

        if not activo_relacionado:
            flash("Debe seleccionar un activo.", "warning")
            return redirigir(id_activo)
        if activo_relacionado == id_activo:
            flash("Un activo no puede contenerse a sí mismo.", "danger")
            return redirigir(id_activo)

        try:
            vincular_contenido_activo(
                activo_origen=id_activo,
                activo_relacionado=activo_relacionado,
                usuario=session["nombre"],
                observaciones=observaciones,
            )
            registrar_movimiento(
                usuario=session["nombre"],
                accion=(
                    f"Vinculó el activo {activo_relacionado} como contenido"
                ),
                modulo="Accesorios",
                referencia=id_activo,
            )
        except Exception as error:
            print("ERROR VINCULANDO CONTENIDO:", error)
            flash(
                "No fue posible vincular el activo. Verifique que no esté "
                "relacionado previamente.",
                "danger",
            )
        else:
            flash(
                f"{activo_relacionado} fue agregado al contenido de "
                f"{id_activo}.",
                "success",
            )
        return redirigir(id_activo)

    @app.route(
        "/maquinarias/<id_activo>/contenido/<int:relacion_id>/retirar",
        methods=["POST"],
    )
    @login_required
    @roles_required("Administrador", "Mantenimiento")
    def retirar_contenido_route(id_activo, relacion_id):
        try:
            activo_retirado = retirar_contenido_activo(
                activo_origen=id_activo,
                relacion_id=relacion_id,
                usuario=session["nombre"],
            )
        except ValueError as error:
            flash(str(error), "warning")
        else:
            flash(
                f"{activo_retirado} fue retirado del contenido de "
                f"{id_activo}.",
                "success",
            )
        return redirigir(id_activo)

    @app.route(
        "/maquinarias/<id_activo>/contenido/registrar",
        methods=["POST"],
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
            return redirigir(id_activo)

        activo_origen = obtener_maquinaria_detalle(id_activo)
        if not activo_origen:
            flash("El activo origen no existe.", "danger")
            return redirigir(id_activo)
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
                observaciones=(
                    f"Accesorio registrado desde {id_activo}. "
                    f"{observaciones}"
                ),
            )
            registrar_movimiento(
                usuario=session["nombre"],
                accion=(
                    f"Registró el accesorio {nuevo_id} desde {id_activo}"
                ),
                modulo="Accesorios",
                referencia=nuevo_id,
            )
            registrar_movimiento(
                usuario=session["nombre"],
                accion=f"Vinculó {nuevo_id} como contenido",
                modulo="Accesorios",
                referencia=id_activo,
            )
        except Exception as error:
            print("ERROR REGISTRANDO ACCESORIO:", error)
            flash("No fue posible registrar el accesorio.", "danger")
        else:
            flash(
                f"Accesorio {nuevo_id} registrado y vinculado correctamente.",
                "success",
            )
        return redirigir(id_activo)
