from datetime import date, datetime

import pandas as pd
from flask import jsonify, render_template, request, session

from database.aduanas import estado_expediente_aduanal, obtener_aduana
from database.maquinarias import (
    obtener_maquinarias_mobile,
    obtener_maquinarias_mobile_filtrado,
    obtener_ubicaciones,
)
from models.auditoria_model import obtener_activos_recientes


def registrar_rutas_maquinaria_mobile(app, login_required):
    """Registra el listado, filtros y datos auxiliares de maquinaria móvil."""

    @app.route("/m/maquinarias/cargar")
    @login_required
    def cargar_maquinarias_mobile():
        offset = int(request.args.get("offset", 0))
        maquinarias = (
            obtener_maquinarias_mobile(limite=20, offset=offset)
            .fillna("")
            .to_dict("records")
        )

        for maquina in maquinarias:
            aduana = obtener_aduana(maquina["id_activo"])
            maquina["expediente"] = estado_expediente_aduanal(aduana)

        return jsonify(maquinarias)

    @app.route("/m/maquinarias")
    @login_required
    def maquinarias_mobile():
        return render_template("maquinaria_qr/maquinarias_mobile.html")

    @app.route("/m/maquinarias/api")
    @login_required
    def api_maquinarias_mobile():
        q = request.args.get("q", "").strip()
        estado = request.args.get("estado", "")
        ubicacion = request.args.get("ubicacion", "")
        tipo = request.args.get("tipo", "")
        offset = int(request.args.get("offset", 0))

        maquinarias = obtener_maquinarias_mobile_filtrado(
            q=q,
            estado=estado,
            ubicacion=ubicacion,
            tipo=tipo,
            limite=20,
            offset=offset,
        ).to_dict("records")

        for maquina in maquinarias:
            aduana = obtener_aduana(maquina["id_activo"])
            maquina["expediente"] = estado_expediente_aduanal(aduana)

            for key, value in list(maquina.items()):
                try:
                    if pd.isna(value):
                        maquina[key] = None
                        continue
                except TypeError:
                    pass

                if isinstance(value, (datetime, date, pd.Timestamp)):
                    maquina[key] = value.strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(maquinarias)

    @app.route("/m/maquinarias/ubicaciones")
    @login_required
    def api_ubicaciones_mobile():
        return jsonify(obtener_ubicaciones())

    @app.route("/m/recientes")
    @login_required
    def api_activos_recientes():
        return jsonify(obtener_activos_recientes(session["nombre"]))
