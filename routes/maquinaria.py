from flask import flash, redirect, render_template, request, session, url_for

from database.maquinarias import (
    insertar_maquinaria,
    obtener_accesorios_asignados_maquinaria,
    obtener_asignacion_activa_accesorio,
    obtener_categorias_accesorios,
    obtener_contenido_activo,
    obtener_estadisticas_maquinarias,
    obtener_historial_asignaciones_accesorio,
    obtener_mantenimiento_en_proceso,
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


def registrar_rutas_maquinaria(
    app,
    login_required,
    roles_required,
    registrar_movimiento,
    es_dispositivo_movil,
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
