import pandas as pd

from database.conexion import engine


def obtener_bajas():

    sql = """

        SELECT *

        FROM bajas

    """

    return pd.read_sql(sql, engine)