import base64
from io import BytesIO

import qrcode
from flask import abort, current_app, flash, redirect, render_template, request, send_file, session, url_for

from database.maquinarias import (
    insertar_maquinaria,
    actualizar_maquinaria,
    obtener_accesorios_asignados_maquinaria,
    obtener_asignacion_activa_accesorio,
    obtener_categorias_accesorios,
    obtener_categorias_maquinaria,
    obtener_contenido_activo,
    obtener_estadisticas_maquinarias,
    obtener_historial_asignaciones_accesorio,
    obtener_mantenimiento_en_proceso,
    obtener_maquinaria,
    obtener_maquinaria_detalle,
    obtener_todas_maquinas,
    obtener_ubicaciones,
    obtener_activos_vecinos,
    siguiente_id_activo,
)
from database.aduanas import estado_expediente_aduanal, obtener_aduana
from database.documentos import listar_documentos
from database.solicitudes_baja import obtener_traslado_en_proceso
from models.auditoria_model import (
    obtener_historial_activo,
    registrar_activo_reciente,
)
from services.reportes_maquinaria import crear_excel_maquinaria, crear_pdf_maquinaria, filtrar_maquinarias


def registrar_rutas_maquinaria(
    app,
    login_required,
    roles_required,
    registrar_movimiento,
    es_dispositivo_movil,
):
    """Registra inicialmente el listado y alta de maquinaria."""

    def _categoria_formulario():
        categoria = request.form.get("categoria", "").strip()
        if categoria == "__NUEVA__":
            categoria = request.form.get("categoria_nueva", "").strip()
        return categoria

    @app.route("/maquinarias")
    @login_required
    def lista_maquinarias():
        return render_template(
            "maquina.html",
            maquinas=obtener_todas_maquinas(),
            estadisticas=obtener_estadisticas_maquinarias(),
            ubicaciones=obtener_ubicaciones(),
            categorias_maquinaria=obtener_categorias_maquinaria(),
        )

    def _filtros_reporte_maquinaria():
        return {
            clave: request.args.get(clave, "").strip()
            for clave in ("q", "tipo", "estado", "ubicacion", "categoria")
        }

    @app.route("/maquinarias/reportes/excel")
    @login_required
    def reporte_maquinarias_excel():
        filtros = _filtros_reporte_maquinaria()
        maquinas = filtrar_maquinarias(obtener_todas_maquinas(), filtros)
        archivo = crear_excel_maquinaria(
            maquinas, filtros, session.get("nombre", "Usuario")
        )
        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Exportó reporte Excel de maquinaria ({len(maquinas)} registros)",
            modulo="Maquinaria",
            referencia="REPORTE",
        )
        return send_file(
            archivo,
            as_attachment=True,
            download_name="reporte_maquinaria.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.route("/maquinarias/reportes/pdf")
    @login_required
    def reporte_maquinarias_pdf():
        filtros = _filtros_reporte_maquinaria()
        maquinas = filtrar_maquinarias(obtener_todas_maquinas(), filtros)
        archivo = crear_pdf_maquinaria(
            maquinas,
            filtros,
            session.get("nombre", "Usuario"),
            current_app.root_path + "/static/img/logo.png",
        )
        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Exportó reporte PDF de maquinaria ({len(maquinas)} registros)",
            modulo="Maquinaria",
            referencia="REPORTE",
        )
        return send_file(
            archivo,
            as_attachment=True,
            download_name="reporte_maquinaria.pdf",
            mimetype="application/pdf",
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
                "categoria": _categoria_formulario(),
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
            categorias_maquinaria=obtener_categorias_maquinaria(),
        )

    @app.route("/m/maquinarias/nuevo", methods=["GET", "POST"])
    @login_required
    @roles_required("Administrador")
    def nueva_maquinaria_mobile():
        if request.method == "POST":
            cantidad = int(request.form["cantidad"] or 1)
            precio = float(request.form["precio_unitario_us"] or 0)
            total = cantidad * precio
            valor_mx = float(request.form["valor_mx"] or 0)

            datos = {
                "id_activo": request.form["id_activo"],
                "categoria": _categoria_formulario(),
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
                "valor_mx": valor_mx,
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
            return redirect(url_for("maquinarias_mobile"))

        return render_template(
            "maquinaria_qr/nueva_maquinaria_mobile.html",
            siguiente_id=siguiente_id_activo(),
            categorias_maquinaria=obtener_categorias_maquinaria(),
            pagina="maquinaria",
        )

    @app.route("/maquinarias/<id_activo>")
    @login_required
    def expediente_maquinaria(id_activo):
        if es_dispositivo_movil():
            return redirect(url_for("maquinaria_qr", id_activo=id_activo))

        maquina = obtener_maquinaria_detalle(id_activo)
        if not maquina:
            flash("El activo no existe.", "danger")
            return redirect(url_for("lista_maquinarias"))

        contenido_activo = obtener_contenido_activo(id_activo)
        es_contenedor = bool(maquina.get("es_contenedor"))
        es_accesorio = (
            not es_contenedor
            and (maquina.get("categoria") or "").strip().upper()
            == "ACCESORIO"
        )

        categorias_accesorios = []
        asignacion_activa = None
        historial_asignaciones = []
        accesorios_asignados = []

        if es_contenedor or es_accesorio:
            categorias_accesorios = obtener_categorias_accesorios()

        if es_accesorio:
            asignacion_activa = obtener_asignacion_activa_accesorio(id_activo)
            historial_asignaciones = (
                obtener_historial_asignaciones_accesorio(id_activo)
            )
        elif not es_contenedor:
            accesorios_asignados = (
                obtener_accesorios_asignados_maquinaria(id_activo)
            )

        registrar_activo_reciente(
            usuario=session["nombre"],
            id_activo=id_activo,
        )

        aduana = obtener_aduana(id_activo)
        es_nacional = False
        es_importado = False
        es_pendiente = False
        es_sin_clasificar = False
        es_reingreso = False

        if aduana:
            origen = (aduana.get("origen") or "").strip().upper()
            if origen in ["NACIONAL", "MEXICO"]:
                es_nacional = True
            elif origen == "PENDIENTE":
                es_pendiente = True
            elif origen == "NA":
                es_sin_clasificar = True
            elif origen == "REINGRESO":
                es_reingreso = True
            else:
                es_importado = True

        estado_aduana = estado_expediente_aduanal(aduana)
        historial = obtener_historial_activo(id_activo)
        vecinos = obtener_activos_vecinos(id_activo)
        documentos = listar_documentos(id_activo)
        traslado_en_proceso = obtener_traslado_en_proceso(id_activo)
        mantenimiento_en_proceso = obtener_mantenimiento_en_proceso(id_activo)

        return render_template(
            "expediente_maquinaria.html",
            maquina=maquina,
            aduana=aduana,
            estado_aduana=estado_aduana,
            historial=historial,
            documentos=documentos,
            traslado_en_proceso=traslado_en_proceso,
            mantenimiento_en_proceso=mantenimiento_en_proceso,
            contenido_activo=contenido_activo,
            anterior=vecinos["anterior"],
            siguiente=vecinos["siguiente"],
            es_nacional=es_nacional,
            es_importado=es_importado,
            es_pendiente=es_pendiente,
            es_sin_clasificar=es_sin_clasificar,
            es_reingreso=es_reingreso,
            es_accesorio=es_accesorio,
            categorias_accesorios=categorias_accesorios,
            asignacion_activa=asignacion_activa,
            historial_asignaciones=historial_asignaciones,
            accesorios_asignados=accesorios_asignados,
        )

    @app.route("/maquinarias/<id_activo>/imprimir")
    @login_required
    def imprimir_maquinaria(id_activo):
        maquina = obtener_maquinaria_detalle(id_activo)
        if not maquina:
            flash("El activo no existe.", "danger")
            return redirect(url_for("lista_maquinarias"))

        return render_template("imprimir-qr.html", maquina=maquina)

    @app.route("/maquinarias/<id_activo>/qr")
    @login_required
    def qr_maquinaria(id_activo):
        maquina = obtener_maquinaria_detalle(id_activo)
        if not maquina:
            flash("El activo no existe.", "danger")
            return redirect(url_for("lista_maquinarias"))

        url = url_for(
            "expediente_maquinaria",
            id_activo=id_activo,
            _external=True,
        )
        imagen = qrcode.make(url)
        buffer = BytesIO()
        imagen.save(buffer, format="PNG")
        buffer.seek(0)
        qr = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return render_template("qr_maquinaria.html", maquina=maquina, qr=qr)

    @app.route("/maquinarias/<id_activo>/editar", methods=["GET", "POST"])
    @login_required
    def editar_maquinaria(id_activo):
        if session.get("rol") != "Administrador":
            flash("No tiene permisos para editar activos.", "danger")
            return redirect(url_for("lista_maquinarias"))

        maquina = obtener_maquinaria(id_activo)
        if not maquina:
            flash("El activo no existe.", "danger")
            return redirect(url_for("lista_maquinarias"))

        if request.method == "POST":
            datos = {
                "id_activo": id_activo,
                "categoria": _categoria_formulario(),
                "descripcion": request.form["descripcion"],
                "cantidad": int(request.form["cantidad"] or 1),
                "marca": request.form["marca"],
                "modelo": request.form["modelo"],
                "numero_serie": request.form["numero_serie"],
                "serie_interna": request.form["serie_interna"],
                "proveedor": request.form["proveedor"],
                "ubicacion": request.form["ubicacion"],
                "precio_unitario_us": float(
                    request.form["precio_unitario_us"] or 0
                ),
                "total_us": float(request.form["total_us"] or 0),
                "valor_mx": float(request.form["valor_mx"] or 0),
                "fecha_alta": request.form["fecha_alta"],
                "observaciones": request.form["observaciones"],
            }
            actualizar_maquinaria(datos)
            registrar_movimiento(
                usuario=session["nombre"],
                accion="Actualizó información del activo",
                modulo="Maquinaria",
                referencia=id_activo,
            )
            flash(
                f"El activo {id_activo} fue actualizado correctamente.",
                "success",
            )
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )

        return render_template(
            "nueva_maquinaria.html",
            maquina=maquina,
            editar=True,
            categorias_maquinaria=obtener_categorias_maquinaria(),
        )

    @app.route(
        "/m/maquinarias/<id_activo>/editar",
        methods=["GET", "POST"],
    )
    @login_required
    @roles_required("Administrador")
    def editar_maquinaria_mobile(id_activo):
        maquina = obtener_maquinaria(id_activo)
        if not maquina:
            flash("El activo no existe.", "danger")
            return redirect(url_for("maquinarias_mobile"))

        if request.method == "POST":
            datos = {
                "id_activo": id_activo,
                "categoria": _categoria_formulario(),
                "descripcion": request.form["descripcion"],
                "cantidad": int(request.form["cantidad"] or 1),
                "marca": request.form["marca"],
                "modelo": request.form["modelo"],
                "numero_serie": request.form["numero_serie"],
                "serie_interna": request.form["serie_interna"],
                "proveedor": request.form["proveedor"],
                "ubicacion": request.form["ubicacion"],
                "precio_unitario_us": float(
                    request.form["precio_unitario_us"] or 0
                ),
                "total_us": float(request.form["total_us"] or 0),
                "valor_mx": float(request.form["valor_mx"] or 0),
                "fecha_alta": request.form["fecha_alta"],
                "observaciones": request.form["observaciones"],
            }
            actualizar_maquinaria(datos)
            registrar_movimiento(
                usuario=session["nombre"],
                accion="Actualizó información del activo",
                modulo="Maquinaria",
                referencia=id_activo,
            )
            flash(
                f"El activo {id_activo} fue actualizado correctamente.",
                "success",
            )
            return redirect(url_for("maquinaria_qr", id_activo=id_activo))

        return render_template(
            "maquinaria_qr/editar_maquinaria_mobile.html",
            maquina=maquina,
            categorias_maquinaria=obtener_categorias_maquinaria(),
            pagina="maquinaria",
        )

    @app.route("/<id_activo>")
    @login_required
    def redireccion_qr_antiguo(id_activo):
        if not id_activo.startswith("ACT-"):
            abort(404)

        return redirect(
            url_for("expediente_maquinaria", id_activo=id_activo)
        )

    @app.route("/maquina/<id_activo>")
    @login_required
    def redireccion_qr_maquina(id_activo):
        return redirect(
            url_for("expediente_maquinaria", id_activo=id_activo),
            code=301,
        )

    @app.route("/qr/<id_activo>")
    @login_required
    def maquinaria_qr(id_activo):
        maquinaria = obtener_maquinaria(id_activo)
        if not maquinaria:
            abort(404)

        vecinos = obtener_activos_vecinos(id_activo)

        registrar_activo_reciente(
            usuario=session["nombre"],
            id_activo=id_activo,
        )

        aduana = obtener_aduana(id_activo)
        estado = estado_expediente_aduanal(aduana)
        traslado_en_proceso = obtener_traslado_en_proceso(id_activo)
        mantenimiento_en_proceso = obtener_mantenimiento_en_proceso(
            id_activo
        )
        contenido_activo = []
        es_contenedor = bool(maquinaria.get("es_contenedor"))
        es_accesorio = (
            not es_contenedor
            and (maquinaria.get("categoria") or "").strip().upper()
            == "ACCESORIO"
        )
        categorias_accesorios = []
        asignacion_activa = None
        historial_asignaciones = []
        accesorios_asignados = []

        if es_contenedor:
            contenido_activo = obtener_contenido_activo(id_activo)

        if es_contenedor or es_accesorio:
            categorias_accesorios = obtener_categorias_accesorios()

        if es_accesorio:
            asignacion_activa = obtener_asignacion_activa_accesorio(
                id_activo
            )
            historial_asignaciones = (
                obtener_historial_asignaciones_accesorio(id_activo)
            )
        elif not es_contenedor:
            accesorios_asignados = (
                obtener_accesorios_asignados_maquinaria(id_activo)
            )

        estado_ui = {
            "ACTIVO": {
                "clase": "activo",
                "icono": "bi-check-circle-fill",
            },
            "BAJA": {
                "clase": "baja",
                "icono": "bi-x-circle-fill",
            },
            "MANTENIMIENTO": {
                "clase": "mantenimiento",
                "icono": "bi-tools",
            },
            "EN TRASLADO": {
                "clase": "traslado",
                "icono": "bi-truck",
            },
        }.get(
            maquinaria["estado"],
            {
                "clase": "activo",
                "icono": "bi-circle-fill",
            },
        )

        return render_template(
            "maquinaria_qr/inicio.html",
            maquinaria=maquinaria,
            aduana=aduana,
            estado=estado,
            traslado_en_proceso=traslado_en_proceso,
            mantenimiento_en_proceso=mantenimiento_en_proceso,
            contenido_activo=contenido_activo,
            estado_ui=estado_ui,
            id_activo=id_activo,
            pagina="inicio",
            es_contenedor=es_contenedor,
            es_accesorio=es_accesorio,
            categorias_accesorios=categorias_accesorios,
            asignacion_activa=asignacion_activa,
            historial_asignaciones=historial_asignaciones,
            accesorios_asignados=accesorios_asignados,
            anterior=vecinos["anterior"],
            siguiente=vecinos["siguiente"],
        )

    @app.route("/qr/<id_activo>/contenido")
    @login_required
    def qr_contenido(id_activo):
        maquinaria = obtener_maquinaria(id_activo)
        if not maquinaria:
            abort(404)

        if maquinaria.get("es_contenedor") != 1:
            flash(
                "Este activo no está marcado como contenedor.",
                "warning",
            )
            return redirect(url_for("maquinaria_qr", id_activo=id_activo))

        return render_template(
            "maquinaria_qr/contenido.html",
            maquinaria=maquinaria,
            contenido_activo=obtener_contenido_activo(id_activo),
            categorias_accesorios=obtener_categorias_accesorios(),
            id_activo=id_activo,
            pagina="contenido",
        )

    @app.route("/qr/<id_activo>/expediente")
    @login_required
    def qr_expediente(id_activo):
        maquinaria = obtener_maquinaria(id_activo)
        aduana = obtener_aduana(id_activo)
        estado = estado_expediente_aduanal(aduana)
        documentos_map = {
            documento["tipo"]: documento
            for documento in listar_documentos(id_activo)
        }

        return render_template(
            "maquinaria_qr/expediente.html",
            maquinaria=maquinaria,
            aduana=aduana,
            estado=estado,
            documentos_map=documentos_map,
            pagina="expediente",
            id_activo=id_activo,
        )
