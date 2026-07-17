import pandas as pd

from sqlalchemy import text
from models.auditoria_model import registrar_movimiento

from database.conexion import engine

from database.maquinarias import (
    baja_desde_solicitud,
    traslado_desde_solicitud,
    mantenimiento_desde_solicitud
)


# ======================================================
# GUARDAR SOLICITUD
# ======================================================

def guardar_solicitud(datos):

    sql = text("""

        INSERT INTO solicitudes_baja(

            id_activo,
            solicitante,
            tipo,
            motivo,
            observaciones,
            prioridad,
            ubicacion_destino,
            proveedor_mantenimiento,
            fecha_estimada_fin

        )

        VALUES(

            :id_activo,
            :solicitante,
            :tipo,
            :motivo,
            :observaciones,
            :prioridad,
            :ubicacion_destino,
            :proveedor_mantenimiento,
            :fecha_estimada_fin

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


def aprobar_solicitud(id_solicitud, administrador, comentario):

    with engine.begin() as conn:

        # Obtener solicitud
        sql = text("""
            SELECT *
            FROM solicitudes_baja
            WHERE id = :id
        """)

        solicitud = conn.execute(
            sql,
            {"id": id_solicitud}
        ).mappings().first()

        if not solicitud:
            raise Exception("La solicitud no existe.")

        if solicitud["estado"] != "Pendiente":
            raise Exception("La solicitud ya fue procesada.")

        # Definir el nuevo estado de la solicitud
        if solicitud["tipo"] == "BAJA":
            nuevo_estado = "Finalizada"
        else:
            nuevo_estado = "En proceso"

        # Actualizar solicitud
        sql_update = text("""
        UPDATE solicitudes_baja
        SET
            estado = :estado,

            aprobado_por = :admin,

            fecha_aprobacion = NOW(),

            finalizado_por = CASE
                WHEN :estado = 'Finalizada' THEN :admin
                ELSE finalizado_por
            END,

            fecha_finalizacion = CASE
                WHEN :estado = 'Finalizada' THEN NOW()
                ELSE fecha_finalizacion
            END,

            comentario_admin = :comentario

        WHERE id = :id
        """)

        conn.execute(sql_update, {

            "id": id_solicitud,
            "estado": nuevo_estado,
            "admin": administrador,
            "comentario": comentario

        })

        # Ejecutar acción según el tipo
        if solicitud["tipo"] == "BAJA":

            baja_desde_solicitud(
                conn,
                solicitud["id_activo"],
                solicitud["motivo"],
                administrador
            )

        elif solicitud["tipo"] == "TRASLADO":

            traslado_desde_solicitud(
                conn,
                solicitud["id_activo"]
            )

        elif solicitud["tipo"] == "MANTENIMIENTO":

            mantenimiento_desde_solicitud(
                conn,
                solicitud["id_activo"]
            )

        registrar_movimiento(

            usuario=administrador,

            accion=f"Aprobó solicitud de {solicitud['tipo']}",

            modulo="Movimientos",

            referencia=solicitud["id_activo"],

            conn=conn

        )

# ======================================================
# RECHAZAR
# ======================================================

def rechazar_solicitud(id, administrador, comentario):

    with engine.begin() as conn:

        # Obtener el activo antes de actualizar
        sql = text("""

            SELECT id_activo

            FROM solicitudes_baja

            WHERE id=:id

        """)

        fila = conn.execute(

            sql,

            {"id": id}

        ).mappings().first()

        sql = text("""

            UPDATE solicitudes_baja

            SET

                estado='Rechazada',

                aprobado_por=:admin,

                comentario_admin=:comentario,

                fecha_aprobacion=NOW()

            WHERE id=:id

        """)

        conn.execute(sql, {

            "admin": administrador,

            "comentario": comentario,

            "id": id

        })

        if fila:

            registrar_movimiento(

                usuario=administrador,

                accion="Rechazó solicitud",

                modulo="Solicitudes",

                referencia=fila["id_activo"],

                conn=conn

            )


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