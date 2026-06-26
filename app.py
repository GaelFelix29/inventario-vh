from flask import Flask, render_template, request
import pandas as pd
import os
import qrcode
import base64
from flask import jsonify
import numpy as np
from io import BytesIO

app = Flask(__name__)

# ==========================================================
# RUTA DEL EXCEL
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_EXCEL = os.path.join(
    BASE_DIR,
    "data",
    "INVENTARIO-MAQUINAS_GAEL Conteo.xlsx"
)

# ==========================================================
# INICIO
# ==========================================================

@app.route("/")
def inicio():

    return render_template("index.html")


# ==========================================================
# DETALLE DE UN ACTIVO
# ==========================================================

@app.route("/<codigo>")
def maquina(codigo):

    try:

        df = pd.read_excel(
            ARCHIVO_EXCEL,
            sheet_name="MAQUINARIAS",
            header=6,
            engine="openpyxl"
        )

        df.columns = df.columns.str.strip()

    except Exception as e:

        return f"""
        <h2>Error al abrir el Excel</h2>
        <pre>{e}</pre>
        <hr>
        <pre>{ARCHIVO_EXCEL}</pre>
        """

    df["ID ACTIVO"] = (
        df["ID ACTIVO"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    codigo = codigo.strip().upper()

    fila = df[df["ID ACTIVO"] == codigo]

    if fila.empty:

        return f"""
        <h2>Activo no encontrado</h2>
        <p>{codigo}</p>
        """

    datos = fila.iloc[0].to_dict()

    for campo, valor in datos.items():

        if pd.isna(valor):

            datos[campo] = ""
            continue

        if "Fecha" in campo:

            try:

                datos[campo] = pd.to_datetime(valor).strftime("%d/%m/%Y")

            except:

                pass

        if campo == "Precio Unitario US":

            datos[campo] = "${:,.2f} USD".format(float(valor))

        if campo == "Total US":

            datos[campo] = "${:,.2f} USD".format(float(valor))

        if campo == "Valor MX":

            datos[campo] = "${:,.2f} MXN".format(float(valor))

    return render_template(
        "maquina.html",
        maquina=datos
    )


# ==========================================================
# PÁGINA PARA IMPRIMIR QR
# ==========================================================

@app.route("/imprimir")
def imprimir():

    df = pd.read_excel(
        ARCHIVO_EXCEL,
        sheet_name="MAQUINARIAS",
        header=6,
        engine="openpyxl"
    )

    df.columns = df.columns.str.strip()

    maquinas = df.to_dict(orient="records")

    return render_template(
        "imprimir-qr.html",
        maquinas=maquinas
    )
# ==========================================================
# GENERAR ETIQUETAS QR
# ==========================================================

@app.route("/etiquetas", methods=["POST"])
def etiquetas():

    datos = request.get_json()

    if not datos:
        return "No se recibieron datos.", 400

    codigos = datos.get("codigos", [])
    copias = int(datos.get("copias", 1))
    tamano = datos.get("tamano", "3")

    if len(codigos) == 0:
        return "No se seleccionó ningún activo.", 400

    try:

        df = pd.read_excel(
            ARCHIVO_EXCEL,
            sheet_name="MAQUINARIAS",
            header=6,
            engine="openpyxl"
        )

    except Exception as e:

        return f"Error al abrir el Excel: {e}", 500

    df.columns = df.columns.str.strip()

    df["ID ACTIVO"] = (
        df["ID ACTIVO"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    etiquetas = []

    print("\n=========== CÓDIGOS RECIBIDOS ===========")
    print(codigos)

    for codigo in codigos:

        codigo = str(codigo).strip().upper()

        print(f"Buscando activo: {codigo}")

        resultado = df[df["ID ACTIVO"] == codigo]

        if resultado.empty:

            print(f"No encontrado: {codigo}")
            continue

        fila = resultado.iloc[0]

        url = request.host_url.rstrip("/") + "/" + codigo

        qr = generar_qr(url)

        for _ in range(copias):

            etiquetas.append({

                "codigo": codigo,

                "nombre": str(fila.get("Categoría", "")),

                "estado": str(fila.get("Estado", "")),

                "ubicacion": str(fila.get("Ubicación Final", "")),

                "tamano": tamano,

                "qr": qr,

                "url": url

            })

    print("\n=========== ETIQUETAS GENERADAS ===========")
    print(f"TOTAL: {len(etiquetas)}")

    return render_template(
        "etiquetas.html",
        etiquetas=etiquetas,
        tamano=tamano,
        copias=copias
    )


# ==========================================================
# GENERAR IMAGEN QR
# ==========================================================

def generar_qr(texto):

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2
    )

    qr.add_data(texto)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = BytesIO()

    img.save(buffer, format="PNG")

    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

from flask import jsonify

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/dashboard/datos")
def dashboard_datos():

    # ===========================
    # LEER MAQUINARIAS
    # ===========================

    maq = pd.read_excel(
        ARCHIVO_EXCEL,
        sheet_name="MAQUINARIAS",
        header=6,
        engine="openpyxl"
    )

    maq.columns = maq.columns.str.strip()

    # ===========================
    # LEER ADUANA
    # ===========================

    aduana = pd.read_excel(
        ARCHIVO_EXCEL,
        sheet_name="ADUANA",
        header=6,
        engine="openpyxl"
    )

    aduana.columns = aduana.columns.str.strip()

    # ===========================
    # LEER BAJAS
    # ===========================

    bajas = pd.read_excel(
        ARCHIVO_EXCEL,
        sheet_name="BAJAS",
        header=6,
        engine="openpyxl"
    )

    bajas.columns = bajas.columns.str.strip()

    # ===========================
    # LIMPIAR DATOS
    # ===========================

    maq = maq.fillna("")
    aduana = aduana.fillna("")
    bajas = bajas.fillna("")

        # ==========================================
    # TOTALES
    # ==========================================

    total_activos = len(maq)

    activos = len(
        maq[
            maq["Estado"]
            .astype(str)
            .str.upper()
            .str.strip()
            == "ACTIVO"
        ]
    )

    total_bajas = len(bajas)

    # ==========================================
    # VALOR TOTAL MX
    # ==========================================

    maq["Valor MX"] = (
        maq["Valor MX"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
    )

    maq["Valor MX"] = pd.to_numeric(
        maq["Valor MX"],
        errors="coerce"
    ).fillna(0)

    valor_total = round(
        maq["Valor MX"].sum(),
        2
    )

    # ==========================================
    # ORIGEN MAQUINARIA
    # ==========================================

    origen = (
        aduana["Origen"]
        .astype(str)
        .str.upper()
        .str.strip()
        .value_counts()
    )

    origen_labels = origen.index.tolist()
    origen_values = origen.values.tolist()

    # ==========================================
    # DOCUMENTACIÓN
    # ==========================================

    documentacion = (
        aduana["Documentación Completa"]
        .astype(str)
        .str.upper()
        .str.strip()
        .replace({
            "SI": "COMPLETA",
            "NO": "PENDIENTE"
        })
        .value_counts()
    )

    doc_labels = documentacion.index.tolist()
    doc_values = documentacion.values.tolist()

    # ==========================================
    # TOP 10 MAQUINARIAS
    # ==========================================

    top = (
        maq["Categoría"]
        .astype(str)
        .str.upper()
        .str.strip()
        .value_counts()
        .head(10)
    )

    top_labels = top.index.tolist()
    top_values = top.values.tolist()

        # ==========================================
    # VALOR POR ORIGEN
    # ==========================================

    origen_maquinas = aduana[["ID Activo", "Origen"]].copy()

    origen_maquinas["ID Activo"] = (
        origen_maquinas["ID Activo"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    maq["ID ACTIVO"] = (
        maq["ID ACTIVO"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    valor_origen = maq.merge(
        origen_maquinas,
        left_on="ID ACTIVO",
        right_on="ID Activo",
        how="left"
    )

    valor_por_origen = (
        valor_origen
        .groupby("Origen")["Valor MX"]
        .sum()
        .sort_values(ascending=False)
    )

    valor_origen_labels = valor_por_origen.index.fillna("SIN DATO").tolist()

    valor_origen_values = (
        valor_por_origen
        .round(2)
        .tolist()
    )

    # ==========================================
    # RESPUESTA JSON
    # ==========================================

    return jsonify({

        "kpi":{

            "total": total_activos,

            "activos": activos,

            "bajas": total_bajas,

            "valor": valor_total

        },

        "origen":{

            "labels": origen_labels,

            "values": origen_values

        },

        "documentacion":{

            "labels": doc_labels,

            "values": doc_values

        },

        "top":{

            "labels": top_labels,

            "values": top_values

        },

        "valorOrigen":{

            "labels": valor_origen_labels,

            "values": valor_origen_values

        }

    })


# ==========================================================
# INICIAR SERVIDOR
# ==========================================================

if __name__ == "__main__":

    app.run(debug=True)
