from flask import flash, jsonify, redirect, render_template, request, session, url_for

from database.aduanas import (
    estado_expediente_aduanal,
    guardar_aduana,
    obtener_aduana,
    obtener_aduanas,
    obtener_aduanas_mobile_filtrado,
    obtener_origenes,
)
from database.maquinarias import obtener_maquinarias_select


def _datos_formulario_aduana(id_activo):
    return {
        "id_activo": id_activo,
        "factura": "",
        "pedimento": "",
        "entrada_mtz": "",
        "id_imp": "",
        "inbond": "",
        "origen": "",
        "fecha_importacion": "",
        "kg_bruto": "",
        "total_bultos": "",
        "documentacion_completa": "",
    }


def _guardar_desde_formulario(id_activo):
    guardar_aduana(
        id_activo,
        request.form["factura"],
        request.form["pedimento"],
        request.form["entrada_mtz"],
        request.form["id_imp"],
        request.form["inbond"],
        request.form["origen"],
        request.form["fecha_importacion"],
        request.form.get("kg_bruto"),
        request.form.get("total_bultos"),
        request.form.get("documentacion_completa"),
    )


def registrar_rutas_aduanas(app, login_required, registrar_movimiento):
    """Registra las vistas y API de Aduanas conservando sus endpoints."""

    @app.route("/aduanas")
    @login_required
    def lista_aduanas():
        aduanas = obtener_aduanas()
        return render_template(
            "aduanas.html",
            aduanas=aduanas.to_dict("records"),
        )

    @app.route("/aduanas/<id_activo>/editar", methods=["GET", "POST"])
    @login_required
    def editar_aduana(id_activo):
        if session.get("rol") != "Administrador":
            flash(
                "No tiene permisos para editar expedientes aduanales.",
                "danger",
            )
            return redirect(url_for("lista_aduanas"))

        maquinarias = obtener_maquinarias_select()
        aduana = obtener_aduana(id_activo)
        editar = aduana is not None

        if request.method == "POST":
            _guardar_desde_formulario(id_activo)
            registrar_movimiento(
                usuario=session["nombre"],
                accion="Actualizó expediente aduanal",
                modulo="Aduanas",
                referencia=id_activo,
            )
            flash("Expediente guardado correctamente.", "success")
            return redirect(
                url_for("expediente_maquinaria", id_activo=id_activo)
            )

        if not editar:
            aduana = _datos_formulario_aduana(id_activo)

        return render_template(
            "nueva_aduana.html",
            maquinarias=maquinarias.to_dict("records"),
            aduana=aduana,
            editar=editar,
        )

    @app.route("/aduanas/nuevo", methods=["GET", "POST"])
    @login_required
    def nueva_aduana():
        if session.get("rol") != "Administrador":
            flash(
                "No tiene permisos para crear expedientes aduanales.",
                "danger",
            )
            return redirect(url_for("lista_aduanas"))

        id_activo = request.args.get("id")
        maquinarias = obtener_maquinarias_select()

        if request.method == "POST":
            id_activo = request.form["id_activo"]
            _guardar_desde_formulario(id_activo)
            registrar_movimiento(
                usuario=session["nombre"],
                accion="Creó expediente aduanal",
                modulo="Aduanas",
                referencia=id_activo,
            )
            flash(
                "Expediente aduanal actualizado correctamente.",
                "success",
            )
            return redirect(url_for("lista_aduanas"))

        return render_template(
            "nueva_aduana.html",
            maquinarias=maquinarias.to_dict("records"),
            aduana=_datos_formulario_aduana(id_activo),
            editar=False,
        )

    @app.route("/aduanas/datos/<id_activo>")
    @login_required
    def datos_aduana(id_activo):
        aduana = obtener_aduana(id_activo)
        if not aduana:
            return jsonify({})

        datos = dict(aduana)
        if datos.get("fecha_importacion"):
            datos["fecha_importacion"] = str(datos["fecha_importacion"])[:10]
        return jsonify(datos)

    @app.route("/m/aduanas")
    @login_required
    def aduanas_mobile():
        return render_template("maquinaria_qr/aduanas_mobile.html")

    @app.route("/m/aduanas/api")
    @login_required
    def api_aduanas_mobile():
        aduanas = (
            obtener_aduanas_mobile_filtrado(
                q=request.args.get("q", "").strip(),
                origen=request.args.get("origen", ""),
                tipo=request.args.get("tipo", ""),
                limite=20,
                offset=int(request.args.get("offset", 0)),
            )
            .fillna("")
            .to_dict("records")
        )
        for aduana in aduanas:
            aduana["expediente"] = estado_expediente_aduanal(aduana)
        return jsonify(aduanas)

    @app.route("/m/aduanas/origenes")
    @login_required
    def api_origenes_mobile():
        return jsonify(obtener_origenes())
