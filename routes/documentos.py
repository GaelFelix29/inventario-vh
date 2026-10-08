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
from supabase_config import supabase, supabase_privado


TIPOS_ARCHIVO_PERMITIDOS = {
    "pdf": ("application/pdf", "DOCUMENTO"),
    "jpg": ("image/jpeg", "IMAGEN"),
    "jpeg": ("image/jpeg", "IMAGEN"),
    "png": ("image/png", "IMAGEN"),
}
TAMANO_MAXIMO_ARCHIVO = 10 * 1024 * 1024


def _tipo_archivo_valido(nombre, contenido):
    """Valida extensión y firma básica; devuelve MIME y clasificación."""
    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    configuracion = TIPOS_ARCHIVO_PERMITIDOS.get(extension)
    if not configuracion:
        return None

    firmas_validas = {
        "pdf": contenido.startswith(b"%PDF-"),
        "jpg": contenido.startswith(b"\xff\xd8\xff"),
        "jpeg": contenido.startswith(b"\xff\xd8\xff"),
        "png": contenido.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    return configuracion if firmas_validas[extension] else None


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
        contenido = archivo.read()
        if not contenido:
            flash("El archivo está vacío.", "warning")
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )
        if len(contenido) > TAMANO_MAXIMO_ARCHIVO:
            flash("El archivo supera el límite de 10 MB.", "warning")
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )

        tipo_archivo = _tipo_archivo_valido(nombre_original, contenido)
        if not tipo_archivo:
            flash(
                "El archivo no es válido. Seleccione un PDF, JPG, JPEG o PNG.",
                "warning",
            )
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )
        content_type, clasificacion = tipo_archivo
        nombre_seguro = secure_filename(nombre_original) or "archivo"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"{id_activo}_{timestamp}_{nombre_seguro}"
        ruta = f"{id_activo}/{nombre_archivo}"

        try:
            supabase.storage.from_("documentos").upload(
                path=ruta,
                file=contenido,
                file_options={
                    "content-type": content_type,
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
                tipo_archivo=clasificacion,
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

        if supabase_privado is None:
            flash(
                "Falta configurar el acceso privado de Supabase; el documento "
                "no fue eliminado.",
                "danger",
            )
            return redirect(
                url_for(
                    "expediente_maquinaria",
                    id_activo=documento["id_activo"],
                )
            )

        try:
            if documento["public_id"]:
                supabase_privado.storage.from_("documentos").remove(
                    [documento["public_id"]]
                )
            eliminar_documento(id_documento)
            registrar_movimiento(
                usuario=session["nombre"],
                accion=(
                    "Eliminó documento y archivo de Supabase: "
                    f"{documento['nombre_original']}"
                ),
                modulo="Documentación",
                referencia=documento["id_activo"],
            )
            flash("Documento eliminado de la aplicación y Supabase.", "success")
        except Exception:
            traceback.print_exc()
            flash(
                "No fue posible eliminar el archivo de Supabase. El registro "
                "se conservó para que puedas intentarlo nuevamente.",
                "danger",
            )
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
