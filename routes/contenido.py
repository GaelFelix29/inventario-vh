from flask import flash, jsonify, redirect, request, session, url_for

from database.maquinarias import (
    buscar_activos,
    finalizar_revision_contenido,
    iniciar_revision_contenido,
    obtener_maquinaria_detalle,
    reabrir_revision_contenido,
    retirar_contenido_activo,
    vincular_contenido_activo,
)

from services.contenido_activos import convertir_en_conjunto, registrar_accesorio_contenido, buscar_accesorios_disponibles


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

    @app.route('/accesorios/disponibles-conjunto')
    @login_required
    @roles_required('Administrador', 'Mantenimiento')
    def buscar_accesorios_conjunto():
        consulta = request.args.get('q', '').strip()
        if len(consulta) < 2:
            return jsonify([])
        return jsonify(buscar_accesorios_disponibles(consulta))

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
        except Exception:
            app.logger.exception('Error iniciando revisión de contenido')
            flash('No fue posible iniciar la revisión. Intente de nuevo.', 'danger')
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
        except Exception:
            app.logger.exception('Error finalizando revisión de contenido')
            flash('No fue posible finalizar la revisión. Intente de nuevo.', 'danger')
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
                    "imagen_url": activo.get("imagen_url"),
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
        except ValueError as error:
            flash(str(error), "warning")
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
        except Exception:
            app.logger.exception('Error retirando contenido')
            flash('No fue posible retirar el accesorio. Su registro se conserva.', 'danger')
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
    @roles_required("Administrador")
    def registrar_accesorio_desde_contenido(id_activo):
        try:
            nuevo_id = registrar_accesorio_contenido(id_activo, request.form, session["nombre"])
        except ValueError as error:
            flash(str(error), "warning")
        except Exception:
            app.logger.exception("Error registrando contenido")
            flash("No se guardó el accesorio. Intente de nuevo; si persiste, contacte al administrador.", "danger")
        else:
            flash(f"{nuevo_id} registrado con expediente propio y vinculado al conjunto.", "success")
        return redirigir(id_activo)

    @app.route("/maquinarias/<id_activo>/contenido/configurar", methods=["POST"])
    @login_required
    @roles_required("Administrador")
    def configurar_conjunto_route(id_activo):
        try:
            convertir_en_conjunto(id_activo, session["nombre"])
        except ValueError as error:
            flash(str(error), "warning")
        except Exception:
            app.logger.exception("Error configurando conjunto")
            flash("No fue posible configurar el conjunto.", "danger")
        else:
            flash("Conjunto configurado. Inicie una revisión para identificar sus piezas.", "success")
        return redirigir(id_activo)
