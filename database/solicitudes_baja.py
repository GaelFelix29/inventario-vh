import pandas as pd

from sqlalchemy import text
from database.maquinarias import baja_desde_solicitud
from models.auditoria_model import registrar_movimiento

from database.conexion import engine


# ======================================================
# GUARDAR SOLICITUD
# ======================================================

def guardar_solicitud(datos):

    sql = text("""

        INSERT INTO solicitudes_baja(

            id_activo,
            solicitante,
            motivo,
            observaciones,
            prioridad

        )

        VALUES(

            :id_activo,
            :solicitante,
            :motivo,
            :observaciones,
            :prioridad

        )

    """)

    with engine.begin() as conn:

        conn.execute(sql, datos)


# ======================================================
# TODAS LAS SOLICITUDES
# ======================================================

def obtener_solicitudes():

    sql = """

        SELECT *

        FROM solicitudes_baja

        ORDER BY fecha DESC

    """

    return pd.read_sql(sql, engine)


# ======================================================
# PENDIENTES
# ======================================================

def obtener_pendientes():

    sql = """

        SELECT *

        FROM solicitudes_baja

        WHERE estado='Pendiente'

        ORDER BY fecha ASC

    """

    return pd.read_sql(sql, engine)


# ======================================================
# APROBAR
# ======================================================


def aprobar_solicitud(id, administrador, comentario):

    with engine.begin() as conn:

        # ==========================================
        # 1. OBTENER LA SOLICITUD
        # ==========================================

        sql = text("""

            SELECT *

            FROM solicitudes_baja

            WHERE id = :id

        """)

        solicitud = conn.execute(

            sql,

            {"id": id}

        ).mappings().first()

        if not solicitud:

            raise Exception("La solicitud no existe.")

        if solicitud["estado"] != "Pendiente":

            raise Exception("La solicitud ya fue procesada.")

        # ==========================================
        # 2. APROBAR LA SOLICITUD
        # ==========================================

        sql_update = text("""

            UPDATE solicitudes_baja

            SET

                estado='Aprobada',

                aprobado_por=:admin,

                fecha_aprobacion=NOW(),

                comentario_admin=:comentario

            WHERE id=:id

        """)

        conn.execute(sql_update, {

            "admin": administrador,

            "comentario": comentario,

            "id": id

        })

        # ==========================================
        # 3. OBTENER DATOS PARA DAR DE BAJA
        # ==========================================

        sql_select = text("""

            SELECT

                id_activo,

                motivo

            FROM solicitudes_baja

            WHERE id=:id

        """)

        fila = conn.execute(

            sql_select,

            {"id": id}

        ).fetchone()

        # ==========================================
        # 4. DAR DE BAJA EL ACTIVO
        # ==========================================

        if fila:

            baja_desde_solicitud(

                conn,

                fila.id_activo,

                fila.motivo,

                administrador

            )

            registrar_movimiento(

                usuario=administrador,

                accion="Aprobó solicitud de baja",

                modulo="Solicitudes",

                referencia=fila.id_activo,

                conn=conn

            )

# ======================================================
# RECHAZAR
# ======================================================

def rechazar_solicitud(id, administrador, comentario):

    sql = text("""

        UPDATE solicitudes_baja

        SET

            estado='Rechazada',

            aprobado_por=:admin,

            comentario_admin=:comentario,

            fecha_aprobacion=NOW()

        WHERE id=:id

    """)

    with engine.begin() as conn:

        conn.execute(sql, {

            "admin": administrador,

            "comentario": comentario,

            "id": id

        })


def obtener_solicitud(id):

    sql = text("""

        SELECT *

        FROM solicitudes_baja

        WHERE id=:id

    """)

    return pd.read_sql(
        sql,
        engine,
        params={"id": id}
    ).iloc[0]

def existe_solicitud_pendiente(id_activo):

    sql = text("""

        SELECT COUNT(*) AS total

        FROM solicitudes_baja

        WHERE id_activo=:id

        AND estado='Pendiente'

    """)

    with engine.begin() as conn:

        total = conn.execute(
            sql,
            {"id": id_activo}
        ).scalar()

    return total > 0