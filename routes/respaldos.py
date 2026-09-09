import os
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from respaldos import BACKUPS, crear_respaldo


def _es_nombre_respaldo_valido(nombre):
    return (
        bool(nombre)
        and os.path.basename(nombre) == nombre
        and nombre.lower().endswith(".sql")
    )


def _ruta_respaldo(nombre):
    if not _es_nombre_respaldo_valido(nombre):
        return None
    ruta = os.path.abspath(os.path.join(BACKUPS, nombre))
    if os.path.dirname(ruta) != os.path.abspath(BACKUPS):
        return None
    return ruta


def _requiere_administrador():
    if session.get("rol") == "Administrador":
        return None
    flash("No tiene permisos para gestionar respaldos.", "danger")
    return redirect(request.referrer or url_for("lista_maquinarias"))


def registrar_rutas_respaldos(app, login_required, registrar_movimiento):
    """Registra listado, creación, descarga y eliminación de respaldos."""

    @app.route("/respaldos")
    @login_required
    def vista_respaldos():
        rechazo = _requiere_administrador()
        if rechazo:
            return rechazo

        respaldos = []
        if os.path.exists(BACKUPS):
            for archivo in os.listdir(BACKUPS):
                ruta = _ruta_respaldo(archivo)
                if not ruta or not os.path.isfile(ruta):
                    continue
                fecha_modificacion = os.path.getmtime(ruta)
                respaldos.append(
                    {
                        "archivo": archivo,
                        "fecha": datetime.fromtimestamp(fecha_modificacion).strftime(
                            "%d/%m/%Y %H:%M"
                        ),
                        "tamano": round(os.path.getsize(ruta) / 1024, 2),
                        "fecha_modificacion": fecha_modificacion,
                    }
                )

        respaldos.sort(
            key=lambda respaldo: respaldo["fecha_modificacion"],
            reverse=True,
        )
        for respaldo in respaldos:
            respaldo.pop("fecha_modificacion", None)

        return render_template(
            "respaldos.html",
            respaldos=respaldos,
            total_respaldos=len(respaldos),
            espacio_total=round(sum(r["tamano"] for r in respaldos), 2),
            ultimo=respaldos[0] if respaldos else None,
        )

    @app.route("/respaldos/crear", methods=["POST"])
    @login_required
    def crear_respaldo_ajax():
        rechazo = _requiere_administrador()
        if rechazo:
            return rechazo
        try:
            archivo = crear_respaldo()
            registrar_movimiento(
                usuario=session["nombre"],
                accion=f"Generó respaldo: {archivo}",
                modulo="Respaldos",
            )
            return jsonify({"ok": True, "archivo": archivo})
        except Exception as error:
            return jsonify({"ok": False, "error": str(error)}), 500

    @app.route("/respaldos/descargar/<nombre>")
    @login_required
    def descargar_respaldo(nombre):
        rechazo = _requiere_administrador()
        if rechazo:
            return rechazo
        if not _ruta_respaldo(nombre):
            return jsonify({"ok": False}), 404
        return send_from_directory(BACKUPS, nombre, as_attachment=True)

    @app.route("/respaldos/eliminar/<nombre>", methods=["POST"])
    @login_required
    def eliminar_respaldo(nombre):
        rechazo = _requiere_administrador()
        if rechazo:
            return rechazo

        ruta = _ruta_respaldo(nombre)
        if not ruta or not os.path.isfile(ruta):
            return jsonify({"ok": False}), 404

        os.remove(ruta)
        registrar_movimiento(
            usuario=session["nombre"],
            accion=f"Eliminó respaldo: {nombre}",
            modulo="Respaldos",
        )
        return jsonify({"ok": True})
