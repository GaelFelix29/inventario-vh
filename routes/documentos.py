import traceback
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from database.documentos import (
    eliminar_documento,
    guardar_documento_bd,
    listar_documentos,
    obtener_documento,
)
from supabase_config import supabase


def registrar_rutas_documentos(app, login_required, registrar_movimiento):
    """Registra carga, eliminación y consulta móvil de documentos."""

    @app.route("/maquinarias/<id_activo>/documentos", methods=["POST"])
    @login_required
    def subir_documento(id_activo):
        if session.get("rol") != "Administrador":
            flash("No tiene permisos para subir documentos.", "danger")
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )

        archivo = request.files.get("documento")
        tipo_documento = request.form.get("tipo_documento")
        if not archivo or archivo.filename == "":
            flash("Seleccione un archivo.", "warning")
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )

        nombre_original = archivo.filename
        nombre_seguro = secure_filename(nombre_original)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"{id_activo}_{timestamp}_{nombre_seguro}"
        ruta = f"{id_activo}/{nombre_archivo}"

        try:
            supabase.storage.from_("documentos").upload(
                path=ruta,
                file=archivo.read(),
                file_options={
                    "content-type": archivo.content_type,
                    "upsert": False,
                },
            )
            url_pdf = supabase.storage.from_("documentos").get_public_url(ruta)
            if isinstance(url_pdf, dict):
                url_guardar = (
                    url_pdf.get("publicUrl") or url_pdf.get("public_url")
                )
            else:
                url_guardar = url_pdf

            guardar_documento_bd(
                id_activo=id_activo,
                nombre_original=nombre_original,
                nombre_archivo=nombre_archivo,
                tipo=tipo_documento,
                tipo_archivo="DOCUMENTO",
                descripcion=request.form.get("descripcion"),
                url=url_guardar,
                public_id=ruta,
                usuario=session["nombre"],
            )
            registrar_movimiento(
                usuario=session["nombre"],
                accion=f"Subió documento: {nombre_original}",
                modulo="Documentación",
                referencia=id_activo,
            )
            flash("Documento subido correctamente.", "success")
        except Exception as error:
            traceback.print_exc()
            flash(
                f"Ocurrió un error al subir el documento: {error}",
                "danger",
            )

        return redirect(url_for("expediente_maquinaria", id_activo=id_activo))

    @app.route("/documentos/<int:id_documento>/eliminar", methods=["POST"])
    @login_required
    def borrar_documento(id_documento):
        if session.get("rol") != "Administrador":
            flash("No tiene permisos para eliminar documentos.", "danger")
            return redirect(request.referrer or url_for("lista_maquinarias"))

        documento = obtener_documento(id_documento)
        if not documento:
            flash("Documento no encontrado.", "danger")
            return redirect(request.referrer or url_for("lista_maquinarias"))

        try:
            if documento["public_id"]:
                supabase.storage.from_("documentos").remove(
                    [documento["public_id"]]
                )
        except Exception:
            traceback.print_exc()

        eliminar_documento(id_documento)
        registrar_movimiento(
            usuario=session["nombre"],
            accion="Eliminó documento",
            modulo="Documentación",
            referencia=documento["id_activo"],
        )
        flash("Documento eliminado correctamente.", "success")
        return redirect(
            url_for(
                "expediente_maquinaria",
                id_activo=documento["id_activo"],
            )
        )

    @app.route("/qr/<id_activo>/documento/<tipo>")
    @login_required
    def qr_documento(id_activo, tipo):
        documento = next(
            (
                item
                for item in listar_documentos(id_activo)
                if item["tipo"].lower() == tipo.lower()
            ),
            None,
        )
        if not documento:
            abort(404)

        return render_template(
            "maquinaria_qr/documento.html",
            documento=documento,
            id_activo=id_activo,
        )
