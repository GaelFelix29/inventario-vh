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
    
