from flask import Flask, render_template, request
import pandas as pd
import os
import qrcode
import base64
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


# ==========================================================
# INICIAR SERVIDOR
# ==========================================================

if __name__ == "__main__":

    app.run(debug=True)
