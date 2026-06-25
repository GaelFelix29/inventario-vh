from flask import Flask, render_template
import pandas as pd
import os

app = Flask(__name__)

# ==========================================
# RUTA DEL EXCEL
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_EXCEL = os.path.join(
    BASE_DIR,
    "data",
    "INVENTARIO-MAQUINAS_GAEL Conteo.xlsx"
)

# ==========================================
# PAGINA PRINCIPAL
# ==========================================

@app.route("/")
def inicio():
    return render_template("index.html")


# ==========================================
# FICHA DE MAQUINA
# ==========================================

@app.route("/<codigo>")
def maquina(codigo):

    try:
        df = pd.read_excel(
            ARCHIVO_EXCEL,
            sheet_name="MAQUINARIAS",
            header=6,
            engine="openpyxl"
        )

        # Quitar espacios de los nombres de columnas
        df.columns = df.columns.str.strip()

    except Exception as e:
        return f"""
        <h2>Error al abrir el Excel</h2>
        <pre>{e}</pre>
        <hr>
        <pre>{ARCHIVO_EXCEL}</pre>
        """

    # Buscar el activo
    fila = df[df["ID ACTIVO"].astype(str).str.upper() == codigo.upper()]

    if fila.empty:
        return f"""
        <h2>Activo no encontrado</h2>
        <p>{codigo}</p>
        """

    datos = fila.iloc[0].to_dict()

    # Reemplazar valores vacíos
    for campo, valor in datos.items():

        if pd.isna(valor):
            datos[campo] = ""
            continue

        # Formato de fechas
        if "Fecha" in campo:
            try:
                datos[campo] = pd.to_datetime(valor).strftime("%d/%m/%Y")
            except:
                pass

        # Formato monetario
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


if __name__ == "__main__":
    app.run(debug=True)