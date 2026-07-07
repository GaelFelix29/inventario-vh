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

    SELECT
        m.*,
        a.origen

    FROM maquinarias m

    LEFT JOIN aduanas a
        ON m.id_activo = a.id_activo

    ORDER BY m.id_activo""")

    with engine.connect() as conn:

        maquinas = conn.execute(sql).mappings().all()

        resultado = []

        for maquina in maquinas:

            maquina = dict(maquina)
            
            maquina["tipo"] = obtener_tipo_expediente(
            maquina.get("origen"))
            
            resultado.append(maquina)
            
    return resultado
    
    

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
            fecha_alta,
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
            :fecha_alta,
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
        fecha_alta = :fecha_alta,
        precio_unitario_us = :precio_unitario_us,
        total_us = :total_us,
        valor_mx = :valor_mx,
        observaciones = :observaciones

    WHERE id_activo = :id_activo

    """)

    with engine.begin() as conn:

        conn.execute(sql, datos)
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

def obtener_activos_vecinos(id_activo):

    sql = text("""

        SELECT
            (
                SELECT id_activo
                FROM maquinarias
                WHERE id_activo < :id
                ORDER BY id_activo DESC
                LIMIT 1
            ) AS anterior,

            (
                SELECT id_activo
                FROM maquinarias
                WHERE id_activo > :id
                ORDER BY id_activo
                LIMIT 1
            ) AS siguiente

    """)

    with engine.connect() as conn:

        return conn.execute(
            sql,
            {"id": id_activo}
        ).mappings().first()
    

def buscar_activos(texto):

    sql = text("""

        SELECT
            id_activo,
            descripcion,
            categoria,
            marca,
            ubicacion
        FROM maquinarias
        WHERE
            id_activo LIKE :q
            OR descripcion LIKE :q
            OR categoria LIKE :q
            OR marca LIKE :q
            OR ubicacion LIKE :q
        ORDER BY id_activo
        LIMIT 20

    """)

    with engine.connect() as conn:

        resultado = conn.execute(
            sql,
            {"q": f"%{texto}%"}
        ).mappings().all()

        return [dict(fila) for fila in resultado]
    
def obtener_tipo_expediente(origen):
    if not origen:
        return {
            "nombre": "Sin clasificar",
            "color": "secondary",
            "icono": "question-circle"
        }

    origen = origen.strip().upper()

    if origen in ("MEXICO", "NACIONAL"):
        return {
            "nombre": "Nacional",
            "color": "success",
            "icono": "flag"
        }

    if origen == "PENDIENTE":
        return {
            "nombre": "Pendiente",
            "color": "warning",
            "icono": "clock-history"
        }

    if origen == "REINGRESO":
        return {
            "nombre": "importado",
            "color": "primary",
            "icono": "globe-americas"
        }

    if origen == "NA":
        return {
            "nombre": "Sin clasificar",
            "color": "secondary",
            "icono": "question-circle"
        }

    return {
        "nombre": "Importado",
        "color": "primary",
        "icono": "globe-americas"
    }
    
def obtener_estadisticas_maquinarias():

    sql = text("""

        SELECT
            COUNT(*) AS total,

            SUM(
                CASE
                    WHEN a.origen IN ('CHINA','REINGRESO')
                    THEN 1
                    ELSE 0
                END
            ) AS importados,

            SUM(
                CASE
                    WHEN a.origen IN ('MEXICO','NACIONAL')
                    THEN 1
                    ELSE 0
                END
            ) AS nacionales,

            SUM(
                CASE
                    WHEN a.origen='PENDIENTE'
                    THEN 1
                    ELSE 0
                END
            ) AS pendientes

        FROM maquinarias m

        LEFT JOIN aduanas a

            ON m.id_activo=a.id_activo

    """)

    with engine.connect() as conn:

        return conn.execute(sql).mappings().first()

def obtener_ubicaciones():

    sql = text("""

        SELECT DISTINCT ubicacion

        FROM maquinarias

        WHERE ubicacion IS NOT NULL
        AND TRIM(ubicacion) <> ''

        ORDER BY ubicacion

    """)

    with engine.connect() as conn:

        return conn.execute(sql).scalars().all()