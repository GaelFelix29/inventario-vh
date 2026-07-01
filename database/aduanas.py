import pandas as pd
from sqlalchemy import text
from database.conexion import engine


def obtener_aduanas():

    sql = """

        SELECT *

        FROM aduanas

    """

    return pd.read_sql(sql, engine)


def crear_registro_aduana_vacio(id_activo):

    sql = text("""

        INSERT INTO aduanas(

            id_activo

        )

        VALUES(

            :id_activo

        )

    """)

    with engine.begin() as conn:

        conn.execute(sql, {

            "id_activo": id_activo

        })

def guardar_aduana(
    id_activo,
    factura,
    pedimento,
    entrada_mtz,
    id_imp,
    inbond,
    origen,
    fecha_importacion
):

    if fecha_importacion == "":
        fecha_importacion = None

    with engine.begin() as conn:

        existe = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM aduanas
                WHERE id_activo=:id
            """),
            {"id": id_activo}
        ).scalar()

        if existe:

            conn.execute(text("""

                UPDATE aduanas
                SET
                    factura=:factura,
                    pedimento=:pedimento,
                    entrada_mtz=:entrada_mtz,
                    id_imp=:id_imp,
                    inbond=:inbond,
                    origen=:origen,
                    fecha_importacion=:fecha_importacion
                WHERE id_activo=:id_activo

            """),{

                "id_activo":id_activo,
                "factura":factura,
                "pedimento":pedimento,
                "entrada_mtz":entrada_mtz,
                "id_imp":id_imp,
                "inbond":inbond,
                "origen":origen,
                "fecha_importacion":fecha_importacion

            })

        else:

            conn.execute(text("""

                INSERT INTO aduanas
                (
                    id_activo,
                    factura,
                    pedimento,
                    entrada_mtz,
                    id_imp,
                    inbond,
                    origen,
                    fecha_importacion
                )
                VALUES
                (
                    :id_activo,
                    :factura,
                    :pedimento,
                    :entrada_mtz,
                    :id_imp,
                    :inbond,
                    :origen,
                    :fecha_importacion
                )

            """),{

                "id_activo":id_activo,
                "factura":factura,
                "pedimento":pedimento,
                "entrada_mtz":entrada_mtz,
                "id_imp":id_imp,
                "inbond":inbond,
                "origen":origen,
                "fecha_importacion":fecha_importacion

            })

def obtener_aduana(id_activo):

    sql = text("""

        SELECT *

        FROM aduanas

        WHERE id_activo=:id_activo

    """)

    return pd.read_sql(

        sql,

        engine,

        params={

            "id_activo": id_activo

        }

    )

def obtener_aduana(id_activo):

    sql = text("""

        SELECT *

        FROM aduanas

        WHERE id_activo=:id

        LIMIT 1

    """)

    with engine.begin() as conn:

        fila = conn.execute(
            sql,
            {"id": id_activo}
        ).mappings().first()

    return fila

def obtener_aduana(id_activo):

    sql = text("""
        SELECT *
        FROM aduanas
        WHERE id_activo = :id
        LIMIT 1
    """)

    with engine.begin() as conn:

        fila = conn.execute(
            sql,
            {"id": id_activo}
        ).mappings().first()

    return fila

def actualizar_aduana(
    id_activo,
    factura,
    pedimento,
    entrada_mtz,
    id_imp,
    inbond,
    origen,
    fecha_importacion
):

    sql = text("""
        UPDATE aduanas
        SET
            factura = :factura,
            pedimento = :pedimento,
            entrada_mtz = :entrada_mtz,
            id_imp = :id_imp,
            inbond = :inbond,
            origen = :origen,
            fecha_importacion = :fecha_importacion
        WHERE id_activo = :id_activo
    """)

    with engine.begin() as conn:

        conn.execute(
            sql,
            {
                "id_activo": id_activo,
                "factura": factura,
                "pedimento": pedimento,
                "entrada_mtz": entrada_mtz,
                "id_imp": id_imp,
                "inbond": inbond,
                "origen": origen,
                "fecha_importacion": fecha_importacion
            }
        )

def estado_expediente_aduanal(aduana):

    campos = [
        ("factura", "Factura"),
        ("pedimento", "Pedimento"),
        ("entrada_mtz", "Entrada MTZ"),
        ("id_imp", "ID IMP"),
        ("inbond", "Inbond"),
        ("origen", "Origen"),
        ("fecha_importacion", "Fecha de Importación")
    ]

    if not aduana:

        return {
            "porcentaje": 0,
            "estado": "Sin expediente",
            "color": "danger",
            "completos": 0,
            "pendientes": len(campos),
            "total": len(campos),
            "faltantes": [c[1] for c in campos]
        }

    completos = 0
    faltantes = []

    for campo, nombre in campos:

        valor = aduana.get(campo)

        if valor is None or str(valor).strip() == "":
            faltantes.append(nombre)
        else:
            completos += 1

    pendientes = len(campos) - completos

    porcentaje = round((completos / len(campos)) * 100)

    if porcentaje == 100:

        estado = "Completo"
        color = "success"

    elif porcentaje == 0:

        estado = "Sin expediente"
        color = "danger"

    else:

        estado = "Incompleto"
        color = "warning"

    return {

        "porcentaje": porcentaje,

        "estado": estado,

        "color": color,

        "completos": completos,

        "pendientes": pendientes,

        "total": len(campos),

        "faltantes": faltantes

    }