import base64
from io import BytesIO

import pandas as pd
import qrcode
from flask import render_template, request, url_for

from database.maquinarias import obtener_maquinarias


def _generar_qr_base64(url):
    codigo_qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    codigo_qr.add_data(url)
    codigo_qr.make(fit=True)

    imagen = codigo_qr.make_image(
        fill_color="black",
        back_color="white",
    )
    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def _maquinarias_seleccionadas():
    datos = request.get_json()
    codigos = datos["codigos"]
    maquinarias = obtener_maquinarias()
    return maquinarias[maquinarias["id_activo"].isin(codigos)]


def _datos_comunes(fila):
    url = url_for(
        "expediente_maquinaria",
        id_activo=fila["id_activo"],
        _external=True,
    )
    return {
        "codigo": fila["id_activo"],
        "nombre": fila["descripcion"],
        "estado": "BAJA" if pd.notna(fila["fecha_baja"]) else "ACTIVO",
        "url": url,
        "qr": _generar_qr_base64(url),
    }


def registrar_rutas_etiquetas(app, login_required):
    """Registra impresión, etiquetas y fichas conservando sus endpoints."""

    @app.route("/imprimir")
    @login_required
    def imprimir_qr():
        maquinarias = obtener_maquinarias()
        return render_template(
            "imprimir-qr.html",
            maquinas=maquinarias.to_dict("records"),
        )

    @app.route("/etiquetas", methods=["POST"])
    @login_required
    def etiquetas():
        etiquetas_generadas = [
            _datos_comunes(fila)
            for _, fila in _maquinarias_seleccionadas().iterrows()
        ]
        return render_template(
            "etiquetas.html",
            etiquetas=etiquetas_generadas,
        )

    @app.route("/fichas", methods=["POST"])
    @login_required
    def fichas():
        fichas_generadas = []
        for _, fila in _maquinarias_seleccionadas().iterrows():
            ficha = _datos_comunes(fila)
            ficha.update(
                {
                    "marca": fila["marca"],
                    "modelo": fila["modelo"],
                    "serie": fila["numero_serie"],
                }
            )
            fichas_generadas.append(ficha)

        return render_template("fichas.html", fichas=fichas_generadas)
