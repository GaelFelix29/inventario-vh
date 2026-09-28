import math
from datetime import datetime
from uuid import uuid4

from flask import (abort, current_app, flash, redirect, render_template,
                   request, send_file, session, url_for)
from werkzeug.utils import secure_filename

from database.estados_cuenta import (
    editar_observacion_movimiento, eliminar_archivo_movimiento,
    eliminar_observacion_movimiento, guardar_archivo_movimiento,
    guardar_observacion_movimiento,
    importar_estado_cuenta, listar_archivos_movimiento, listar_estados_cuenta,
    listar_movimientos, listar_observaciones_movimiento, obtener_estado_cuenta,
    listar_movimientos_exportacion, obtener_archivo_movimiento,
    obtener_movimiento_bancario, renombrar_archivo_movimiento,
)
from services.importador_estados_cuenta import leer_estado_cuenta
from services.reportes_finanzas import crear_excel_movimientos, crear_pdf_movimientos
from database.mensajes import (
    enviar_mensaje, listar_usuarios_financieros_mensajeria,
    obtener_o_crear_conversacion, obtener_usuario_mensajeria,
)
import json
from supabase_config import supabase_finanzas


ROLES_FINANCIEROS = ("Administrador", "Compras", "Finanzas")
EXTENSIONES_FINANZAS = {"pdf", "xlsx", "xls", "csv", "jpg", "jpeg", "png", "webp"}
TAMANO_MAXIMO_FINANZAS = 10 * 1024 * 1024


def registrar_rutas_finanzas(app, login_required, roles_required, registrar_movimiento):
    def _filtros_movimientos():
        buscar = (request.args.get("buscar") or "").strip()
        tipo = request.args.get("tipo") or "todos"
        if tipo not in ("todos", "cargos", "abonos"):
            tipo = "todos"
        concepto = (request.args.get("concepto") or "TODOS").upper()
        if concepto not in ("TODOS", "PAGOSA", "PAGOS"):
            concepto = "TODOS"

        def fecha(nombre):
            valor = (request.args.get(nombre) or "").strip()
            try:
                return datetime.strptime(valor, "%Y-%m-%d").date() if valor else None
            except ValueError:
                return None

        fecha_desde, fecha_hasta = fecha("fecha_desde"), fecha("fecha_hasta")
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
        return buscar, tipo, concepto, fecha_desde, fecha_hasta

    @app.route("/finanzas/estados-cuenta")
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def estados_cuenta():
        return render_template("finanzas/estados_cuenta.html", estados=listar_estados_cuenta())

    @app.route("/finanzas/estados-cuenta/importar", methods=["POST"])
    @login_required
    @roles_required("Administrador", "Finanzas")
    def importar_estado_cuenta_route():
        archivo = request.files.get("archivo")
        if not archivo or not archivo.filename.lower().endswith(".xlsx"):
            flash("Selecciona un archivo de Excel .xlsx.", "warning")
            return redirect(url_for("estados_cuenta"))
        try:
            estado = leer_estado_cuenta(archivo.stream, archivo.filename)
            estado_id = importar_estado_cuenta(estado, session["usuario_id"])
            registrar_movimiento(session["nombre"], f"Importó el estado de cuenta {archivo.filename}", "Finanzas", str(estado_id))
            flash(f"Estado importado: {len(estado['movimientos']):,} movimientos conciliados.", "success")
            return redirect(url_for("detalle_estado_cuenta", estado_id=estado_id))
        except ValueError as error:
            flash(str(error), "warning")
        except Exception as error:
            print("ERROR IMPORTANDO ESTADO DE CUENTA:", error)
            flash("No fue posible importar el archivo. Verifica que la migración esté aplicada.", "danger")
        return redirect(url_for("estados_cuenta"))

    @app.route("/finanzas/estados-cuenta/<int:estado_id>")
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def detalle_estado_cuenta(estado_id):
        estado = obtener_estado_cuenta(estado_id)
        if not estado:
            abort(404)
        buscar, tipo, concepto, fecha_desde, fecha_hasta = _filtros_movimientos()
        concepto_db = concepto.lower() if concepto == "TODOS" else concepto
        try:
            pagina = max(1, int(request.args.get("pagina") or 1))
        except ValueError:
            pagina = 1
        try:
            por_pagina = int(request.args.get("por_pagina") or 20)
        except ValueError:
            por_pagina = 20
        if por_pagina not in (10, 20, 50, 100):
            por_pagina = 20
        movimientos, total = listar_movimientos(
            estado_id, buscar, tipo, pagina, por_pagina, concepto_db,
            fecha_desde, fecha_hasta
        )
        paginas = max(1, math.ceil(total / por_pagina))
        if pagina > paginas:
            pagina = paginas
            movimientos, total = listar_movimientos(
                estado_id, buscar, tipo, pagina, por_pagina, concepto_db,
                fecha_desde, fecha_hasta
            )
        desde = ((pagina - 1) * por_pagina + 1) if total else 0
        hasta = min(pagina * por_pagina, total)
        return render_template("finanzas/detalle_estado_cuenta.html", estado=estado,
                               movimientos=movimientos, total=total, pagina=pagina,
                               paginas=paginas, por_pagina=por_pagina,
                               desde=desde, hasta=hasta, buscar=buscar, tipo=tipo,
                               concepto=concepto, fecha_desde=fecha_desde,
                               fecha_hasta=fecha_hasta,
                               usuarios_financieros=(
                                   listar_usuarios_financieros_mensajeria(
                                       session["usuario_id"]
                                   )
                               ))

    @app.route("/finanzas/movimientos/<int:movimiento_id>/compartir", methods=["POST"])
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def compartir_movimiento_bancario(movimiento_id):
        movimiento = obtener_movimiento_bancario(movimiento_id)
        if not movimiento:
            abort(404)
        try:
            destinatario_id = int(request.form.get("destinatario_id") or 0)
        except (TypeError, ValueError):
            destinatario_id = 0
        destinatario = obtener_usuario_mensajeria(destinatario_id)
        if not destinatario or destinatario["rol"] not in ROLES_FINANCIEROS:
            flash("Selecciona un usuario con acceso a Finanzas.", "warning")
            return redirect(url_for(
                "detalle_estado_cuenta", estado_id=movimiento["estado_cuenta_id"]
            ))
        comentario = (request.form.get("comentario") or "").strip()
        if len(comentario) > 500:
            flash("El comentario no puede superar 500 caracteres.", "warning")
            return redirect(url_for(
                "detalle_estado_cuenta", estado_id=movimiento["estado_cuenta_id"]
            ))
        referencia = {
            "movimiento_id": movimiento["id"],
            "fecha": movimiento["fecha"].strftime("%d/%m/%Y"),
            "descripcion": (movimiento["descripcion"] or "")[:900],
            "tipo": "Abono" if movimiento["abono"] else "Cargo",
            "monto": float(movimiento["abono"] or movimiento["cargo"] or 0),
            "comentario": comentario,
        }
        contenido = "__MOVIMIENTO_BANCARIO__:" + json.dumps(
            referencia, ensure_ascii=False, separators=(",", ":")
        )
        conversacion_id = obtener_o_crear_conversacion(
            session["usuario_id"], destinatario_id
        )
        enviar_mensaje(conversacion_id, session["usuario_id"], contenido)
        registrar_movimiento(
            session["nombre"],
            f"Compartió movimiento bancario #{movimiento_id} con {destinatario['nombre']}",
            "Finanzas", str(movimiento_id)
        )
        flash("Movimiento compartido por mensaje.", "success")
        return redirect(url_for(
            "ver_conversacion", conversacion_id=conversacion_id
        ))

    def _datos_reporte(estado_id):
        estado = obtener_estado_cuenta(estado_id)
        if not estado:
            abort(404)
        buscar, tipo, concepto, fecha_desde, fecha_hasta = _filtros_movimientos()
        movimientos = listar_movimientos_exportacion(
            estado_id, buscar, tipo,
            concepto.lower() if concepto == "TODOS" else concepto,
            fecha_desde, fecha_hasta
        )
        filtros = {
            "buscar": buscar, "tipo": tipo, "concepto": concepto,
            "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta,
        }
        return estado, movimientos, filtros

    @app.route("/finanzas/estados-cuenta/<int:estado_id>/exportar/excel")
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def exportar_movimientos_excel(estado_id):
        estado, movimientos, filtros = _datos_reporte(estado_id)
        archivo = crear_excel_movimientos(
            estado, movimientos, filtros, session.get("nombre", "Usuario")
        )
        registrar_movimiento(
            session["nombre"],
            f"Exportó movimientos bancarios a Excel ({len(movimientos)} registros)",
            "Finanzas", str(estado_id)
        )
        return send_file(
            archivo, as_attachment=True,
            download_name=f"movimientos_{estado.periodo_inicio:%Y_%m}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.route("/finanzas/estados-cuenta/<int:estado_id>/exportar/pdf")
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def exportar_movimientos_pdf(estado_id):
        estado, movimientos, filtros = _datos_reporte(estado_id)
        archivo = crear_pdf_movimientos(
            estado, movimientos, filtros, session.get("nombre", "Usuario"),
            current_app.root_path + "/static/img/logo.png"
        )
        registrar_movimiento(
            session["nombre"],
            f"Exportó movimientos bancarios a PDF ({len(movimientos)} registros)",
            "Finanzas", str(estado_id)
        )
        return send_file(
            archivo, as_attachment=True,
            download_name=f"movimientos_{estado.periodo_inicio:%Y_%m}.pdf",
            mimetype="application/pdf",
        )

    @app.route("/finanzas/movimientos/<int:movimiento_id>")
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def detalle_movimiento_bancario(movimiento_id):
        movimiento = obtener_movimiento_bancario(movimiento_id)
        if not movimiento:
            abort(404)
        return render_template(
            "finanzas/movimiento_bancario.html",
            movimiento=movimiento,
            observaciones=listar_observaciones_movimiento(movimiento_id),
            archivos=listar_archivos_movimiento(movimiento_id),
        )

    @app.route("/finanzas/movimientos/<int:movimiento_id>/observaciones", methods=["POST"])
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def agregar_observacion_bancaria(movimiento_id):
        try:
            guardar_observacion_movimiento(
                movimiento_id, request.form.get("observacion"),
                session["usuario_id"]
            )
            registrar_movimiento(
                session["nombre"], "Agregó una observación bancaria",
                "Finanzas", str(movimiento_id)
            )
            flash("Observación guardada correctamente.", "success")
        except ValueError as error:
            flash(str(error), "warning")
        return redirect(url_for(
            "detalle_movimiento_bancario", movimiento_id=movimiento_id
        ))

    @app.route("/finanzas/observaciones/<int:observacion_id>/editar", methods=["POST"])
    @login_required
    @roles_required("Administrador")
    def editar_observacion_bancaria(observacion_id):
        movimiento_id = request.form.get("movimiento_id", type=int)
        try:
            movimiento_id = editar_observacion_movimiento(
                observacion_id, request.form.get("observacion")
            )
            registrar_movimiento(
                session["nombre"], "Editó una observación bancaria",
                "Finanzas", str(movimiento_id)
            )
            flash("Observación actualizada correctamente.", "success")
        except ValueError as error:
            flash(str(error), "warning")
        return redirect(url_for(
            "detalle_movimiento_bancario", movimiento_id=movimiento_id
        ))

    @app.route("/finanzas/observaciones/<int:observacion_id>/eliminar", methods=["POST"])
    @login_required
    @roles_required("Administrador")
    def eliminar_observacion_bancaria(observacion_id):
        movimiento_id = request.form.get("movimiento_id", type=int)
        try:
            movimiento_id = eliminar_observacion_movimiento(observacion_id)
            registrar_movimiento(
                session["nombre"], "Eliminó una observación bancaria",
                "Finanzas", str(movimiento_id)
            )
            flash("Observación eliminada correctamente.", "success")
        except ValueError as error:
            flash(str(error), "warning")
        return redirect(url_for(
            "detalle_movimiento_bancario", movimiento_id=movimiento_id
        ))

    @app.route("/finanzas/movimientos/<int:movimiento_id>/archivos", methods=["POST"])
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def agregar_archivo_bancario(movimiento_id):
        if supabase_finanzas is None:
            flash("Falta configurar el acceso privado de Supabase.", "danger")
            return redirect(url_for("detalle_movimiento_bancario", movimiento_id=movimiento_id))
        movimiento = obtener_movimiento_bancario(movimiento_id)
        if not movimiento:
            abort(404)
        archivo = request.files.get("archivo")
        if not archivo or not archivo.filename:
            flash("Selecciona un archivo.", "warning")
            return redirect(url_for("detalle_movimiento_bancario", movimiento_id=movimiento_id))
        nombre_seguro = secure_filename(archivo.filename)
        extension = nombre_seguro.rsplit(".", 1)[-1].lower() if "." in nombre_seguro else ""
        if not nombre_seguro or extension not in EXTENSIONES_FINANZAS:
            flash("Formato no permitido. Usa PDF, Excel, CSV o imagen.", "warning")
            return redirect(url_for("detalle_movimiento_bancario", movimiento_id=movimiento_id))
        contenido = archivo.read()
        if not contenido or len(contenido) > TAMANO_MAXIMO_FINANZAS:
            flash("El archivo está vacío o supera 10 MB.", "warning")
            return redirect(url_for("detalle_movimiento_bancario", movimiento_id=movimiento_id))
        ruta = f"finanzas/{movimiento['estado_cuenta_id']}/{movimiento_id}/{uuid4().hex}_{nombre_seguro}"
        try:
            supabase_finanzas.storage.from_("finanzas").upload(
                path=ruta, file=contenido,
                file_options={"content-type": archivo.content_type, "upsert": False},
            )
            guardar_archivo_movimiento(
                movimiento_id, archivo.filename, ruta, None,
                archivo.content_type, len(contenido), session["usuario_id"]
            )
            registrar_movimiento(
                session["nombre"], f"Adjuntó archivo bancario: {archivo.filename}",
                "Finanzas", str(movimiento_id)
            )
            flash("Archivo adjuntado correctamente.", "success")
        except Exception as error:
            print("ERROR SUBIENDO ARCHIVO FINANCIERO:", error)
            try:
                supabase_finanzas.storage.from_("finanzas").remove([ruta])
            except Exception:
                pass
            flash("No fue posible guardar el archivo.", "danger")
        return redirect(url_for(
            "detalle_movimiento_bancario", movimiento_id=movimiento_id
        ))

    @app.route("/finanzas/archivos/<int:archivo_id>/editar", methods=["POST"])
    @login_required
    @roles_required("Administrador")
    def editar_archivo_bancario(archivo_id):
        movimiento_id = request.form.get("movimiento_id", type=int)
        try:
            movimiento_id = renombrar_archivo_movimiento(
                archivo_id, request.form.get("nombre")
            )
            registrar_movimiento(
                session["nombre"], "Renombró un archivo bancario",
                "Finanzas", str(movimiento_id)
            )
            flash("Nombre del archivo actualizado.", "success")
        except ValueError as error:
            flash(str(error), "warning")
        return redirect(url_for(
            "detalle_movimiento_bancario", movimiento_id=movimiento_id
        ))

    @app.route("/finanzas/archivos/<int:archivo_id>/eliminar", methods=["POST"])
    @login_required
    @roles_required("Administrador")
    def eliminar_archivo_bancario_route(archivo_id):
        archivo = obtener_archivo_movimiento(archivo_id)
        movimiento_id = (
            archivo["movimiento_id"] if archivo
            else request.form.get("movimiento_id", type=int)
        )
        if not archivo:
            flash("El archivo no existe.", "warning")
        elif supabase_finanzas is None:
            flash("Falta configurar el acceso privado de Supabase.", "danger")
        else:
            try:
                supabase_finanzas.storage.from_("finanzas").remove(
                    [archivo["ruta_storage"]]
                )
                eliminar_archivo_movimiento(archivo_id)
                registrar_movimiento(
                    session["nombre"],
                    f"Eliminó archivo bancario: {archivo['nombre_original']}",
                    "Finanzas", str(movimiento_id)
                )
                flash("Archivo eliminado correctamente.", "success")
            except Exception as error:
                print("ERROR ELIMINANDO ARCHIVO FINANCIERO:", error)
                flash("No fue posible eliminar el archivo.", "danger")
        return redirect(url_for(
            "detalle_movimiento_bancario", movimiento_id=movimiento_id
        ))

    @app.route("/finanzas/archivos/<int:archivo_id>")
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def abrir_archivo_bancario(archivo_id):
        if supabase_finanzas is None:
            abort(503)
        archivo = obtener_archivo_movimiento(archivo_id)
        if not archivo:
            abort(404)
        resultado = supabase_finanzas.storage.from_("finanzas").create_signed_url(
            archivo["ruta_storage"], 300
        )
        if isinstance(resultado, dict):
            enlace = (
                resultado.get("signedURL") or resultado.get("signedUrl")
                or resultado.get("signed_url")
            )
        else:
            enlace = resultado
        if not enlace:
            abort(404)
        return redirect(enlace)
