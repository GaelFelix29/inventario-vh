from flask import Flask, render_template
import pandas as pd
import os

app = Flask(__name__)

# ==========================================
# RUTA DEL EXCEL (Compatible con Render)
# ==========================================

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

    <p>Ejemplo:</p>

    <a href="/ACT-0001">ACT-0001</a>
    """


@app.route("/<codigo>")
def maquina(codigo):

    # ==========================================
    # LEER EXCEL
    # ==========================================

    try:
        df = pd.read_excel(ARCHIVO_EXCEL)
    except Exception as e:
        return f"""
        <h2>Error al abrir el archivo Excel</h2>

        <pre>{e}</pre>

        <hr>

        <b>Ruta utilizada:</b>

        <pre>{ARCHIVO_EXCEL}</pre>
        """

    # ==========================================
    # BUSCAR ACTIVO
    # ==========================================

    columna = "ID_ACTIVO"

    if columna not in df.columns:
        return f"""
        <h2>No existe la columna:</h2>

        <pre>{columna}</pre>

        <h3>Columnas encontradas:</h3>

        <pre>{list(df.columns)}</pre>
        """

    fila = df[df[columna].astype(str).str.upper() == codigo.upper()]

    if fila.empty:
        return f"""
        <h2>Activo no encontrado</h2>

        <p>{codigo}</p>
        """

    datos = fila.iloc[0].to_dict()

    # ==========================================
    # FORMATO DE DATOS
    # ==========================================

    for campo, valor in datos.items():

        if pd.isna(valor):
            datos[campo] = "Sin información"
            continue

        if "Fecha" in campo:
            try:
                datos[campo] = pd.to_datetime(valor).strftime("%d/%m/%Y")
            except:
                pass

        if campo == "Valor_MX":
            datos[campo] = "${:,.2f} MXN".format(float(valor))

        if campo == "Precio_Unitario_US":
            datos[campo] = "${:,.2f} USD".format(float(valor))

        if campo == "Total_US":
            datos[campo] = "${:,.2f} USD".format(float(valor))

    # ==========================================
    # ENVIAR AL HTML
    # ==========================================

    return render_template(
        "maquina.html",
        datos=datos
    )


if __name__ == "__main__":
    app.run(debug=True)