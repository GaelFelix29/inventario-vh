import pandas as pd

from database.conexion import engine

from sqlalchemy import text
from database.conexion import engine



def obtener_maquinarias():

    sql = """

        SELECT *

        FROM maquinarias

        ORDER BY id_activo

    """

    return pd.read_sql(sql, engine)


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

    if df.empty:
        return None

    return df.iloc[0].to_dict()

def obtener_todas_maquinas():

    sql = text("""

        SELECT *

        FROM maquinarias

        ORDER BY id_activo

    """)

    with engine.connect() as conn:

        return conn.execute(sql).mappings().all()
    

def insertar_maquinaria(datos):

    sql = text("""
        INSERT INTO maquinarias(

            id_activo,
            categoria,
            descripcion,
            cantidad,
            marca,
            modelo,
            numero_serie,
            serie_interna,
            proveedor,
            ubicacion,
            precio_unitario_us,
            total_us,
            valor_mx,
            observaciones

        )

        VALUES(

            :id_activo,
            :categoria,
            :descripcion,
            :cantidad,
            :marca,
            :modelo,
            :numero_serie,
            :serie_interna,
            :proveedor,
            :ubicacion,
            :precio_unitario_us,
            :total_us,
            :valor_mx,
            :observaciones

        )
    """)

    with engine.begin() as conn:
        conn.execute(sql, datos)
    
    

def siguiente_id_activo():

    sql = text("""

        SELECT id_activo

        FROM maquinarias

        ORDER BY id_activo DESC

        LIMIT 1

    """)

    with engine.connect() as conn:

        ultimo = conn.execute(sql).scalar()

    if not ultimo:

        return "ACT-0001"

    numero = int(ultimo.replace("ACT-", ""))

    numero += 1

    return f"ACT-{numero:04d}"

def obtener_maquinaria_detalle(id_activo):

    sql = text("""

        SELECT *

        FROM maquinarias

        WHERE id_activo=:id

    """)

    with engine.begin() as conn:

        fila = conn.execute(sql, {

            "id": id_activo

        }).mappings().first()

    return fila

def actualizar_maquinaria(datos):

    sql = text("""

    UPDATE maquinarias
    SET

        categoria = :categoria,
        descripcion = :descripcion,
        cantidad = :cantidad,
        marca = :marca,
        modelo = :modelo,
        numero_serie = :numero_serie,
        serie_interna = :serie_interna,
        proveedor = :proveedor,
        ubicacion = :ubicacion,
        precio_unitario_us = :precio_unitario_us,
        total_us = :total_us,
        valor_mx = :valor_mx,
        observaciones = :observaciones

    WHERE id_activo = :id_activo

    """)

    with engine.begin() as conn:

        conn.execute(sql, datos)

    
def baja_desde_solicitud(conn, id_activo, motivo, responsable):

    sql = text("""

        UPDATE maquinarias

        SET

            estado='BAJA',

            fecha_baja=CURDATE(),

            motivo_baja=:motivo,

            responsable_baja=:responsable,

            ultima_actualizacion=NOW()

        WHERE id_activo=:id

    """)

    conn.execute(sql, {

        "id": id_activo,

        "motivo": motivo,

        "responsable": responsable

    })

def obtener_maquinarias_select():

    sql = """

        SELECT
            id_activo,
            descripcion
        FROM maquinarias
        ORDER BY id_activo

    """

    return pd.read_sql(sql, engine)