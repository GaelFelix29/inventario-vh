import pandas as pd

from database.conexion import engine


def obtener_aduanas():

    sql = """

        SELECT *

        FROM aduanas

    """

    return pd.read_sql(sql, engine)