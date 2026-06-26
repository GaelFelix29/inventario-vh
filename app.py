from flask import Flask
from flask import render_template
from flask import jsonify
from flask import request
import pandas as pd

from database.maquinarias import obtener_maquinarias
from database.maquinarias import obtener_maquinaria

from database.aduanas import obtener_aduanas

import qrcode
import base64

from io import BytesIO

app = Flask(__name__)

# ==========================================================
# INICIO
# ==========================================================

@app.route("/")
def inicio():

    return render_template("index.html")

# ==========================================================
# DASHBOARD
# ==========================================================

@app.route("/dashboard")
def dashboard():

    return render_template("dashboard.html")


# ==========================================================
# DATOS DASHBOARD
# ==========================================================

@app.route("/dashboard/datos")
def dashboard_datos():

    maq = obtener_maquinarias()
    aduana = obtener_aduanas()

    # ==========================
    # KPIs
    # ==========================

    total = len(maq)

    bajas = maq["fecha_baja"].notna().sum()

    activos = total - bajas

    valor = maq["valor_mx"].fillna(0).sum()

    # ==========================
    # ORIGEN
    # ==========================

    origen = (
        aduana["origen"]
        .fillna("SIN DATO")
        .value_counts()
    )

    # ==========================
    # DOCUMENTACION
    # ==========================

    documentacion = (
        aduana["documentacion_completa"]
        .fillna("NO")
        .value_counts()
    )

    # ==========================
    # TOP MAQUINARIAS
    # ==========================

    top = (
        maq["categoria"]
        .fillna("SIN DATO")
        .value_counts()
        .head(10)
    )

    # ==========================
    # VALOR POR ORIGEN
    # ==========================

    valor_origen = (
        aduana
        .merge(
            maq[["id_activo","valor_mx"]],
            on="id_activo",
            how="left"
        )
        .groupby("origen")["valor_mx"]
        .sum()
    )

    return jsonify({

        "kpi":{

            "total": int(total),

            "activos": int(activos),

            "bajas": int(bajas),

            "valor": float(valor)

        },

        "origen":{

            "labels": origen.index.tolist(),

            "values": origen.values.tolist()

        },

        "documentacion":{

            "labels": documentacion.index.tolist(),

            "values": documentacion.values.tolist()

        },

        "top":{

            "labels": top.index.tolist(),

            "values": top.values.tolist()

        },

        "valorOrigen":{

            "labels": valor_origen.index.tolist(),

            "values": valor_origen.values.tolist()

        }

    })

@app.route("/<codigo>")
def maquina(codigo):

    df = obtener_maquinaria(codigo)

    if df.empty:
        return "Activo no encontrado", 404

    maquina = df.iloc[0].to_dict()

    return render_template(
        "maquina.html",
        maquina=maquina
    )


# ==========================================================
# IMPRIMIR QR
# ==========================================================

@app.route("/imprimir")
def imprimir_qr():

    maquinas = obtener_maquinarias()

    return render_template(
        "imprimir-qr.html",
        maquinas=maquinas.to_dict("records")
    )


# ==========================================================
# GENERAR ETIQUETAS
# ==========================================================

@app.route("/etiquetas", methods=["POST"])
def etiquetas():

    datos = request.get_json()

    codigos = datos["codigos"]

    maquinas = obtener_maquinarias()

    maquinas = maquinas[
        maquinas["id_activo"].isin(codigos)
    ]

    etiquetas = []

    for _, fila in maquinas.iterrows():

        url = request.host_url + fila["id_activo"]

        qr = qrcode.make(url)

        buffer = BytesIO()

        qr.save(buffer, format="PNG")

        qr64 = base64.b64encode(
            buffer.getvalue()
        ).decode()

        etiquetas.append({

            "codigo": fila["id_activo"],

            "nombre": fila["descripcion"],

            "estado":
                "BAJA"
                if pd.notna(fila["fecha_baja"])
                else "ACTIVO",

            "url": url,

            "qr": qr64

        })

    return render_template(
        "etiquetas.html",
        etiquetas=etiquetas
    )
# ==========================================================
# SERVIDOR
# ==========================================================

if __name__ == "__main__":

    app.run(debug=True)