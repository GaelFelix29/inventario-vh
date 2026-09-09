from uuid import uuid4

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from database.documentos import (
    eliminar_documento,
    guardar_documento_bd,
    listar_documentos,
    obtener_documento,
)
from database.maquinarias import obtener_maquinaria
from supabase_config import supabase


EXTENSIONES_PERMITIDAS = {"jpg", "jpeg", "png", "webp"}
MAXIMO_ARCHIVOS = 10
TAMANIO_MAXIMO = 8 * 1024 * 1024


def _volver_evidencias(id_activo):
    return redirect(url_for("qr_evidencias", id_activo=id_activo))


def _preparar_imagenes(archivos, id_activo):
    preparados = []
    for archivo in archivos:
        nombre_original = archivo.filename
        nombre_seguro = secure_filename(nombre_original)

        if not nombre_seguro:
            raise ValueError("Una de las imágenes no tiene un nombre válido.")
        if "." not in nombre_seguro:
            raise ValueError(
                f"El archivo {nombre_original} no tiene una extensión válida."
            )

        extension = nombre_seguro.rsplit(".", 1)[1].lower()
        if extension not in EXTENSIONES_PERMITIDAS:
            raise ValueError(
                f"El archivo {nombre_original} no es una imagen JPG, PNG o WEBP."
            )
        if not archivo.content_type or not archivo.content_type.startswith("image/"):
            raise ValueError(
                f"El archivo {nombre_original} no fue reconocido como imagen."
            )

        contenido = archivo.read()
        if not contenido:
            raise ValueError(f"El archivo {nombre_original} está vacío.")
        if len(contenido) > TAMANIO_MAXIMO:
            raise ValueError(
                f"La imagen {nombre_original} supera el límite de 8 MB."
            )

        nombre_archivo = f"{id_activo}_{uuid4().hex}_{nombre_seguro}"
        preparados.append(
            {
                "nombre_original": nombre_original,
                "nombre_archivo": nombre_archivo,
                "contenido": contenido,
                "content_type": archivo.content_type,
                "ruta": f"{id_activo}/{nombre_archivo}",
            }
        )
    return preparados


def registrar_rutas_evidencias(app, login_required, registrar_movimiento):
    """Registra galería, carga múltiple y eliminación de evidencias."""

    @app.route("/qr/<id_activo>/evidencias")
    @login_required
    def qr_evidencias(id_activo):
        return render_template(
            "maquinaria_qr/evidencias.html",
            maquinaria=obtener_maquinaria(id_activo),
            imagenes=listar_documentos(id_activo, "IMAGEN"),
            id_activo=id_activo,
            pagina="evidencias",
        )

    @app.route("/qr/<id_activo>/evidencias", methods=["POST"])
    @login_required
    def subir_evidencia(id_activo):
        if session.get("rol") != "Administrador":
            flash("No tiene permisos para subir evidencias.", "danger")
            return _volver_evidencias(id_activo)

        archivos = [
            archivo
            for archivo in request.files.getlist("documentos")
            if archivo and archivo.filename
        ]
        if not archivos:
            flash("Seleccione al menos una imagen.", "warning")
            return _volver_evidencias(id_activo)
        if len(archivos) > MAXIMO_ARCHIVOS:
            flash("Puede subir un máximo de 10 imágenes por envío.", "warning")
            return _volver_evidencias(id_activo)

        try:
            imagenes = _preparar_imagenes(archivos, id_activo)
        except ValueError as error:
            flash(str(error), "warning")
            return _volver_evidencias(id_activo)

        cantidad_guardada = 0
        try:
            for imagen in imagenes:
                supabase.storage.from_("documentos").upload(
                    path=imagen["ruta"],
                    file=imagen["contenido"],
                    file_options={
                        "content-type": imagen["content_type"],
                        "upsert": False,
                    },
                )
                url_publica = supabase.storage.from_("documentos").get_public_url(
                    imagen["ruta"]
                )
                if isinstance(url_publica, dict):
                    url_guardar = (
                        url_publica.get("publicUrl")
                        or url_publica.get("public_url")
                    )
                else:
                    url_guardar = url_publica
                if not url_guardar:
                    raise ValueError(
                        "No fue posible obtener la URL de una evidencia."
                    )

                guardar_documento_bd(
                    id_activo=id_activo,
                    nombre_original=imagen["nombre_original"],
                    nombre_archivo=imagen["nombre_archivo"],
                    tipo="General",
                    tipo_archivo="IMAGEN",
                    descripcion=None,
                    url=url_guardar,
                    public_id=imagen["ruta"],
                    usuario=session["nombre"],
                )
                registrar_movimiento(
                    usuario=session["nombre"],
                    accion=f"Subió evidencia: {imagen['nombre_original']}",
                    modulo="Evidencias",
                    referencia=id_activo,
                )
                cantidad_guardada += 1

            mensaje = (
                "Evidencia guardada correctamente."
                if cantidad_guardada == 1
                else f"{cantidad_guardada} evidencias guardadas correctamente."
            )
            flash(mensaje, "success")
        except Exception:
            if cantidad_guardada:
                flash(
                    f"Se guardaron {cantidad_guardada} imágenes, pero ocurrió "
                    "un error con las restantes.",
                    "warning",
                )
            else:
                flash("No fue posible guardar las evidencias.", "danger")

        return _volver_evidencias(id_activo)

    @app.route("/evidencias/<int:id>/eliminar")
    @login_required
    def eliminar_evidencia(id):
        if session.get("rol") != "Administrador":
            flash("Sin permisos.", "danger")
            return redirect(request.referrer or url_for("dashboard"))

        try:
            documento = obtener_documento(id)
            if not documento:
                flash("La evidencia no existe.", "warning")
                return redirect(request.referrer)

            supabase.storage.from_("documentos").remove([documento["public_id"]])
            eliminar_documento(id)
            registrar_movimiento(
                usuario=session["nombre"],
                accion=f"Eliminó evidencia: {documento['nombre_original']}",
                modulo="Evidencias",
                referencia=documento["id_activo"],
            )
            flash("Evidencia eliminada correctamente.", "success")
            return _volver_evidencias(documento["id_activo"])
        except Exception as error:
            flash(f"Error al eliminar evidencia: {error}", "danger")
            return redirect(request.referrer)
