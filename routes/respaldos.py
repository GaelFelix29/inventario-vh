import os
import time
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash

from respaldos import BACKUPS, crear_respaldo


CLAVE_ACCESO_CONFIG = "RESPALDOS_PASSWORD_HASH"
SESION_ACCESO = "respaldos_acceso_hasta"
SESION_INTENTOS = "respaldos_intentos_fallidos"
SESION_BLOQUEO = "respaldos_bloqueado_hasta"
DURACION_ACCESO_SEGUNDOS = 10 * 60
DURACION_BLOQUEO_SEGUNDOS = 15 * 60
MAXIMO_INTENTOS = 5


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


def _acceso_respaldos_vigente():
    try:
        return float(session.get(SESION_ACCESO, 0)) > time.time()
    except (TypeError, ValueError):
        session.pop(SESION_ACCESO, None)
        return False


def _verificar_clave(clave, clave_hash):
    if not clave or not clave_hash:
        return False
    try:
        return check_password_hash(clave_hash, clave)
    except (TypeError, ValueError):
        return False


def registrar_rutas_respaldos(app, login_required, registrar_movimiento):
    """Registra listado, creación, descarga y eliminación de respaldos."""

    def requiere_acceso_respaldos(respuesta_json=False):
        rechazo = _requiere_administrador()
        if rechazo:
            return rechazo
        if _acceso_respaldos_vigente():
            return None
        if respuesta_json:
            return jsonify({
                "ok": False,
                "error": "El acceso a Respaldos está bloqueado. Vuelve a ingresar la contraseña.",
            }), 403
        return redirect(url_for("acceso_respaldos"))

    @app.route("/respaldos/acceso", methods=["GET", "POST"])
    @login_required
    def acceso_respaldos():
        rechazo = _requiere_administrador()
        if rechazo:
            return rechazo

        if request.method == "GET" and request.args.get("nuevo") == "1":
            session.pop(SESION_ACCESO, None)

        ahora = time.time()
        try:
            bloqueado_hasta = float(session.get(SESION_BLOQUEO, 0) or 0)
        except (TypeError, ValueError):
            bloqueado_hasta = 0
            session.pop(SESION_BLOQUEO, None)
        segundos_bloqueo = max(0, int(bloqueado_hasta - ahora))
        clave_hash = (os.getenv(CLAVE_ACCESO_CONFIG) or "").strip()

        if request.method == "POST":
            if not clave_hash:
                flash(
                    "La contraseña adicional de Respaldos aún no está configurada en el servidor.",
                    "danger",
                )
            elif segundos_bloqueo:
                flash(
                    "Se alcanzó el límite de intentos. Espera unos minutos antes de volver a intentar.",
                    "warning",
                )
            elif _verificar_clave(request.form.get("password", ""), clave_hash):
                session[SESION_ACCESO] = ahora + DURACION_ACCESO_SEGUNDOS
                session.pop(SESION_INTENTOS, None)
                session.pop(SESION_BLOQUEO, None)
                registrar_movimiento(
                    usuario=session["nombre"],
                    accion="Autorizó acceso protegido a respaldos",
                    modulo="Respaldos",
                )
                flash("Acceso autorizado por 10 minutos.", "success")
                return redirect(url_for("vista_respaldos"))
            else:
                intentos = int(session.get(SESION_INTENTOS, 0) or 0) + 1
                restantes = max(0, MAXIMO_INTENTOS - intentos)
                session[SESION_INTENTOS] = intentos
                registrar_movimiento(
                    usuario=session["nombre"],
                    accion="Intento fallido de acceso protegido a respaldos",
                    modulo="Respaldos",
                )
                if restantes == 0:
                    session[SESION_BLOQUEO] = ahora + DURACION_BLOQUEO_SEGUNDOS
                    session.pop(SESION_INTENTOS, None)
                    segundos_bloqueo = DURACION_BLOQUEO_SEGUNDOS
                    flash(
                        "Acceso bloqueado durante 15 minutos por varios intentos incorrectos.",
                        "danger",
                    )
                else:
                    flash(
                        f"Contraseña incorrecta. Quedan {restantes} intentos.",
                        "danger",
                    )

        return render_template(
            "acceso_respaldos.html",
            configurado=bool(clave_hash),
            segundos_bloqueo=segundos_bloqueo,
        )

    @app.route("/respaldos")
    @login_required
    def vista_respaldos():
        rechazo = requiere_acceso_respaldos()
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
        rechazo = requiere_acceso_respaldos(respuesta_json=True)
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
        rechazo = requiere_acceso_respaldos()
        if rechazo:
            return rechazo
        if not _ruta_respaldo(nombre):
            return jsonify({"ok": False}), 404
        return send_from_directory(BACKUPS, nombre, as_attachment=True)

    @app.route("/respaldos/eliminar/<nombre>", methods=["POST"])
    @login_required
    def eliminar_respaldo(nombre):
        rechazo = requiere_acceso_respaldos(respuesta_json=True)
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
