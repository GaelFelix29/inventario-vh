import pandas as pd

from database.conexion import engine


def obtener_maquinarias():

    sql = """

        SELECT *

        FROM maquinarias

        ORDER BY id_activo

    """

    return pd.read_sql(sql, engine)


from sqlalchemy import text

def obtener_maquinaria(codigo):

    sql = text("""
        SELECT *
        FROM maquinarias
        WHERE id_activo = :codigo
    """)

    df = pd.read_sql(
        sql,
        engine,
        params={"codigo": codigo}
    )

    return df