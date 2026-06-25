from flask import Flask, render_template
import pandas as pd
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_EXCEL = os.path.join(
    BASE_DIR,
    "data",
    "INVENTARIO-MAQUINAS_GAEL Conteo.xlsx"
)


@app.route("/")
def inicio():
    return """
    <h1>Inventario Vital Health</h1>

    <p>Escribe el código del activo después de la diagonal.</p>

    <a href="/ACT-0001">ACT-0001</a>
    """


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

        <pre>{ARCHIVO_EXCEL}</pre>
        """

    columna = "ID ACTIVO"

    fila = df[
        df[columna]
        .astype(str)
        .str.strip()
        .str.upper()
        == codigo.strip().upper()
    ]

    if fila.empty:

        return f"""
        <h2>Activo no encontrado</h2>

        <p>{codigo}</p>
        """

    datos = fila.iloc[0].to_dict()

    for campo, valor in datos.items():

        if pd.isna(valor):
            datos[campo] = "Sin información"
            continue

        if "Fecha" in campo:
            try:
                datos[campo] = pd.to_datetime(valor).strftime("%d/%m/%Y")
            except:
                pass

        if campo == "Valor MX":
            try:
                datos[campo] = "${:,.2f} MXN".format(float(valor))
            except:
                pass

        if campo == "Precio Unitario US":
            try:
                datos[campo] = "${:,.2f} USD".format(float(valor))
            except:
                pass

        if campo == "Total US":
            try:
                datos[campo] = "${:,.2f} USD".format(float(valor))
            except:
                pass

    return render_template(
        "maquina.html",
        datos=datos
    )


if __name__ == "__main__":
    app.run(debug=True)