from sqlalchemy import text
from database.conexion import engine


# ==========================================
# REGISTRAR MOVIMIENTO
# ==========================================

def registrar_movimiento(
    usuario,
    accion,
    modulo,
    referencia="",
    conn=None
):

    sql = text("""

        INSERT INTO auditoria
        (

            usuario,
            accion,
            modulo,
            referencia

        )

        VALUES
        (

            :usuario,
            :accion,
            :modulo,
            :referencia

        )

    """)

    parametros = {

        "usuario": usuario,
        "accion": accion,
        "modulo": modulo,
        "referencia": referencia

    }

    # Si ya existe una transacción, usarla
    if conn is not None:

        conn.execute(sql, parametros)

    # Si no existe, abrir una nueva
    else:

        with engine.begin() as conexion:

            conexion.execute(sql, parametros)



# ==========================================
# OBTENER HISTORIAL
# ==========================================

def obtener_historial():

    sql = text("""

        SELECT *

        FROM auditoria

        ORDER BY fecha DESC

    """)

    with engine.connect() as conn:

        resultado = conn.execute(sql)

        return resultado.mappings().all()
    
def obtener_historial_activo(id_activo):

    sql = text("""

        SELECT

            fecha,
            usuario,
            accion,
            modulo

        FROM auditoria

        WHERE referencia = :id

        ORDER BY fecha DESC

    """)

    with engine.connect() as conn:

        resultado = conn.execute(
            sql,
            {"id": id_activo}
        )

        return resultado.mappings().all()


def registrar_activo_reciente(usuario, id_activo):

    print("ENTRÓ A registrar_activo_reciente")
    print(usuario)
    print(id_activo)

    sql = text("""

        INSERT INTO activos_recientes
        (
            usuario,
            id_activo
        )
        VALUES
        (
            :usuario,
            :id_activo
        )

    """)

    with engine.begin() as conn:

        conn.execute(sql, {

            "usuario": usuario,
            "id_activo": id_activo

        })
    print("INSERT REALIZADO")

def obtener_activos_recientes(usuario):

    sql = text("""

        SELECT
            ar.id_activo,
            m.descripcion,
            m.ubicacion

        FROM activos_recientes ar

        INNER JOIN maquinarias m
            ON ar.id_activo = m.id_activo

        WHERE ar.usuario = :usuario

        GROUP BY
            ar.id_activo,
            m.descripcion,
            m.ubicacion

        ORDER BY MAX(ar.fecha) DESC

        LIMIT 2

    """)

    with engine.connect() as conn:

        resultado = conn.execute(
            sql,
            {"usuario": usuario}
        ).mappings().all()

        return [dict(r) for r in resultado]