from datetime import datetime

from flask import abort, flash, redirect, render_template, url_for

from database.maquinarias import (
    obtener_mantenimiento_en_proceso,
    obtener_maquinaria,
)
from database.solicitudes_baja import (
    existe_solicitud_pendiente,
    obtener_traslado_en_proceso,
)
from models.auditoria_model import obtener_historial_activo


def registrar_rutas_movimientos_mobile(
    app,
    login_required,
    roles_required,
):
    """Registra movimientos e historial de un activo en móvil."""

    @app.route("/m/maquinarias/<id_activo>/movimiento/<tipo>")
    @login_required
    @roles_required("Administrador", "Mantenimiento")
    def formulario_movimiento_mobile(id_activo, tipo):
        maquina = obtener_maquinaria(id_activo)
        if not maquina:
            flash("Activo no encontrado.", "danger")
            return redirect(url_for("dashboard_mobil"))

        titulos = {
            "TRASLADO": "Solicitud de Traslado",
            "MANTENIMIENTO": "Solicitud de Mantenimiento",
            "BAJA": "Solicitud de Baja",
            "REINCORPORACION": "Solicitud de Reactivación",
        }
        if tipo not in titulos:
            abort(404)

        return render_template(
            "maquinaria_qr/formulario_movimiento.html",
            maquina=maquina,
            tipo=tipo,
            titulo=titulos[tipo],
            id_activo=id_activo,
            pagina="movimientos",
        )

    @app.route("/m/maquinarias/<id_activo>/movimientos")
    @login_required
    @roles_required("Administrador", "Mantenimiento")
    def movimientos_mobile(id_activo):
        maquina = obtener_maquinaria(id_activo)
        if not maquina:
            flash("Activo no encontrado.", "danger")
            return redirect(url_for("dashboard_mobil"))

        return render_template(
            "maquinaria_qr/movimientos_mobile.html",
            maquina=maquina,
            traslado_en_proceso=obtener_traslado_en_proceso(id_activo),
            mantenimiento_en_proceso=(
                obtener_mantenimiento_en_proceso(id_activo)
            ),
            solicitud_pendiente=existe_solicitud_pendiente(id_activo),
            id_activo=id_activo,
            pagina="movimientos",
        )

    @app.route("/m/maquinarias/<id_activo>/actividad")
    @login_required
    def actividad_mobile(id_activo):
        maquinaria = obtener_maquinaria(id_activo)
        if not maquinaria:
            flash("Activo no encontrado.", "danger")
            return redirect(url_for("dashboard_mobil"))

        historial_procesado = []
        for evento in obtener_historial_activo(id_activo):
            nuevo = dict(evento)
            accion = nuevo["accion"].upper()

            if "REINCORPORACION" in accion:
                nuevo["icono"] = "bi-arrow-clockwise"
                nuevo["color"] = "success"
            elif "BAJA" in accion:
                nuevo["icono"] = "bi-trash-fill"
                nuevo["color"] = "danger"
            elif "DOCUMENTO" in accion:
                nuevo["icono"] = "bi-file-earmark-text-fill"
                nuevo["color"] = "primary"
            elif "TRASLADO" in accion:
                nuevo["icono"] = "bi-truck"
                nuevo["color"] = "info"
            elif "MANTENIMIENTO" in accion:
                nuevo["icono"] = "bi-tools"
                nuevo["color"] = "warning"
            elif "ADUANA" in accion or "PEDIMENTO" in accion:
                nuevo["icono"] = "bi-folder2-open"
                nuevo["color"] = "secondary"
            else:
                nuevo["icono"] = "bi-clock-history"
                nuevo["color"] = "dark"

            fecha = nuevo["fecha"]
            if isinstance(fecha, datetime):
                nuevo["fecha_formato"] = fecha.strftime("%d %b · %H:%M")
            else:
                nuevo["fecha_formato"] = str(fecha)

            historial_procesado.append(nuevo)

        return render_template(
            "maquinaria_qr/actividad_mobile.html",
            maquinaria=maquinaria,
            historial=historial_procesado,
            pagina="actividad",
            id_activo=id_activo,
        )
