from datetime import datetime

from flask import flash, redirect, render_template, request, session, url_for

from models.auditoria_model import obtener_actividad_filtrada


MODULOS_GENERALES = [
    "Accesorios",
    "Aduanas",
    "Documentación",
    "Evidencias",
    "Login",
    "Maquinaria",
    "Movimientos",
    "Respaldos",
    "Seguridad",
    "Solicitudes",
    "Usuarios",
]

MODULOS_MANTENIMIENTO = [
    "Accesorios",
    "Maquinaria",
    "Movimientos",
    "Solicitudes",
]


def _modulos_autorizados(rol):
    if rol in {"Administrador", "Visualizador"}:
        return MODULOS_GENERALES
    if rol == "Mantenimiento":
        return MODULOS_MANTENIMIENTO
    return None


def _validar_fecha(valor, mensaje):
    if not valor:
        return ""
    try:
        datetime.strptime(valor, "%Y-%m-%d")
        return valor
    except ValueError:
        flash(mensaje, "warning")
        return ""


def _validar_hora(valor, mensaje):
    if not valor:
        return ""
    try:
        datetime.strptime(valor, "%H:%M")
        return valor
    except ValueError:
        flash(mensaje, "warning")
        return ""


def mostrar_actividad_sistema(plantilla):
    rol = session.get("rol")
    usuario_actual = session.get("nombre")
    modulos_disponibles = _modulos_autorizados(rol)

    if modulos_disponibles is None:
        flash("No tienes permiso para consultar la actividad.", "danger")
        return redirect(url_for("inicio"))

    fecha_desde = _validar_fecha(
        (request.args.get("fecha_desde") or "").strip(),
        "La fecha inicial no es válida.",
    )
    fecha_hasta = _validar_fecha(
        (request.args.get("fecha_hasta") or "").strip(),
        "La fecha final no es válida.",
    )
    hora_desde = _validar_hora(
        (request.args.get("hora_desde") or "").strip(),
        "La hora inicial no es válida.",
    )
    hora_hasta = _validar_hora(
        (request.args.get("hora_hasta") or "").strip(),
        "La hora final no es válida.",
    )
    modulo = (request.args.get("modulo") or "").strip()

    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        flash(
            "La fecha inicial no puede ser posterior a la fecha final.",
            "warning",
        )
        fecha_desde = ""
        fecha_hasta = ""

    if hora_desde and hora_hasta and hora_desde > hora_hasta:
        flash(
            "La hora inicial no puede ser posterior a la hora final.",
            "warning",
        )
        hora_desde = ""
        hora_hasta = ""

    if modulo not in modulos_disponibles:
        modulo = ""

    actividad = obtener_actividad_filtrada(
        rol=rol,
        usuario_actual=usuario_actual,
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None,
        hora_desde=hora_desde or None,
        hora_hasta=hora_hasta or None,
        modulo=modulo or None,
        limite=100,
    )

    filtros = {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "hora_desde": hora_desde,
        "hora_hasta": hora_hasta,
        "modulo": modulo,
    }

    return render_template(
        plantilla,
        actividad=actividad,
        filtros=filtros,
        modulos=modulos_disponibles,
        pagina="actividad",
    )


def registrar_rutas_actividad(app, login_required):
    """Registra Actividad conservando sus URLs y endpoints históricos."""

    @app.route("/actividad")
    @login_required
    def actividad_sistema():
        return mostrar_actividad_sistema("actividad_escritorio.html")

    @app.route("/m/actividad")
    @login_required
    def actividad_sistema_mobile():
        return mostrar_actividad_sistema("maquinaria_qr/actividad.html")
