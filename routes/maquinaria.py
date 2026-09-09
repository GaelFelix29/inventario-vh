from flask import flash, redirect, render_template, request, session, url_for

from database.maquinarias import (
    insertar_maquinaria,
    obtener_estadisticas_maquinarias,
    obtener_todas_maquinas,
    obtener_ubicaciones,
    siguiente_id_activo,
)


def registrar_rutas_maquinaria(
    app,
    login_required,
    roles_required,
    registrar_movimiento,
):
    """Registra inicialmente el listado y alta de maquinaria."""

    @app.route("/maquinarias")
    @login_required
    def lista_maquinarias():
        return render_template(
            "maquina.html",
            maquinas=obtener_todas_maquinas(),
            estadisticas=obtener_estadisticas_maquinarias(),
            ubicaciones=obtener_ubicaciones(),
        )

    @app.route("/maquinarias/nuevo", methods=["GET", "POST"])
    @login_required
    @roles_required("Administrador")
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
                "observaciones": request.form["observaciones"],
            }

            insertar_maquinaria(datos)
            registrar_movimiento(
                usuario=session["nombre"],
                accion="Registró un nuevo activo",
                modulo="Maquinaria",
                referencia=request.form["id_activo"],
            )
            flash("Activo registrado correctamente.", "success")
            return redirect(url_for("lista_maquinarias"))

        return render_template(
            "nueva_maquinaria.html",
            siguiente_id=siguiente_id_activo(),
        )
