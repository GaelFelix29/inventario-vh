from pathlib import Path
from uuid import uuid4
from datetime import datetime

from flask import abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from services.reportes_mantenimiento import crear_pdf_formato_mantenimiento
from supabase_config import supabase_finanzas

from database.mantenimiento import (
    crear_plan_siguiente,
    guardar_semana_manual,
    obtener_anios_planes,
    obtener_plan_naranjo,
    resumen_plan,
    vaciar_programacion,
    iniciar_ejecucion,
    obtener_agenda_activo,
    obtener_ejecucion,
    guardar_formato_eco1,
    obtener_archivo_formato,
    obtener_formato_activo,
    asignar_formato_activo,
    actualizar_datos_historicos_mantenimiento,
    usuario_puede_editar_plan,
    listar_asignacion_formatos,
    guardar_documento_mantenimiento,
    obtener_documento_mantenimiento,
    obtener_registro_mantenimiento,
)


FORMATO_ECO1 = [
    ("Encapsuladora automática #1", [
        ("enc_01", "Limpieza general de partes mecánicas"),
        ("enc_02", "Revisión y engrasado de rodamientos del plato giratorio y mecanismo de cápsulas"),
        ("enc_03", "Revisión y engrasado de levas del sistema mecánico general"),
        ("enc_04", "Revisión y engrasado de bielas del sistema mecánico general"),
        ("enc_05", "Revisión y engrasado de cojinetes del sistema mecánico general"),
        ("enc_06", "Revisión y engrasado de cadenas del sistema mecánico general"),
        ("enc_07", "Revisión o cambio de aceite en motor reductor"),
        ("enc_08", "Revisión del panel de control, botones, pantalla táctil y paro de emergencia"),
        ("enc_09", "Limpieza de panel eléctrico"),
        ("enc_10", "Revisión de conexión eléctrica: cable, clavija y contacto"),
        ("enc_11", "Revisión de conexiones neumáticas"),
        ("enc_12", "Revisión de tornillería faltante y ajuste general"),
        ("enc_13", "Revisión de tornillo sin fin de la tolva de polvo"),
        ("enc_14", "Verificar la posición correcta de la base de la tolva de polvo"),
    ]),
    ("Aspiradora de polvo", [
        ("asp_01", "Revisión y limpieza de filtros: tubo de escape y filtro de tela"),
        ("asp_02", "Revisión de conexiones eléctricas: cable y conectores"),
        ("asp_03", "Revisión general de funcionamiento"),
    ]),
    ("Bomba de vacío", [
        ("bom_01", "Limpieza de filtros: prefiltro principal y prefiltro secundario"),
        ("bom_02", "Revisión de conexiones eléctricas"),
        ("bom_03", "Revisión general de funcionamiento"),
        ("bom_04", "Revisión de conexiones neumáticas"),
        ("bom_05", "Verificar presión dentro de parámetros (80–60 kPa)"),
    ]),
]

FORMATO_CC8 = [
    ("Contadora de cápsulas #8", [
        ("cc8_01", "Revisión de accesorios completos: tuerca, guasas y discos contadores"),
        ("cc8_02", "Correcto funcionamiento de gatillo accionador"),
        ("cc8_03", "Correcto funcionamiento de botón encendido y apagado"),
        ("cc8_04", "Correcto funcionamiento de perilla de velocidad de giro"),
        ("cc8_05", "Correcto funcionamiento del sistema de vibración"),
        ("cc8_06", "Correcto funcionamiento del sensor de giro interior"),
        ("cc8_07", "Limpieza general interior y exterior"),
        ("cc8_08", "Revisión del cableado eléctrico interior en buen estado"),
        ("cc8_09", "Revisión del cable de alimentación"),
    ]),
]

MATERIALES_ECO1 = [
    "Herramienta kosherizada/Halal", "Herramienta convencional",
    "Grasa grado alimenticio Repsol", "Grasa grado alimenticio Super Lube",
    "Grasa grado alimenticio FML-2",
]

FORMATOS_DIGITALES = {
    "ECO-1": (FORMATO_ECO1, MATERIALES_ECO1),
    "CC-8": (FORMATO_CC8, MATERIALES_ECO1),
}


def registrar_rutas_mantenimiento(app, login_required):
    @app.get("/mantenimiento/registros/<int:mantenimiento_id>")
    @login_required
    def detalle_registro_mantenimiento(mantenimiento_id):
        registro, documentos = obtener_registro_mantenimiento(mantenimiento_id)
        if not registro:
            abort(404)
        return render_template(
            "mantenimiento/registro.html", registro=registro,
            documentos=documentos,
            puede_adjuntar=session.get("rol") in {"Administrador", "Mantenimiento"},
            puede_editar_historico=(session.get("rol") == "Administrador" and
                                    not registro.get("ejecucion_id")),
            puede_exportar=bool(registro.get("ejecucion_id") and
                                registro.get("estado_ejecucion") == "COMPLETO" and
                                registro.get("formato") in FORMATOS_DIGITALES),
        )

    @app.post("/mantenimiento/registros/<int:mantenimiento_id>/historico")
    @login_required
    def editar_registro_historico_mantenimiento(mantenimiento_id):
        if session.get("rol") != "Administrador":
            flash("Sólo el administrador puede editar registros históricos.", "danger")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))
        tecnico = " ".join(request.form.get("tecnico", "").split())
        fecha_texto = request.form.get("fecha_realizada", "").strip()
        inicio_texto = request.form.get("inicio", "").strip()
        fin_texto = request.form.get("fin", "").strip()
        try:
            if not tecnico or not fecha_texto:
                raise ValueError("Indica el responsable y la fecha de realización.")
            fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
            inicio = datetime.strptime(inicio_texto, "%Y-%m-%dT%H:%M") if inicio_texto else None
            fin = datetime.strptime(fin_texto, "%Y-%m-%dT%H:%M") if fin_texto else None
            actualizar_datos_historicos_mantenimiento(
                mantenimiento_id, tecnico, fecha, inicio, fin, session["nombre"]
            )
            flash("Datos históricos actualizados correctamente.", "success")
        except ValueError as error:
            flash(str(error), "warning")
        except SQLAlchemyError:
            flash("No fue posible actualizar el registro histórico.", "danger")
        return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))

    @app.post("/mantenimiento/registros/<int:mantenimiento_id>/documentos")
    @login_required
    def adjuntar_documento_mantenimiento(mantenimiento_id):
        if session.get("rol") not in {"Administrador", "Mantenimiento"}:
            flash("Tu perfil no puede adjuntar documentos.", "danger")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))
        if supabase_finanzas is None:
            flash("Falta configurar el acceso privado de Supabase.", "danger")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))
        archivo = request.files.get("archivo")
        if not archivo or not archivo.filename:
            flash("Selecciona un documento.", "warning")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))
        nombre = secure_filename(archivo.filename)
        extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
        if not nombre or extension not in {"pdf", "png", "jpg", "jpeg"}:
            flash("Usa un archivo PDF, PNG o JPG.", "warning")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))
        contenido = archivo.read()
        if not contenido or len(contenido) > 10 * 1024 * 1024:
            flash("El archivo está vacío o supera 10 MB.", "warning")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))
        ruta = f"mantenimiento/{mantenimiento_id}/{uuid4().hex}_{nombre}"
        try:
            supabase_finanzas.storage.from_("finanzas").upload(
                path=ruta, file=contenido,
                file_options={"content-type": archivo.content_type, "upsert": False},
            )
            guardar_documento_mantenimiento(
                mantenimiento_id, archivo.filename, ruta, archivo.content_type,
                session.get("usuario_id"), session["nombre"],
            )
            flash("Documento adjuntado correctamente.", "success")
        except Exception as error:
            print("ERROR SUBIENDO DOCUMENTO DE MANTENIMIENTO:", error)
            try:
                supabase_finanzas.storage.from_("finanzas").remove([ruta])
            except Exception:
                pass
            flash("No fue posible guardar el documento.", "danger")
        return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))

    @app.get("/mantenimiento/documentos/<int:documento_id>")
    @login_required
    def abrir_documento_mantenimiento(documento_id):
        if supabase_finanzas is None:
            abort(503)
        documento = obtener_documento_mantenimiento(documento_id)
        if not documento:
            abort(404)
        resultado = supabase_finanzas.storage.from_("finanzas").create_signed_url(
            documento["ruta_storage"], 300
        )
        enlace = (resultado.get("signedURL") or resultado.get("signedUrl") or
                  resultado.get("signed_url")) if isinstance(resultado, dict) else resultado
        if not enlace:
            abort(404)
        return redirect(enlace)

    @app.get("/mantenimiento/registros/<int:mantenimiento_id>/pdf")
    @login_required
    def exportar_registro_mantenimiento_pdf(mantenimiento_id):
        registro, _ = obtener_registro_mantenimiento(mantenimiento_id)
        if not registro:
            abort(404)
        if not (registro.get("ejecucion_id") and
                registro.get("estado_ejecucion") == "COMPLETO" and
                registro.get("formato") in FORMATOS_DIGITALES):
            flash("Este mantenimiento todavía no tiene un formulario digital completo para exportar.", "warning")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))
        secciones, materiales = FORMATOS_DIGITALES[registro["formato"]]
        archivo = crear_pdf_formato_mantenimiento(
            registro, secciones, materiales,
            Path(app.root_path) / "static" / "img" / "logo.png",
        )
        return send_file(archivo, mimetype="application/pdf", as_attachment=True,
                         download_name=f"mantenimiento_{registro['codigo']}_semana_{registro['semana']}.pdf")

    @app.route("/mantenimiento/formatos", methods=["GET", "POST"])
    @login_required
    def administrar_formatos_mantenimiento():
        if request.method == "POST":
            if session.get("rol") != "Administrador":
                flash("Solo el administrador puede cambiar formatos.", "danger")
                return redirect(url_for("administrar_formatos_mantenimiento"))
            try:
                asignar_formato_activo(
                    request.form.get("id_activo", ""),
                    request.form.get("formato_id", type=int),
                    session["nombre"],
                )
                flash("La asignación del formato se actualizó correctamente.", "success")
            except (ValueError, SQLAlchemyError) as error:
                flash(str(error) if isinstance(error, ValueError) else
                      "No fue posible actualizar el formato.", "danger")
            return redirect(url_for("administrar_formatos_mantenimiento",
                                    buscar=request.form.get("buscar", "")))
        maquinas, formatos = listar_asignacion_formatos()
        buscar = " ".join(request.args.get("buscar", "").split())
        if buscar:
            termino = buscar.casefold()
            maquinas = [m for m in maquinas if termino in " ".join((
                m["id_activo"], m["codigo"], m["equipo"], m["departamento"]
            )).casefold()]
        return render_template(
            "mantenimiento/formatos.html", maquinas=maquinas, formatos=formatos,
            buscar=buscar, es_administrador=session.get("rol") == "Administrador",
        )

    @app.get("/mantenimiento/maquinaria/<id_activo>")
    @login_required
    def mantenimiento_maquinaria(id_activo):
        from datetime import date
        anio = request.args.get("anio", date.today().year, type=int)
        origen = request.args.get("origen", "web")
        if origen not in {"web", "qr"}:
            origen = "web"
        equipo, agenda = obtener_agenda_activo(id_activo, anio)
        if not equipo:
            flash("La maquinaria no existe.", "warning")
            return redirect(url_for("mantenimiento_preventivo"))
        formato_asignado = obtener_formato_activo(id_activo)
        return render_template(
            "mantenimiento/maquinaria.html", equipo=equipo, agenda=agenda,
            anio=anio, semana_actual=date.today().isocalendar().week,
            origen=origen,
            puede_iniciar=session.get("rol") in {"Administrador", "Mantenimiento"},
            formato_asignado=formato_asignado,
        )

    @app.get("/mantenimiento/formatos/<int:formato_id>/archivo")
    @login_required
    def archivo_formato_mantenimiento(formato_id):
        ruta = obtener_archivo_formato(formato_id)
        if not ruta:
            abort(404)
        return send_file(ruta, mimetype="application/pdf", as_attachment=False,
                         download_name=ruta.name)

    @app.post("/mantenimiento/maquinaria/<id_activo>/<int:mantenimiento_id>/iniciar")
    @login_required
    def iniciar_mantenimiento_programado(id_activo, mantenimiento_id):
        origen = request.form.get("origen", "web")
        if origen not in {"web", "qr"}:
            origen = "web"
        if session.get("rol") not in {"Administrador", "Mantenimiento"}:
            flash("Tu perfil no puede iniciar mantenimientos.", "danger")
            return redirect(url_for("mantenimiento_maquinaria", id_activo=id_activo, origen=origen))
        formato = obtener_formato_activo(id_activo)
        if not formato:
            flash("Esta maquinaria todavía no tiene un formato preventivo confirmado.", "warning")
            return redirect(url_for("mantenimiento_maquinaria", id_activo=id_activo, origen=origen))
        if not formato["digitalizado"]:
            flash("El formato oficial está asociado, pero su versión digital todavía está pendiente.", "warning")
            return redirect(url_for("mantenimiento_maquinaria", id_activo=id_activo, origen=origen))
        try:
            ejecucion_id = iniciar_ejecucion(
                mantenimiento_id, id_activo,
                session.get("usuario_id"), session["nombre"]
            )
            flash("Mantenimiento iniciado. El formato quedó guardado como borrador.", "success")
            return redirect(url_for("formato_mantenimiento", ejecucion_id=ejecucion_id, origen=origen))
        except (ValueError, SQLAlchemyError) as error:
            flash(str(error) if isinstance(error, ValueError) else "No fue posible iniciar el mantenimiento.", "danger")
        return redirect(url_for("mantenimiento_maquinaria", id_activo=id_activo, origen=origen))

    @app.route("/mantenimiento/formato/<int:ejecucion_id>", methods=["GET", "POST"])
    @login_required
    def formato_mantenimiento(ejecucion_id):
        origen = request.args.get("origen", request.form.get("origen", "web"))
        if origen not in {"web", "qr"}:
            origen = "web"
        ejecucion = obtener_ejecucion(ejecucion_id)
        if not ejecucion:
            flash("El formato no existe.", "warning")
            return redirect(url_for("mantenimiento_preventivo"))
        codigo_formato = ejecucion["codigo"].strip().upper()
        configuracion = FORMATOS_DIGITALES.get(codigo_formato)
        if not configuracion:
            flash("La plantilla digital de esta maquinaria aún no está configurada.", "warning")
            return redirect(url_for("mantenimiento_maquinaria", id_activo=ejecucion["id_activo"], anio=ejecucion["anio"], origen=origen))
        puede_editar = session.get("rol") in {"Administrador", "Mantenimiento"}
        if request.method == "POST":
            if not puede_editar:
                flash("Tu perfil no puede modificar este formato.", "danger")
                return redirect(url_for("formato_mantenimiento", ejecucion_id=ejecucion_id, origen=origen))
            secciones, materiales = configuracion
            claves = [clave for _, actividades in secciones for clave, _ in actividades]
            datos = {
                "fecha_realizacion": request.form.get("fecha_realizacion", ""),
                "procedimiento": request.form.get("procedimiento", ""),
                "respuestas": {clave: request.form.get(f"actividad_{clave}", "") for clave in claves},
                "materiales": request.form.getlist("materiales"),
                "observaciones": request.form.get("observaciones", ""),
                "firma_tecnico": request.form.get("firma_tecnico", ""),
                "firma_supervisor": request.form.get("firma_supervisor", ""),
                "claves": claves,
            }
            finalizar = request.form.get("accion") == "finalizar"
            try:
                guardar_formato_eco1(
                    ejecucion_id, datos, session["nombre"], finalizar,
                    codigo_formato,
                )
                flash("Formato finalizado correctamente." if finalizar else "Borrador guardado.", "success")
            except (ValueError, SQLAlchemyError) as error:
                flash(str(error) if isinstance(error, ValueError) else "No fue posible guardar el formato.", "danger")
            return redirect(url_for("formato_mantenimiento", ejecucion_id=ejecucion_id, origen=origen))
        secciones, materiales = configuracion
        return render_template(
            "mantenimiento/formato_eco1.html", ejecucion=ejecucion,
            secciones=secciones, materiales=materiales,
            codigo_formato=codigo_formato,
            origen=origen,
            puede_editar=puede_editar and ejecucion["estado"] != "COMPLETO",
        )

    @app.route("/mantenimiento")
    @login_required
    def mantenimiento_preventivo():
        from datetime import date
        anios = obtener_anios_planes()
        predeterminado = date.today().year if date.today().year in anios else (anios[0] if anios else date.today().year)
        anio = request.args.get("anio", predeterminado, type=int)
        buscar = " ".join(request.args.get("buscar", "").split())
        departamento = " ".join(request.args.get("departamento", "").split())
        pagina = max(1, request.args.get("pagina", 1, type=int))
        por_pagina = request.args.get("por_pagina", 20, type=int)
        if por_pagina not in (20, 50):
            por_pagina = 20
        try:
            plan, equipos = obtener_plan_naranjo(anio)
        except SQLAlchemyError:
            plan, equipos = None, []

        resumen = resumen_plan(equipos)
        departamentos = sorted({e["departamento"] for e in equipos})
        if buscar:
            termino = buscar.casefold()
            equipos = [e for e in equipos if termino in " ".join((
                e["codigo"], e["equipo"], e["departamento"], e["id_activo"]
            )).casefold()]
        if departamento:
            equipos = [e for e in equipos if e["departamento"] == departamento]
        total = len(equipos)
        paginas = max(1, (total + por_pagina - 1) // por_pagina)
        pagina = min(pagina, paginas)
        inicio = (pagina - 1) * por_pagina
        equipos = equipos[inicio:inicio + por_pagina]

        semanas = range(1, 53)
        puede_editar_plan = usuario_puede_editar_plan(session.get("usuario_id"))
        return render_template(
            "mantenimiento/index.html",
            plan=plan,
            equipos=equipos,
            resumen=resumen,
            anio=anio,
            semanas=semanas,
            buscar=buscar,
            departamento=departamento,
            departamentos=departamentos,
            pagina=pagina,
            paginas=paginas,
            por_pagina=por_pagina,
            total_filtrado=total,
            anios=anios,
            anio_actual=date.today().year,
            plan_siguiente_existe=(date.today().year + 1) in anios,
            puede_editar=puede_editar_plan,
            es_administrador=session.get("rol") == "Administrador",
        )

    @app.post("/mantenimiento/programacion")
    @login_required
    def guardar_programacion_mantenimiento():
        if not usuario_puede_editar_plan(session.get("usuario_id")):
            flash("No tienes permiso para modificar el plan.", "danger")
            return redirect(url_for("mantenimiento_preventivo"))
        try:
            guardar_semana_manual(
                request.form.get("plan_equipo_id", type=int),
                request.form.get("semana", type=int),
                request.form.get("opcion", ""),
                session["nombre"],
            )
            flash("La semana se actualizó correctamente.", "success")
        except (TypeError, ValueError) as error:
            flash(str(error), "warning")
        except SQLAlchemyError:
            flash("No fue posible guardar la semana.", "danger")
        regresar = request.form.get("regresar", "")
        if not regresar.startswith("/mantenimiento"):
            regresar = url_for("mantenimiento_preventivo")
        return redirect(regresar)

    @app.post("/mantenimiento/programacion/rapida")
    @login_required
    def guardar_programacion_mantenimiento_rapida():
        if not usuario_puede_editar_plan(session.get("usuario_id")):
            return jsonify({"ok": False, "error": "No tienes permiso para modificar el plan."}), 403
        datos = request.get_json(silent=True) or {}
        try:
            resultado = guardar_semana_manual(
                int(datos.get("plan_equipo_id")), int(datos.get("semana")),
                datos.get("opcion", ""), session["nombre"],
            )
            return jsonify({"ok": True, **resultado})
        except (TypeError, ValueError) as error:
            return jsonify({"ok": False, "error": str(error)}), 400
        except SQLAlchemyError:
            return jsonify({"ok": False, "error": "No fue posible guardar la semana."}), 500

    @app.post("/mantenimiento/crear-siguiente")
    @login_required
    def crear_plan_mantenimiento_siguiente():
        from datetime import date
        if not usuario_puede_editar_plan(session.get("usuario_id")):
            flash("No tienes permiso para crear planes.", "danger")
            return redirect(url_for("mantenimiento_preventivo"))
        try:
            anio_origen = request.form.get("anio", type=int)
            if anio_origen != date.today().year:
                raise ValueError(
                    f"Durante {date.today().year} solamente puede prepararse el plan {date.today().year + 1}."
                )
            nuevo_anio = crear_plan_siguiente(
                anio_origen, session["nombre"]
            )
            flash(f"Plan {nuevo_anio} creado para captura gradual.", "success")
            return redirect(url_for("mantenimiento_preventivo", anio=nuevo_anio))
        except (TypeError, ValueError) as error:
            flash(str(error), "warning")
        except SQLAlchemyError:
            flash("No fue posible crear el plan siguiente.", "danger")
        return redirect(url_for("mantenimiento_preventivo"))

    @app.post("/mantenimiento/vaciar")
    @login_required
    def vaciar_plan_mantenimiento():
        anio = request.form.get("anio", type=int)
        if (session.get("rol") != "Administrador" or
                not usuario_puede_editar_plan(session.get("usuario_id"))):
            flash("Solo el administrador puede reiniciar un plan.", "danger")
            return redirect(url_for("mantenimiento_preventivo", anio=anio))
        try:
            eliminados = vaciar_programacion(anio, session["nombre"])
            flash(f"Plan {anio} reiniciado: {eliminados} semanas eliminadas.", "success")
        except (TypeError, ValueError) as error:
            flash(str(error), "warning")
        except SQLAlchemyError:
            flash("No fue posible reiniciar el plan.", "danger")
        return redirect(url_for("mantenimiento_preventivo", anio=anio))
