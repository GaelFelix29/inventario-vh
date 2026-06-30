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