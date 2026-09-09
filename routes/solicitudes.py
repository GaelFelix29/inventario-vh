from flask import flash, redirect, request, session, url_for

from database.maquinarias import obtener_maquinaria
from database.solicitudes_baja import (
    existe_solicitud_pendiente,
    guardar_solicitud,
)


ACCIONES_SOLICITUD = {
    "BAJA": "Solicitó baja del activo",
    "TRASLADO": "Solicitó traslado del activo",
    "MANTENIMIENTO": "Solicitó mantenimiento del activo",
    "REINCORPORACION": "Solicitó reactivación del activo",
}


def registrar_rutas_solicitudes(
    app,
    login_required,
    registrar_movimiento,
):
    """Registra inicialmente la creación de solicitudes de activos."""

    @app.route("/maquinarias/<id_activo>/solicitud-baja", methods=["POST"])
    @login_required
    def solicitud_baja(id_activo):
        if session.get("rol") not in ["Administrador", "Mantenimiento"]:
            flash("No tiene permisos para realizar esta acción.", "danger")
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )

        maquina = obtener_maquinaria(id_activo)
        if not maquina:
            flash("El activo no existe.", "danger")
            return redirect(url_for("lista_maquinarias"))

        origen = request.form.get("origen", "desktop")

        def regresar():
            if origen in ("mobile", "qr"):
                return redirect(url_for("maquinaria_qr", id_activo=id_activo))
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )

        tipo = request.form["tipo"]
        if maquina["estado"] == "BAJA" and tipo != "REINCORPORACION":
            flash(
                "Este activo ya fue dado de baja y solo puede solicitar "
                "una reactivación.",
                "warning",
            )
            return regresar()

        if existe_solicitud_pendiente(id_activo):
            flash(
                "Este activo ya cuenta con una solicitud pendiente.",
                "warning",
            )
            return regresar()

        datos = {
            "id_activo": id_activo,
            "solicitante": session["nombre"],
            "tipo": tipo,
            "motivo": request.form["motivo"],
            "observaciones": request.form["observaciones"],
            "prioridad": request.form["prioridad"],
            "ubicacion_destino": (
                request.form.get("ubicacion_destino") or None
            ),
            "proveedor_mantenimiento": (
                request.form.get("proveedor_mantenimiento") or None
            ),
            "fecha_estimada_fin": (
                request.form.get("fecha_estimada_fin") or None
            ),
        }
        guardar_solicitud(datos)
        registrar_movimiento(
            usuario=session["nombre"],
            accion=ACCIONES_SOLICITUD[tipo],
            modulo="Maquinaria",
            referencia=id_activo,
        )
        flash(
            "La solicitud fue enviada correctamente y está pendiente "
            "de aprobación.",
            "success",
        )
        return regresar()
