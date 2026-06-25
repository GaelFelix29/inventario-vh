from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

ARCHIVO_EXCEL = "data/INVENTARIO-MAQUINAS_GAEL Conteo.xlsx"

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

    # =============================
    # LEER EXCEL
    # =============================

    df = pd.read_excel(
        ARCHIVO_EXCEL,
        sheet_name="MAQUINARIAS",
        header=6
    )

    # =============================
    # LIMPIAR NOMBRES DE COLUMNAS
    # =============================

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(" ", "_", regex=False)
    )

    # =============================
    # BUSCAR COLUMNA ID
    # =============================

    columna_id = None

    for col in df.columns:

        nombre = col.upper()

        if "ID" in nombre and "ACT" in nombre:

            columna_id = col

            break

    if columna_id is None:

        return f"""
        <h2>No encontré la columna del ID.</h2>

        <br>

        {df.columns.tolist()}
        """

    # =============================
    # LIMPIAR DATOS
    # =============================

    df[columna_id] = (
        df[columna_id]
        .astype(str)
        .str.strip()
    )

    # =============================
    # BUSCAR ACTIVO
    # =============================

    fila = df[
        df[columna_id].str.upper() == codigo.upper()
    ]

    if fila.empty:

        return f"<h2>El activo {codigo} no existe.</h2>"

    datos = fila.iloc[0].to_dict()

    # =============================
    # FORMATO DE DATOS
    # =============================

    for campo, valor in datos.items():

        # Vacíos
        if pd.isna(valor):

            datos[campo] = "Sin información"

            continue

        # Fechas
        if "Fecha" in campo:

            try:

                datos[campo] = pd.to_datetime(
                    valor
                ).strftime("%d/%m/%Y")

            except:

                pass

        # Dinero USD
        if campo == "Precio_Unitario_US":

            datos[campo] = "${:,.2f} USD".format(
                float(valor)
            )

        if campo == "Total_US":

            datos[campo] = "${:,.2f} USD".format(
                float(valor)
            )

        # Dinero MXN
        if campo == "Valor_MX":

            datos[campo] = "${:,.2f} MXN".format(
                float(valor)
            )

    return render_template(
        "maquina.html",
        datos=datos
    )


if __name__ == "__main__":

    app.run(
        debug=True
    )