from pathlib import Path
from uuid import uuid4
from datetime import date, datetime

from flask import abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from services.reportes_mantenimiento import crear_pdf_formato_mantenimiento
from services.agenda_mantenimiento import (
    ESTADOS_AGENDA,
    preparar_agenda,
)
from services.formatos_digitales import (
    claves_plantilla,
    datos_plantilla_para_vista,
    normalizar_procedimientos,
    obtener_plantilla_documento,
    obtener_plantilla_ejecucion,
    serializar_procedimientos,
)
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
    guardar_formato_digital,
    obtener_archivo_formato,
    obtener_formato_activo,
    asignar_formato_activo,
    actualizar_formato_mantenimiento,
    actualizar_datos_historicos_mantenimiento,
    usuario_puede_editar_plan,
    listar_asignacion_formatos,
    guardar_documento_mantenimiento,
    obtener_documento_mantenimiento,
    obtener_registro_mantenimiento,
)


ORIGENES_MANTENIMIENTO = {"web", "qr", "mobile"}


def _layout_mantenimiento(origen):
    if origen == "qr":
        return "maquinaria_qr/base_qr.html"
    if origen == "mobile":
        return "maquinaria_qr/base_mobile.html"
    return "base.html"


def _resumir_equipo_mobile(equipo, semana_actual):
    """Prepara una tarjeta de consulta sin exponer la cuadrícula del plan."""
    resultado = dict(equipo)
    semanas = [
        {"semana": int(numero), **datos}
        for numero, datos in equipo.get("semanas", {}).items()
        if datos.get("estado") != "SIN_REQUERIMIENTO"
    ]
    en_proceso = [
        item for item in semanas
        if item.get("estado_ejecucion") == "BORRADOR"
    ]
    pendientes = [
        item for item in semanas
        if item.get("estado") in {"PROGRAMADO", "REPROGRAMADO"}
        and item.get("estado_ejecucion") != "COMPLETO"
    ]
    no_realizados = [item for item in semanas if item.get("estado") == "NO_REALIZADO"]
    realizados = [item for item in semanas if item.get("estado") == "REALIZADO"]

    if en_proceso:
        destacado = min(en_proceso, key=lambda item: item["semana"])
        clave, etiqueta = "EN_PROCESO", "En proceso"
        detalle = f"Semana {destacado['semana']} · formulario iniciado"
    elif pendientes:
        futuros = [item for item in pendientes if item["semana"] >= semana_actual]
        destacado = (min(futuros, key=lambda item: item["semana"])
                     if futuros else max(pendientes, key=lambda item: item["semana"]))
        clave = destacado.get("estado") or "PROGRAMADO"
        etiqueta = "Reprogramado" if clave == "REPROGRAMADO" else "Programado"
        sufijo = "" if destacado["semana"] >= semana_actual else " · pendiente"
        detalle = f"Semana {destacado['semana']}{sufijo}"
    elif no_realizados:
        destacado = max(no_realizados, key=lambda item: item["semana"])
        clave, etiqueta = "NO_REALIZADO", "No realizado"
        detalle = f"Semana {destacado['semana']}"
    elif realizados:
        destacado = max(realizados, key=lambda item: item["semana"])
        clave, etiqueta = "REALIZADO", "Realizado"
        detalle = f"Último registro: semana {destacado['semana']}"
    else:
        destacado = None
        clave, etiqueta = "SIN_PROGRAMACION", "Sin programación"
        detalle = "Sin semanas activas en este plan"

    resultado.update({
        "estado_consulta": clave,
        "estado_etiqueta": etiqueta,
        "estado_detalle": detalle,
        "semana_destacada": destacado,
    })
    return resultado


def registrar_rutas_mantenimiento(app, login_required):
    @app.get("/mantenimiento/registros/<int:mantenimiento_id>")
    @login_required
    def detalle_registro_mantenimiento(mantenimiento_id):
        origen = request.args.get("origen", "web")
        if origen not in ORIGENES_MANTENIMIENTO:
            origen = "web"
        registro, documentos = obtener_registro_mantenimiento(mantenimiento_id)
        if not registro:
            abort(404)
        plantilla = obtener_plantilla_ejecucion(registro)
        return render_template(
            "mantenimiento/registro.html", registro=registro,
            documentos=documentos,
            origen=origen,
            layout_template=_layout_mantenimiento(origen),
            id_activo=registro["id_activo"], pagina="mantenimiento",
            puede_adjuntar=session.get("rol") in {"Administrador", "Mantenimiento"},
            puede_editar_historico=(session.get("rol") == "Administrador" and
                                    not registro.get("ejecucion_id")),
            puede_exportar=bool(registro.get("ejecucion_id") and
                                registro.get("estado_ejecucion") == "COMPLETO" and
                                plantilla),
        )

    @app.post("/mantenimiento/registros/<int:mantenimiento_id>/historico")
    @login_required
    def editar_registro_historico_mantenimiento(mantenimiento_id):
        origen = request.form.get("origen", "web")
        if origen not in ORIGENES_MANTENIMIENTO:
            origen = "web"
        if session.get("rol") != "Administrador":
            flash("Sólo el administrador puede editar registros históricos.", "danger")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id, origen=origen))
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
        return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id, origen=origen))

    @app.post("/mantenimiento/registros/<int:mantenimiento_id>/documentos")
    @login_required
    def adjuntar_documento_mantenimiento(mantenimiento_id):
        origen = request.form.get("origen", "web")
        if origen not in ORIGENES_MANTENIMIENTO:
            origen = "web"
        if session.get("rol") not in {"Administrador", "Mantenimiento"}:
            flash("Tu perfil no puede adjuntar documentos.", "danger")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id, origen=origen))
        if supabase_finanzas is None:
            flash("Falta configurar el acceso privado de Supabase.", "danger")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id, origen=origen))
        archivo = request.files.get("archivo")
        if not archivo or not archivo.filename:
            flash("Selecciona un documento.", "warning")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id, origen=origen))
        nombre = secure_filename(archivo.filename)
        extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
        if not nombre or extension not in {"pdf", "png", "jpg", "jpeg"}:
            flash("Usa un archivo PDF, PNG o JPG.", "warning")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id, origen=origen))
        contenido = archivo.read()
        if not contenido or len(contenido) > 10 * 1024 * 1024:
            flash("El archivo está vacío o supera 10 MB.", "warning")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id, origen=origen))
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
        return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id, origen=origen))

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
        plantilla = obtener_plantilla_ejecucion(registro)
        if not (registro.get("ejecucion_id") and
                registro.get("estado_ejecucion") == "COMPLETO" and
                plantilla):
            flash("Este mantenimiento todavía no tiene un formulario digital completo para exportar.", "warning")
            return redirect(url_for("detalle_registro_mantenimiento", mantenimiento_id=mantenimiento_id))
        secciones, materiales = datos_plantilla_para_vista(plantilla)
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

    @app.post("/mantenimiento/formatos/<int:formato_id>/editar")
    @login_required
    def editar_formato_mantenimiento(formato_id):
        buscar = " ".join(request.form.get("buscar", "").split())
        destino = url_for("administrar_formatos_mantenimiento", buscar=buscar)
        if session.get("rol") != "Administrador":
            flash("Solo el administrador puede editar formatos.", "danger")
            return redirect(destino)

        codigo = request.form.get("codigo_documento", "")
        nombre = request.form.get("nombre", "")
        version = request.form.get("version", "")
        archivo = request.files.get("archivo")
        nombre_nuevo = None
        ruta_nueva = None
        if archivo and archivo.filename:
            nombre_seguro = secure_filename(archivo.filename)
            extension = nombre_seguro.rsplit(".", 1)[-1].lower() if "." in nombre_seguro else ""
            contenido = archivo.read()
            if extension != "pdf" or not contenido.startswith(b"%PDF-"):
                flash("El documento oficial debe ser un archivo PDF válido.", "warning")
                return redirect(destino)
            if len(contenido) > 10 * 1024 * 1024:
                flash("El PDF supera el límite de 10 MB.", "warning")
                return redirect(destino)
            carpeta = Path(app.root_path) / "private" / "formatos_mantenimiento"
            carpeta.mkdir(parents=True, exist_ok=True)
            base = secure_filename(codigo) or f"formato_{formato_id}"
            nombre_nuevo = f"{base}_{uuid4().hex[:10]}.pdf"
            ruta_nueva = carpeta / nombre_nuevo
            try:
                ruta_nueva.write_bytes(contenido)
            except OSError:
                flash("No fue posible guardar el nuevo PDF.", "danger")
                return redirect(destino)

        try:
            resultado = actualizar_formato_mantenimiento(
                formato_id, codigo, nombre, version, nombre_nuevo,
                session["nombre"],
            )
            if not resultado["hubo_cambios"]:
                flash("El formato no tenía cambios por guardar.", "info")
            elif resultado["requiere_revision"]:
                flash("Formato actualizado. Su digitalización quedó pendiente de revisión.", "success")
            else:
                flash("Formato actualizado correctamente.", "success")
        except ValueError as error:
            if ruta_nueva and ruta_nueva.exists():
                ruta_nueva.unlink()
            flash(str(error), "warning")
        except (SQLAlchemyError, OSError):
            if ruta_nueva and ruta_nueva.exists():
                ruta_nueva.unlink()
            flash("No fue posible actualizar el formato.", "danger")
        return redirect(destino)

    @app.get("/mantenimiento/maquinaria/<id_activo>")
    @login_required
    def mantenimiento_maquinaria(id_activo):
        from datetime import date
        anio = request.args.get("anio", date.today().year, type=int)
        origen = request.args.get("origen", "web")
        if origen not in ORIGENES_MANTENIMIENTO:
            origen = "web"
        equipo, agenda = obtener_agenda_activo(id_activo, anio)
        if not equipo:
            flash("La maquinaria no existe.", "warning")
            return redirect(url_for("mantenimiento_preventivo"))
        agenda_preparada = preparar_agenda(
            agenda,
            semana=request.args.get("semana", type=int),
            estado=(request.args.get("estado") or "").strip().upper(),
            pagina=request.args.get("pagina_agenda", 1, type=int),
            por_pagina=request.args.get("por_pagina", 8, type=int),
        )
        formato_asignado = obtener_formato_activo(id_activo)
        return render_template(
            "mantenimiento/maquinaria.html", equipo=equipo,
            agenda=agenda_preparada["items"],
            anio=anio, semana_actual=date.today().isocalendar().week,
            origen=origen,
            layout_template=_layout_mantenimiento(origen),
            id_activo=id_activo, pagina="mantenimiento",
            puede_iniciar=session.get("rol") in {"Administrador", "Mantenimiento"},
            formato_asignado=formato_asignado,
            semana_filtro=agenda_preparada["semana"],
            estado_filtro=agenda_preparada["estado"],
            estados_agenda=ESTADOS_AGENDA,
            pagina_agenda=agenda_preparada["pagina"],
            paginas_agenda=agenda_preparada["paginas"],
            por_pagina=agenda_preparada["por_pagina"],
            total_agenda=agenda_preparada["total"],
            total_agenda_sin_filtro=agenda_preparada["total_sin_filtro"],
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
        if origen not in ORIGENES_MANTENIMIENTO:
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
        plantilla = obtener_plantilla_documento(
            formato["codigo_documento"], incluir_bloqueados=True
        )
        if not plantilla:
            flash("La plantilla digital de este documento todavía no está configurada.", "warning")
            return redirect(url_for("mantenimiento_maquinaria", id_activo=id_activo, origen=origen))
        if not plantilla.get("habilitado"):
            flash(plantilla.get("motivo_bloqueo") or
                  "La plantilla digital requiere revisión antes de utilizarse.", "warning")
            return redirect(url_for("mantenimiento_maquinaria", id_activo=id_activo, origen=origen))
        try:
            ejecucion_id = iniciar_ejecucion(
                mantenimiento_id, id_activo,
                session.get("usuario_id"), session["nombre"],
                formato, plantilla,
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
        if origen not in ORIGENES_MANTENIMIENTO:
            origen = "web"
        ejecucion = obtener_ejecucion(ejecucion_id)
        if not ejecucion:
            flash("El formato no existe.", "warning")
            return redirect(url_for("mantenimiento_preventivo"))
        codigo_formato = ejecucion["codigo"].strip().upper()
        plantilla = obtener_plantilla_ejecucion(ejecucion)
        if not plantilla:
            flash("La plantilla digital de esta maquinaria aún no está configurada.", "warning")
            return redirect(url_for("mantenimiento_maquinaria", id_activo=ejecucion["id_activo"], anio=ejecucion["anio"], origen=origen))
        puede_editar = session.get("rol") in {"Administrador", "Mantenimiento"}
        if request.method == "POST":
            if not puede_editar:
                flash("Tu perfil no puede modificar este formato.", "danger")
                return redirect(url_for("formato_mantenimiento", ejecucion_id=ejecucion_id, origen=origen))
            claves = claves_plantilla(plantilla)
            procedimientos = normalizar_procedimientos(
                request.form.getlist("procedimiento"),
                plantilla.get("procedimientos", []),
            )
            datos = {
                "fecha_realizacion": request.form.get("fecha_realizacion", ""),
                "procedimiento": serializar_procedimientos(
                    procedimientos, plantilla.get("procedimientos", [])
                ),
                "respuestas": {clave: request.form.get(f"actividad_{clave}", "") for clave in claves},
                "materiales": request.form.getlist("materiales"),
                "observaciones": request.form.get("observaciones", ""),
                "firma_tecnico": request.form.get("firma_tecnico", ""),
                "firma_supervisor": request.form.get("firma_supervisor", ""),
                "claves": claves,
            }
            finalizar = request.form.get("accion") == "finalizar"
            try:
                guardar_formato_digital(
                    ejecucion_id, datos, session["nombre"], finalizar,
                    codigo_formato,
                )
                flash("Formato finalizado correctamente." if finalizar else "Borrador guardado.", "success")
            except ValueError as error:
                flash(str(error), "warning")
            except SQLAlchemyError:
                app.logger.exception(
                    "Error guardando el formato digital %s", ejecucion_id
                )
                flash(
                    "No fue posible guardar el formato. Revisa la conexión e inténtalo nuevamente.",
                    "danger",
                )
            return redirect(url_for("formato_mantenimiento", ejecucion_id=ejecucion_id, origen=origen))
        secciones, materiales = datos_plantilla_para_vista(plantilla)
        procedimientos_seleccionados = normalizar_procedimientos(
            ejecucion.get("procedimiento"), plantilla.get("procedimientos", [])
        )
        return render_template(
            "mantenimiento/formato_digital.html", ejecucion=ejecucion,
            secciones=secciones, materiales=materiales,
            codigo_formato=codigo_formato,
            origen=origen,
            plantilla=plantilla,
            procedimientos_seleccionados=procedimientos_seleccionados,
            layout_template=_layout_mantenimiento(origen),
            id_activo=ejecucion["id_activo"], pagina="mantenimiento",
            puede_editar=puede_editar and ejecucion["estado"] != "COMPLETO",
        )

    @app.get("/m/mantenimiento")
    @login_required
    def mantenimiento_mobile():
        anios = obtener_anios_planes()
        predeterminado = (date.today().year if date.today().year in anios
                          else (anios[0] if anios else date.today().year))
        anio = request.args.get("anio", predeterminado, type=int)
        buscar = " ".join(request.args.get("buscar", "").split())
        departamento = " ".join(request.args.get("departamento", "").split())
        estado = (request.args.get("estado") or "").strip().upper()
        pagina_actual = max(1, request.args.get("pagina", 1, type=int))
        semana_actual = date.today().isocalendar().week

        try:
            plan, equipos_plan = obtener_plan_naranjo(anio)
        except SQLAlchemyError:
            plan, equipos_plan = None, []

        equipos = [
            _resumir_equipo_mobile(equipo, semana_actual)
            for equipo in equipos_plan
            if equipo.get("datos_mantenimiento_completos")
        ]
        departamentos = sorted({equipo["departamento"] for equipo in equipos})
        resumen = {
            "equipos": len(equipos),
            "pendientes": sum(
                equipo["estado_consulta"] in {"PROGRAMADO", "REPROGRAMADO"}
                for equipo in equipos
            ),
            "en_proceso": sum(
                equipo["estado_consulta"] == "EN_PROCESO" for equipo in equipos
            ),
            "realizados": sum(
                equipo["estado_consulta"] == "REALIZADO" for equipo in equipos
            ),
        }

        if buscar:
            termino = buscar.casefold()
            equipos = [
                equipo for equipo in equipos
                if termino in " ".join(str(equipo.get(campo) or "") for campo in (
                    "id_activo", "codigo", "equipo", "departamento",
                    "voltaje", "codigo_documento", "formato_nombre",
                )).casefold()
            ]
        if departamento:
            equipos = [
                equipo for equipo in equipos
                if equipo["departamento"] == departamento
            ]
        estados_validos = {
            "PROGRAMADO", "REPROGRAMADO", "EN_PROCESO", "REALIZADO",
            "NO_REALIZADO", "SIN_PROGRAMACION",
        }
        if estado not in estados_validos:
            estado = ""
        if estado:
            equipos = [
                equipo for equipo in equipos
                if equipo["estado_consulta"] == estado
            ]

        por_pagina = 12
        total = len(equipos)
        paginas = max(1, (total + por_pagina - 1) // por_pagina)
        pagina_actual = min(pagina_actual, paginas)
        inicio = (pagina_actual - 1) * por_pagina
        equipos = equipos[inicio:inicio + por_pagina]

        return render_template(
            "maquinaria_qr/mantenimiento_mobile.html",
            plan=plan, equipos=equipos, resumen=resumen,
            anio=anio, anios=anios, semana_actual=semana_actual,
            buscar=buscar, departamento=departamento,
            departamentos=departamentos, estado=estado,
            pagina=pagina_actual, paginas=paginas, total=total,
            pagina_seccion="mantenimiento", pagina_actual="mantenimiento",
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
            resultado = vaciar_programacion(anio, session["nombre"])
            flash(
                f"Plan {anio} reiniciado: {resultado['eliminados']} semanas sin historial "
                f"eliminadas y {resultado['protegidos']} registros históricos conservados.",
                "success",
            )
        except (TypeError, ValueError) as error:
            flash(str(error), "warning")
        except SQLAlchemyError:
            flash("No fue posible reiniciar el plan.", "danger")
        return redirect(url_for("mantenimiento_preventivo", anio=anio))
