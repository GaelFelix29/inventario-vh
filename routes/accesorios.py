from flask import flash, jsonify, redirect, request, session, url_for

from database.maquinarias import (
    actualizar_categoria_accesorio,
    asignar_accesorio_maquinaria,
    buscar_maquinarias_asignables,
    crear_categoria_y_clasificar_accesorio,
    liberar_accesorio_maquinaria,
)


def registrar_rutas_accesorios(app, login_required):
    """Registra clasificación y asignación de accesorios."""

    def puede_gestionar():
        return session.get("rol") in ["Administrador", "Mantenimiento"]

    def redirigir(id_accesorio):
        retorno_id = (
            request.form.get("retorno_id") or id_accesorio
        ).strip().upper()
        origen = request.form.get("origen")
        retorno_vista = request.form.get("retorno_vista")

        if origen == "qr":
            if retorno_vista == "contenido":
                return redirect(
                    url_for("qr_contenido", id_activo=retorno_id)
                )
            return redirect(
                url_for("maquinaria_qr", id_activo=retorno_id)
            )
        return redirect(
            url_for("expediente_maquinaria", id_activo=retorno_id)
        )

    @app.route("/accesorios/<id_accesorio>/categoria", methods=["POST"])
    @login_required
    def actualizar_categoria_accesorio_route(id_accesorio):
        if not puede_gestionar():
            flash("No tiene permisos para clasificar accesorios.", "danger")
            return redirigir(id_accesorio)

        try:
            categoria = actualizar_categoria_accesorio(
                id_activo=id_accesorio,
                categoria_accesorio_id=request.form.get(
                    "categoria_accesorio_id"
                ),
                usuario=session["nombre"],
            )
        except ValueError as error:
            flash(str(error), "warning")
        except Exception as error:
            print("ERROR ACTUALIZANDO CATEGORÍA DEL ACCESORIO:", error)
            flash("No fue posible actualizar la categoría.", "danger")
        else:
            flash(
                f"{id_accesorio} fue clasificado como {categoria['nombre']}.",
                "success",
            )
        return redirigir(id_accesorio)

    @app.route("/accesorios/<id_accesorio>/asignacion", methods=["POST"])
    @login_required
    def asignar_accesorio_maquinaria_route(id_accesorio):
        if not puede_gestionar():
            flash("No tiene permisos para asignar accesorios.", "danger")
            return redirigir(id_accesorio)

        try:
            resultado = asignar_accesorio_maquinaria(
                id_accesorio=id_accesorio,
                id_maquinaria=request.form.get("id_maquinaria"),
                usuario=session["nombre"],
                observaciones=request.form.get("observaciones"),
            )
        except ValueError as error:
            flash(str(error), "warning")
        except Exception as error:
            print("ERROR ASIGNANDO ACCESORIO:", error)
            flash("No fue posible guardar la asignación.", "danger")
        else:
            if resultado["maquinaria_anterior"]:
                mensaje = (
                    f"{id_accesorio} cambió de "
                    f"{resultado['maquinaria_anterior']} a "
                    f"{resultado['id_maquinaria']}."
                )
            else:
                mensaje = (
                    f"{id_accesorio} fue asignado a "
                    f"{resultado['id_maquinaria']}."
                )
            flash(mensaje, "success")
        return redirigir(id_accesorio)

    @app.route(
        "/accesorios/<id_accesorio>/asignacion/liberar",
        methods=["POST"],
    )
    @login_required
    def liberar_accesorio_maquinaria_route(id_accesorio):
        if not puede_gestionar():
            flash("No tiene permisos para liberar accesorios.", "danger")
            return redirigir(id_accesorio)

        try:
            id_maquinaria = liberar_accesorio_maquinaria(
                id_accesorio=id_accesorio,
                usuario=session["nombre"],
            )
        except ValueError as error:
            flash(str(error), "warning")
        except Exception as error:
            print("ERROR LIBERANDO ACCESORIO:", error)
            flash("No fue posible liberar el accesorio.", "danger")
        else:
            flash(
                f"{id_accesorio} fue liberado de {id_maquinaria}.",
                "success",
            )
        return redirigir(id_accesorio)

    @app.route("/buscar-maquinarias-asignables")
    @login_required
    def buscar_maquinarias_asignables_ajax():
        if not puede_gestionar():
            return jsonify([]), 403

        texto = request.args.get("q", "").strip()
        id_accesorio = request.args.get("id_accesorio", "").strip().upper()
        if len(texto) < 2:
            return jsonify([])

        maquinarias = buscar_maquinarias_asignables(
            texto=texto,
            id_accesorio=id_accesorio,
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
        methods=["POST"],
    )
    @login_required
    def crear_categoria_accesorio_route(id_accesorio):
        if not puede_gestionar():
            flash("No tiene permisos para crear categorías.", "danger")
            return redirigir(id_accesorio)

        try:
            categoria = crear_categoria_y_clasificar_accesorio(
                id_activo=id_accesorio,
                nombre=request.form.get("nombre_categoria"),
                descripcion=request.form.get("descripcion_categoria"),
                usuario=session["nombre"],
            )
        except ValueError as error:
            flash(str(error), "warning")
        except Exception as error:
            print("ERROR CREANDO CATEGORÍA DE ACCESORIO:", error)
            flash("No fue posible crear la categoría.", "danger")
        else:
            flash(
                f"Se creó la categoría {categoria['nombre']} y se asignó a "
                f"{id_accesorio}.",
                "success",
            )
        return redirigir(id_accesorio)
