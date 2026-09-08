from sqlalchemy import text
from database.conexion import engine
from datetime import date, datetime, timedelta

ZONA_HORARIA_LOCAL = "-07:00"


# ==========================================
# REGISTRAR MOVIMIENTO
# ==========================================


def registrar_movimiento(usuario, accion, modulo, referencia="", conn=None):

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
        "referencia": referencia,
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

        resultado = conn.execute(sql, {"id": id_activo})

        return resultado.mappings().all()


# ==========================================
# OBTENER ACTIVIDAD FILTRADA
# ==========================================


def obtener_actividad_filtrada(
    rol,
    usuario_actual,
    fecha_desde=None,
    fecha_hasta=None,
    hora_desde=None,
    hora_hasta=None,
    modulo=None,
    limite=100,
):
    condiciones = []
    parametros = {}

    # ======================================
    # PERMISOS SEGÚN EL ROL
    # ======================================

    if rol == "Administrador":
        # El administrador puede consultar todo.
        pass

    elif rol == "Mantenimiento":
        condiciones.append("""
            (
                modulo IN (
                    'Accesorios',
                    'Movimientos',
                    'Solicitudes'
                )

                OR

                (
                    modulo = 'Maquinaria'

                    AND accion IN (
                        'Solicitó baja del activo',
                        'Solicitó mantenimiento del activo',
                        'Solicitó traslado del activo',
                        'Solicitó reactivación del activo',
                        'Confirmó recepción del activo',
                        'Finalizó mantenimiento del activo'
                    )
                )
            )
        """)

    elif rol == "Visualizador":
        condiciones.append("usuario = :usuario_actual")

        parametros["usuario_actual"] = usuario_actual

    else:
        # Un rol desconocido no recibe resultados.
        condiciones.append("1 = 0")

    # ======================================
    # FILTROS OPCIONALES
    # ======================================

    if fecha_desde:
        condiciones.append("""
            DATE(
                CONVERT_TZ(
                    fecha,
                    '+00:00',
                    :zona_horaria
                )
            ) >= :fecha_desde
        """)
        parametros["fecha_desde"] = fecha_desde

    if fecha_hasta:
        condiciones.append("""
            DATE(
                CONVERT_TZ(
                    fecha,
                    '+00:00',
                    :zona_horaria
                )
            ) <= :fecha_hasta
        """)
        parametros["fecha_hasta"] = fecha_hasta

    if hora_desde:
        condiciones.append("""
            TIME(
                CONVERT_TZ(
                    fecha,
                    '+00:00',
                    :zona_horaria
                )
            ) >= :hora_desde
        """)
        parametros["hora_desde"] = hora_desde

    if hora_hasta:
        condiciones.append("""
            TIME(
                CONVERT_TZ(
                    fecha,
                    '+00:00',
                    :zona_horaria
                )
            ) <= :hora_hasta
        """)
        parametros["hora_hasta"] = hora_hasta

    # ======================================
    # CONSTRUIR CONSULTA
    # ======================================

    where_sql = ""

    if condiciones:
        where_sql = "WHERE " + " AND ".join(condiciones)

    try:
        limite = int(limite)
    except (TypeError, ValueError):
        limite = 100

    limite = max(1, min(limite, 200))
    parametros["limite"] = limite
    parametros["zona_horaria"] = ZONA_HORARIA_LOCAL
    sql = text(f"""
        SELECT
            id,
            CONVERT_TZ(
            fecha,
            '+00:00',
            :zona_horaria
            ) AS fecha,
            usuario,
            accion,
            modulo,
            referencia

        FROM auditoria

        {where_sql}

        ORDER BY fecha DESC, id DESC

        LIMIT :limite
    """)

    with engine.connect() as conn:
        resultado = conn.execute(sql, parametros)

        return resultado.mappings().all()


# ==========================================
# ACTIVIDAD DE LOS ÚLTIMOS SIETE DÍAS
# ==========================================


def obtener_actividad_ultimos_7_dias(rol, usuario_actual):
    condiciones = ["fecha >= CURDATE() - INTERVAL 6 DAY"]

    parametros = {}

    # ======================================
    # PERMISOS SEGÚN EL ROL
    # ======================================

    if rol == "Administrador":
        pass

    elif rol == "Mantenimiento":
        condiciones.append("""
            (
                modulo IN (
                    'Accesorios',
                    'Movimientos',
                    'Solicitudes'
                )

                OR

                (
                    modulo = 'Maquinaria'

                    AND accion IN (
                        'Solicitó baja del activo',
                        'Solicitó mantenimiento del activo',
                        'Solicitó traslado del activo',
                        'Solicitó reactivación del activo',
                        'Confirmó recepción del activo',
                        'Finalizó mantenimiento del activo'
                    )
                )
            )
        """)

    elif rol == "Visualizador":
        condiciones.append("usuario = :usuario_actual")

        parametros["usuario_actual"] = usuario_actual

    else:
        condiciones.append("1 = 0")

    where_sql = "WHERE " + " AND ".join(condiciones)

    sql = text(f"""
        SELECT
            DATE(fecha) AS fecha_dia,
            COUNT(*) AS total

        FROM auditoria

        {where_sql}

        GROUP BY DATE(fecha)

        ORDER BY DATE(fecha)
    """)

    with engine.connect() as conn:
        resultado = conn.execute(sql, parametros).mappings().all()

    cantidades_por_fecha = {
        str(fila["fecha_dia"]): int(fila["total"]) for fila in resultado
    }

    etiquetas = []
    valores = []

    hoy = date.today()

    for dias_atras in range(6, -1, -1):
        fecha_actual = hoy - timedelta(days=dias_atras)

        clave = fecha_actual.isoformat()

        etiquetas.append(fecha_actual.strftime("%d/%m"))

        valores.append(cantidades_por_fecha.get(clave, 0))

    return {"etiquetas": etiquetas, "valores": valores}


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

        conn.execute(sql, {"usuario": usuario, "id_activo": id_activo})
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

        resultado = conn.execute(sql, {"usuario": usuario}).mappings().all()

        return [dict(r) for r in resultado]
