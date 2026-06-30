from sqlalchemy import text
from database.conexion import engine


# ==========================================
# REGISTRAR MOVIMIENTO
# ==========================================

def registrar_movimiento(usuario,
                          accion,
                          modulo,
                          referencia=""):

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

    with engine.begin() as conn:

        conn.execute(sql, {

            "usuario": usuario,
            "accion": accion,
            "modulo": modulo,
            "referencia": referencia

        })


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