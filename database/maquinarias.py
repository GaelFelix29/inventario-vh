import pandas as pd

from database.conexion import engine

from sqlalchemy import text
from database.conexion import engine

import re
import unicodedata

from models.auditoria_model import registrar_movimiento


def obtener_maquinarias():

    sql = """

        SELECT *

        FROM maquinarias

        ORDER BY id_activo

    """

    return pd.read_sql(sql, engine)


def obtener_maquinarias_mobile(limite=20, offset=0):

    sql = text("""

        SELECT *

        FROM maquinarias

        ORDER BY id_activo

        LIMIT :limite OFFSET :offset

    """)

    return pd.read_sql(sql, engine, params={"limite": limite, "offset": offset})


def obtener_maquinaria(codigo):

    sql = text("""
        SELECT *
        FROM maquinarias
        WHERE id_activo = :codigo
    """)

    df = pd.read_sql(sql, engine, params={"codigo": codigo})

    if df.empty:
        return None

    return df.iloc[0].to_dict()


def obtener_todas_maquinas():

    sql = text("""

    SELECT
    m.*,
    a.origen,

    (
        SELECT COUNT(*)
        FROM asignaciones_accesorios aa
        WHERE aa.id_maquinaria = m.id_activo
        AND aa.estado = 'ACTIVA'
    ) AS cantidad_accesorios

FROM maquinarias m

    LEFT JOIN aduanas a
        ON m.id_activo = a.id_activo

    ORDER BY m.id_activo""")

    with engine.connect() as conn:

        maquinas = conn.execute(sql).mappings().all()

        resultado = []

        for maquina in maquinas:

            maquina = dict(maquina)

            maquina["tipo"] = obtener_tipo_expediente(maquina.get("origen"))

            resultado.append(maquina)

    return resultado


def insertar_maquinaria(datos):

    sql = text("""
        INSERT INTO maquinarias(
            id_activo,
            categoria,
            categoria_accesorio_id,
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
            :categoria_accesorio_id,
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

    datos_insertar = dict(datos)

    es_accesorio = (
        datos_insertar.get("categoria") or ""
    ).strip().upper() == "ACCESORIO"

    with engine.begin() as conn:

        categoria_accesorio_id = None

        if es_accesorio:

            categoria_accesorio_id = conn.execute(text("""
                    SELECT id
                    FROM categorias_accesorios
                    WHERE codigo = 'POR_CLASIFICAR'
                    AND activo = 1
                    LIMIT 1
                """)).scalar()

            if not categoria_accesorio_id:
                raise ValueError("No existe la categoría activa POR_CLASIFICAR.")

        datos_insertar["categoria_accesorio_id"] = categoria_accesorio_id

        conn.execute(sql, datos_insertar)


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

        fila = conn.execute(sql, {"id": id_activo}).mappings().first()

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

    conn.execute(sql, {"id": id_activo, "motivo": motivo, "responsable": responsable})


def traslado_desde_solicitud(conn, id_activo):

    sql = text("""

        UPDATE maquinarias

        SET

            estado='EN_TRASLADO',

            ultima_actualizacion=NOW()

        WHERE id_activo=:id

    """)

    conn.execute(sql, {"id": id_activo})


def mantenimiento_desde_solicitud(conn, id_activo):

    sql = text("""

        UPDATE maquinarias

        SET

            estado='EN_MANTENIMIENTO',

            ultima_actualizacion=NOW()

        WHERE id_activo=:id

    """)

    conn.execute(sql, {"id": id_activo})


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

        return conn.execute(sql, {"id": id_activo}).mappings().first()


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

        resultado = conn.execute(sql, {"q": f"%{texto}%"}).mappings().all()

        return [dict(fila) for fila in resultado]


def obtener_tipo_expediente(origen):
    if not origen:
        return {
            "nombre": "Sin clasificar",
            "color": "secondary",
            "icono": "question-circle",
        }

    origen = origen.strip().upper()

    if origen in ("MEXICO", "NACIONAL"):
        return {"nombre": "Nacional", "color": "success", "icono": "flag"}

    if origen == "PENDIENTE":
        return {"nombre": "Pendiente", "color": "warning", "icono": "clock-history"}

    if origen == "REINGRESO":
        return {"nombre": "importado", "color": "primary", "icono": "globe-americas"}

    if origen == "NA":
        return {
            "nombre": "Sin clasificar",
            "color": "secondary",
            "icono": "question-circle",
        }

    return {"nombre": "Importado", "color": "primary", "icono": "globe-americas"}


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


def confirmar_recepcion(conn, id_activo, nueva_ubicacion):

    sql = text("""

        UPDATE maquinarias

        SET

            estado='ACTIVO',

            ubicacion=:ubicacion,

            ultima_actualizacion=NOW()

        WHERE id_activo=:id

    """)

    conn.execute(sql, {"id": id_activo, "ubicacion": nueva_ubicacion})


def finalizar_mantenimiento(conn, id_activo):

    sql = text("""

        UPDATE maquinarias

        SET

            estado='ACTIVO',

            ultima_actualizacion=NOW()

        WHERE id_activo=:id

    """)

    conn.execute(sql, {"id": id_activo})


def confirmar_recepcion_activo(id_activo, usuario):

    with engine.begin() as conn:

        # Buscar el traslado en proceso
        sql = text("""
            SELECT ubicacion_destino
            FROM solicitudes_baja
            WHERE id_activo = :id
            AND tipo = 'TRASLADO'
            AND estado = 'En proceso'
            ORDER BY fecha_aprobacion DESC
            LIMIT 1
        """)

        fila = conn.execute(sql, {"id": id_activo}).mappings().first()

        if not fila:
            raise Exception("No existe un traslado en proceso para este activo.")

        # Confirmar recepción de la maquinaria
        confirmar_recepcion(conn, id_activo, fila["ubicacion_destino"])

        # Finalizar la solicitud
        sql = text("""
            UPDATE solicitudes_baja
            SET
                estado = 'Finalizada',
                fecha_finalizacion = NOW(),
                finalizado_por = :usuario
            WHERE id_activo = :id
            AND tipo = 'TRASLADO'
            AND estado = 'En proceso'
        """)

        conn.execute(sql, {"id": id_activo, "usuario": usuario})

        registrar_movimiento(
            usuario=usuario,
            accion="Confirmó recepción del traslado",
            modulo="Movimientos",
            referencia=id_activo,
            conn=conn,
        )


def finalizar_mantenimiento_activo(id_activo, usuario):

    with engine.begin() as conn:

        finalizar_mantenimiento(conn, id_activo)

        sql = text("""

        SELECT *

        FROM solicitudes_baja

        WHERE

            id_activo=:id

            AND tipo='MANTENIMIENTO'

        """)

        fila = conn.execute(sql, {"id": id_activo}).mappings().first()

        print(fila)

        sql = text("""

        UPDATE solicitudes_baja

        SET

            estado='Finalizada',

            fecha_finalizacion=NOW(),

            finalizado_por=:usuario

        WHERE

            id_activo=:id

            AND tipo='MANTENIMIENTO'

            AND estado='En proceso'

        """)

        conn.execute(sql, {"id": id_activo, "usuario": usuario})

        registrar_movimiento(
            usuario=usuario,
            accion="Finalizó mantenimiento del activo",
            modulo="Maquinaria",
            referencia=id_activo,
            conn=conn,
        )


# ==========================================
# OBTENER DOCUMENTO
# ==========================================


def obtener_documento(id_documento):

    sql = text("""

        SELECT *

        FROM documentos_maquinaria

        WHERE id = :id

    """)

    with engine.connect() as conn:

        return conn.execute(sql, {"id": id_documento}).mappings().first()


def reincorporar_desde_solicitud(conn, id_activo):

    sql = text("""
        UPDATE maquinarias
        SET

            estado = 'ACTIVO',

            ultima_actualizacion = NOW()

        WHERE id_activo = :id
    """)

    conn.execute(sql, {"id": id_activo})


def obtener_mantenimiento_en_proceso(id_activo):

    with engine.begin() as conn:

        sql = text("""
            SELECT *
            FROM solicitudes_baja
            WHERE id_activo = :id_activo
            AND tipo = 'MANTENIMIENTO'
            AND estado = 'En proceso'
            ORDER BY fecha DESC
            LIMIT 1
        """)

        return conn.execute(sql, {"id_activo": id_activo}).mappings().first()


def obtener_maquinarias_mobile_filtrado(
    q="", estado="", ubicacion="", tipo="", limite=20, offset=0
):

    sql = """
SELECT
    m.*,
    a.origen,

    (
        SELECT COUNT(*)
        FROM asignaciones_accesorios aa
        WHERE aa.id_maquinaria = m.id_activo
        AND aa.estado = 'ACTIVA'
    ) AS cantidad_accesorios

FROM maquinarias m
    
    LEFT JOIN aduanas a
        ON m.id_activo = a.id_activo
    WHERE 1=1
    """

    params = {}

    # ===============================
    # BUSCADOR
    # ===============================

    if q:

        sql += """

        AND (

            m.id_activo LIKE :q
            OR m.descripcion LIKE :q
            OR m.marca LIKE :q
            OR m.modelo LIKE :q
            OR m.ubicacion LIKE :q

        )

        """

        params["q"] = f"%{q}%"

    # ===============================
    # ESTADO
    # ===============================

    if estado:

        sql += """

        AND m.estado = :estado

        """

        params["estado"] = estado

    # ===============================
    # UBICACIÓN
    # ===============================

    if ubicacion:

        sql += """

        AND m.ubicacion = :ubicacion

        """

        params["ubicacion"] = ubicacion

    # ===============================
    # TIPO (NACIONAL / IMPORTADO)
    # ===============================

    if tipo:

        if tipo == "Importado":

            sql += """

            AND (
                a.origen IS NOT NULL
                AND UPPER(a.origen) <> 'NACIONAL'
            )

            """

        elif tipo == "Nacional":

            sql += """

            AND UPPER(a.origen) = 'NACIONAL'

            """

    # ===============================

    sql += """

    ORDER BY m.id_activo

    LIMIT :limite OFFSET :offset

    """

    params["limite"] = limite
    params["offset"] = offset

    return pd.read_sql(text(sql), engine, params=params)


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


def obtener_contenido_activo(id_activo):

    sql = text("""
        SELECT
            r.id,
            r.activo_origen,
            r.activo_relacionado,
            r.tipo_relacion,
            r.estado,
            r.fecha_inicio,
            r.observaciones,

            m.categoria,
            m.categoria_accesorio_id,
            m.descripcion,
            m.marca,
            m.modelo,
            m.numero_serie,
            m.ubicacion,

            ca.codigo AS categoria_accesorio_codigo,
            ca.nombre AS categoria_accesorio_nombre,

            aa.id AS asignacion_id,
            aa.id_maquinaria AS maquinaria_asignada_id,
            aa.fecha_asignacion,
            aa.asignado_por,

            destino.descripcion AS maquinaria_asignada_descripcion,
            destino.marca AS maquinaria_asignada_marca,
            destino.modelo AS maquinaria_asignada_modelo,
            destino.ubicacion AS maquinaria_asignada_ubicacion

        FROM relaciones_activos r

        INNER JOIN maquinarias m
            ON m.id_activo = r.activo_relacionado

        LEFT JOIN categorias_accesorios ca
            ON ca.id = m.categoria_accesorio_id

        LEFT JOIN asignaciones_accesorios aa
            ON aa.id_accesorio = m.id_activo
        AND aa.estado = 'ACTIVA'

        LEFT JOIN maquinarias destino
            ON destino.id_activo = aa.id_maquinaria

        WHERE r.activo_origen = :id_activo
        AND r.tipo_relacion = 'CONTIENE'
        AND r.estado = 'ACTIVA'

        ORDER BY r.fecha_inicio ASC
    """)

    with engine.connect() as conn:

        resultado = conn.execute(sql, {"id_activo": id_activo}).mappings().all()

        return [dict(fila) for fila in resultado]


def vincular_contenido_activo(
    activo_origen, activo_relacionado, usuario, observaciones=None
):

    sql = text("""
        INSERT INTO relaciones_activos (
            activo_origen,
            activo_relacionado,
            tipo_relacion,
            estado,
            observaciones,
            creado_por
        )
        VALUES (
            :activo_origen,
            :activo_relacionado,
            'CONTIENE',
            'ACTIVA',
            :observaciones,
            :creado_por
        )
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "activo_origen": activo_origen,
                "activo_relacionado": activo_relacionado,
                "observaciones": observaciones,
                "creado_por": usuario,
            },
        )


def retirar_contenido_activo(activo_origen, relacion_id, usuario):

    with engine.begin() as conn:

        contenedor = (
            conn.execute(
                text("""
                SELECT es_contenedor, estado_revision_contenido
                FROM maquinarias
                WHERE id_activo = :id
                FOR UPDATE
            """),
                {"id": activo_origen},
            )
            .mappings()
            .first()
        )

        if not contenedor:
            raise ValueError("El activo contenedor no existe.")

        if not contenedor["es_contenedor"]:
            raise ValueError("El activo no está marcado como contenedor.")

        if contenedor["estado_revision_contenido"] != "EN_REVISION":
            raise ValueError(
                "Solo se puede retirar contenido durante una revisión activa."
            )

        relacion = (
            conn.execute(
                text("""
                SELECT activo_relacionado, estado
                FROM relaciones_activos
                WHERE id = :relacion_id
                  AND activo_origen = :activo_origen
                  AND tipo_relacion = 'CONTIENE'
                FOR UPDATE
            """),
                {"relacion_id": relacion_id, "activo_origen": activo_origen},
            )
            .mappings()
            .first()
        )

        if not relacion:
            raise ValueError("La relación de contenido no existe para este contenedor.")

        if relacion["estado"] != "ACTIVA":
            raise ValueError("La relación de contenido ya no está activa.")

        conn.execute(
            text("""
                UPDATE relaciones_activos
                SET
                    estado = 'INACTIVA',
                    fecha_fin = NOW()
                WHERE id = :relacion_id
            """),
            {"relacion_id": relacion_id},
        )

        registrar_movimiento(
            usuario=usuario,
            accion=f"Retiró {relacion['activo_relacionado']} del contenido",
            modulo="Accesorios",
            referencia=activo_origen,
            conn=conn,
        )

        return relacion["activo_relacionado"]


def iniciar_revision_contenido(id_activo, usuario):

    with engine.begin() as conn:

        activo = (
            conn.execute(
                text("""
                SELECT es_contenedor, estado_revision_contenido
                FROM maquinarias
                WHERE id_activo = :id
                FOR UPDATE
            """),
                {"id": id_activo},
            )
            .mappings()
            .first()
        )

        if not activo:
            raise ValueError("El activo no existe.")

        if not activo["es_contenedor"]:
            raise ValueError("El activo no está marcado como contenedor.")

        if activo["estado_revision_contenido"] != "PENDIENTE":
            raise ValueError(
                "La revisión solo puede iniciarse desde el estado PENDIENTE."
            )

        conn.execute(
            text("""
                UPDATE maquinarias
                SET estado_revision_contenido = 'EN_REVISION'
                WHERE id_activo = :id
            """),
            {"id": id_activo},
        )

        registrar_movimiento(
            usuario=usuario,
            accion="Inició revisión de contenido",
            modulo="Maquinaria",
            referencia=id_activo,
            conn=conn,
        )


def finalizar_revision_contenido(id_activo, usuario):

    with engine.begin() as conn:

        activo = (
            conn.execute(
                text("""
                SELECT es_contenedor, estado_revision_contenido
                FROM maquinarias
                WHERE id_activo = :id
                FOR UPDATE
            """),
                {"id": id_activo},
            )
            .mappings()
            .first()
        )

        if not activo:
            raise ValueError("El activo no existe.")

        if not activo["es_contenedor"]:
            raise ValueError("El activo no está marcado como contenedor.")

        if activo["estado_revision_contenido"] != "EN_REVISION":
            raise ValueError(
                "La revisión solo puede finalizarse desde el estado EN_REVISION."
            )

        conn.execute(
            text("""
                UPDATE maquinarias
                SET
                    estado_revision_contenido = 'VERIFICADO',
                    fecha_revision_contenido = NOW(),
                    revisado_por = :usuario
                WHERE id_activo = :id
            """),
            {"id": id_activo, "usuario": usuario},
        )

        registrar_movimiento(
            usuario=usuario,
            accion="Finalizó revisión de contenido",
            modulo="Maquinaria",
            referencia=id_activo,
            conn=conn,
        )


def obtener_categorias_accesorios():

    sql = text("""
        SELECT
            id,
            codigo,
            nombre,
            descripcion
        FROM categorias_accesorios
        WHERE activo = 1
        ORDER BY
            CASE
                WHEN codigo = 'POR_CLASIFICAR' THEN 1
                ELSE 0
            END,
            nombre
    """)

    with engine.connect() as conn:

        resultado = conn.execute(sql).mappings().all()

        return [dict(categoria) for categoria in resultado]


def actualizar_categoria_accesorio(id_activo, categoria_accesorio_id, usuario):

    try:
        categoria_accesorio_id = int(categoria_accesorio_id)
    except (TypeError, ValueError):
        raise ValueError("La categoría seleccionada no es válida.")

    with engine.begin() as conn:

        accesorio = (
            conn.execute(
                text("""
                SELECT
                    m.id_activo,
                    m.categoria,
                    m.es_contenedor,
                    m.categoria_accesorio_id,
                    c.nombre AS categoria_anterior
                FROM maquinarias m
                LEFT JOIN categorias_accesorios c
                    ON c.id = m.categoria_accesorio_id
                WHERE m.id_activo = :id_activo
                FOR UPDATE
            """),
                {"id_activo": id_activo},
            )
            .mappings()
            .first()
        )

        if not accesorio:
            raise ValueError("El accesorio no existe.")

        if accesorio["es_contenedor"]:
            raise ValueError(
                "Una caja contenedora no puede clasificarse como accesorio."
            )

        if (accesorio["categoria"] or "").strip().upper() != "ACCESORIO":
            raise ValueError(
                "El activo seleccionado no está registrado como accesorio."
            )

        categoria_nueva = (
            conn.execute(
                text("""
                SELECT id, codigo, nombre
                FROM categorias_accesorios
                WHERE id = :categoria_id
                  AND activo = 1
                FOR UPDATE
            """),
                {"categoria_id": categoria_accesorio_id},
            )
            .mappings()
            .first()
        )

        if not categoria_nueva:
            raise ValueError("La categoría no existe o está desactivada.")

        if accesorio["categoria_accesorio_id"] == categoria_nueva["id"]:
            raise ValueError("El accesorio ya tiene seleccionada esa categoría.")

        conn.execute(
            text("""
                UPDATE maquinarias
                SET categoria_accesorio_id = :categoria_id
                WHERE id_activo = :id_activo
            """),
            {"categoria_id": categoria_nueva["id"], "id_activo": id_activo},
        )

        categoria_anterior = accesorio["categoria_anterior"] or "Sin categoría"

        registrar_movimiento(
            usuario=usuario,
            accion=(
                f"Cambió categoría técnica de "
                f"{categoria_anterior} a "
                f"{categoria_nueva['nombre']}"
            ),
            modulo="Accesorios",
            referencia=id_activo,
            conn=conn,
        )

        return dict(categoria_nueva)


def asignar_accesorio_maquinaria(
    id_accesorio, id_maquinaria, usuario, observaciones=None
):

    id_accesorio = (id_accesorio or "").strip().upper()
    id_maquinaria = (id_maquinaria or "").strip().upper()
    observaciones = (observaciones or "").strip() or None

    if not id_accesorio:
        raise ValueError("Debe seleccionar un accesorio.")

    if not id_maquinaria:
        raise ValueError("Debe seleccionar una maquinaria.")

    if id_accesorio == id_maquinaria:
        raise ValueError("Un accesorio no puede asignarse a sí mismo.")

    with engine.begin() as conn:

        filas = (
            conn.execute(
                text("""
                SELECT
                    id_activo,
                    categoria,
                    es_contenedor,
                    estado
                FROM maquinarias
                WHERE id_activo IN (
                    :id_accesorio,
                    :id_maquinaria
                )
                ORDER BY id_activo
                FOR UPDATE
            """),
                {"id_accesorio": id_accesorio, "id_maquinaria": id_maquinaria},
            )
            .mappings()
            .all()
        )

        activos = {fila["id_activo"]: fila for fila in filas}

        accesorio = activos.get(id_accesorio)
        maquinaria = activos.get(id_maquinaria)

        if not accesorio:
            raise ValueError("El accesorio no existe.")

        if not maquinaria:
            raise ValueError("La maquinaria seleccionada no existe.")

        if accesorio["es_contenedor"]:
            raise ValueError("Una caja contenedora no puede asignarse como accesorio.")

        if (accesorio["categoria"] or "").strip().upper() != "ACCESORIO":
            raise ValueError(
                "El activo seleccionado no está registrado como accesorio."
            )

        if (accesorio["estado"] or "").strip().upper() != "ACTIVO":
            raise ValueError("El accesorio debe estar activo para poder asignarse.")

        if maquinaria["es_contenedor"]:
            raise ValueError("El destino no puede ser una caja contenedora.")

        if (maquinaria["categoria"] or "").strip().upper() == "ACCESORIO":
            raise ValueError("Un accesorio no puede asignarse a otro accesorio.")

        if (maquinaria["estado"] or "").strip().upper() != "ACTIVO":
            raise ValueError("La maquinaria seleccionada no está activa.")

        asignacion_actual = (
            conn.execute(
                text("""
                SELECT
                    id,
                    id_maquinaria
                FROM asignaciones_accesorios
                WHERE id_accesorio = :id_accesorio
                  AND estado = 'ACTIVA'
                FOR UPDATE
            """),
                {"id_accesorio": id_accesorio},
            )
            .mappings()
            .first()
        )

        if asignacion_actual and asignacion_actual["id_maquinaria"] == id_maquinaria:
            raise ValueError(f"El accesorio ya está asignado a {id_maquinaria}.")

        maquinaria_anterior = None

        if asignacion_actual:

            maquinaria_anterior = asignacion_actual["id_maquinaria"]

            conn.execute(
                text("""
                    UPDATE asignaciones_accesorios
                    SET
                        estado = 'FINALIZADA',
                        fecha_fin = NOW(),
                        finalizado_por = :usuario
                    WHERE id = :asignacion_id
                """),
                {"usuario": usuario, "asignacion_id": asignacion_actual["id"]},
            )

        resultado = conn.execute(
            text("""
                INSERT INTO asignaciones_accesorios (
                    id_accesorio,
                    id_maquinaria,
                    estado,
                    asignado_por,
                    observaciones
                )
                VALUES (
                    :id_accesorio,
                    :id_maquinaria,
                    'ACTIVA',
                    :usuario,
                    :observaciones
                )
            """),
            {
                "id_accesorio": id_accesorio,
                "id_maquinaria": id_maquinaria,
                "usuario": usuario,
                "observaciones": observaciones,
            },
        )

        if maquinaria_anterior:

            accion = f"Cambió asignación de {maquinaria_anterior} " f"a {id_maquinaria}"

        else:

            accion = f"Asignó el accesorio a {id_maquinaria}"

        registrar_movimiento(
            usuario=usuario,
            accion=accion,
            modulo="Accesorios",
            referencia=id_accesorio,
            conn=conn,
        )

        return {
            "asignacion_id": resultado.lastrowid,
            "id_accesorio": id_accesorio,
            "id_maquinaria": id_maquinaria,
            "maquinaria_anterior": maquinaria_anterior,
        }


def liberar_accesorio_maquinaria(id_accesorio, usuario):

    id_accesorio = (id_accesorio or "").strip().upper()

    if not id_accesorio:
        raise ValueError("Debe seleccionar un accesorio.")

    with engine.begin() as conn:

        accesorio = (
            conn.execute(
                text("""
                SELECT id_activo
                FROM maquinarias
                WHERE id_activo = :id_accesorio
                FOR UPDATE
            """),
                {"id_accesorio": id_accesorio},
            )
            .mappings()
            .first()
        )

        if not accesorio:
            raise ValueError("El accesorio no existe.")

        asignacion = (
            conn.execute(
                text("""
                SELECT
                    id,
                    id_maquinaria
                FROM asignaciones_accesorios
                WHERE id_accesorio = :id_accesorio
                  AND estado = 'ACTIVA'
                FOR UPDATE
            """),
                {"id_accesorio": id_accesorio},
            )
            .mappings()
            .first()
        )

        if not asignacion:
            raise ValueError("El accesorio no tiene una asignación activa.")

        conn.execute(
            text("""
                UPDATE asignaciones_accesorios
                SET
                    estado = 'FINALIZADA',
                    fecha_fin = NOW(),
                    finalizado_por = :usuario
                WHERE id = :asignacion_id
            """),
            {"usuario": usuario, "asignacion_id": asignacion["id"]},
        )

        registrar_movimiento(
            usuario=usuario,
            accion=(f"Liberó el accesorio de " f"{asignacion['id_maquinaria']}"),
            modulo="Accesorios",
            referencia=id_accesorio,
            conn=conn,
        )

        return asignacion["id_maquinaria"]


def obtener_asignacion_activa_accesorio(id_accesorio):

    sql = text("""
        SELECT
            aa.id AS asignacion_id,
            aa.id_accesorio,
            aa.id_maquinaria,
            aa.fecha_asignacion,
            aa.asignado_por,
            aa.observaciones,

            ca.id AS categoria_accesorio_id,
            ca.codigo AS categoria_accesorio_codigo,
            ca.nombre AS categoria_accesorio_nombre,

            m.descripcion AS maquinaria_descripcion,
            m.marca AS maquinaria_marca,
            m.modelo AS maquinaria_modelo,
            m.numero_serie AS maquinaria_serie,
            m.ubicacion AS maquinaria_ubicacion

        FROM asignaciones_accesorios aa

        INNER JOIN maquinarias a
            ON a.id_activo = aa.id_accesorio

        LEFT JOIN categorias_accesorios ca
            ON ca.id = a.categoria_accesorio_id

        INNER JOIN maquinarias m
            ON m.id_activo = aa.id_maquinaria

        WHERE aa.id_accesorio = :id_accesorio
          AND aa.estado = 'ACTIVA'

        LIMIT 1
    """)

    with engine.connect() as conn:

        asignacion = (
            conn.execute(sql, {"id_accesorio": id_accesorio}).mappings().first()
        )

        return dict(asignacion) if asignacion else None


def obtener_accesorios_asignados_maquinaria(id_maquinaria):

    sql = text("""
        SELECT
            aa.id AS asignacion_id,
            aa.id_accesorio,
            aa.id_maquinaria,
            aa.fecha_asignacion,
            aa.asignado_por,
            aa.observaciones,

            a.descripcion AS accesorio_descripcion,
            a.marca AS accesorio_marca,
            a.modelo AS accesorio_modelo,
            a.numero_serie AS accesorio_serie,
            a.ubicacion AS accesorio_ubicacion,

            ca.id AS categoria_accesorio_id,
            ca.codigo AS categoria_accesorio_codigo,
            ca.nombre AS categoria_accesorio_nombre

        FROM asignaciones_accesorios aa

        INNER JOIN maquinarias a
            ON a.id_activo = aa.id_accesorio

        LEFT JOIN categorias_accesorios ca
            ON ca.id = a.categoria_accesorio_id

        WHERE aa.id_maquinaria = :id_maquinaria
          AND aa.estado = 'ACTIVA'

        ORDER BY
            ca.nombre,
            a.descripcion,
            a.id_activo
    """)

    with engine.connect() as conn:

        resultado = conn.execute(sql, {"id_maquinaria": id_maquinaria}).mappings().all()

        return [dict(accesorio) for accesorio in resultado]


def obtener_historial_asignaciones_accesorio(id_accesorio):

    sql = text("""
        SELECT
            aa.id AS asignacion_id,
            aa.id_accesorio,
            aa.id_maquinaria,
            aa.estado,
            aa.fecha_asignacion,
            aa.fecha_fin,
            aa.asignado_por,
            aa.finalizado_por,
            aa.observaciones,

            m.descripcion AS maquinaria_descripcion,
            m.marca AS maquinaria_marca,
            m.modelo AS maquinaria_modelo,
            m.ubicacion AS maquinaria_ubicacion

        FROM asignaciones_accesorios aa

        INNER JOIN maquinarias m
            ON m.id_activo = aa.id_maquinaria

        WHERE aa.id_accesorio = :id_accesorio

        ORDER BY aa.fecha_asignacion DESC
    """)

    with engine.connect() as conn:

        resultado = conn.execute(sql, {"id_accesorio": id_accesorio}).mappings().all()

        return [dict(asignacion) for asignacion in resultado]


def buscar_maquinarias_asignables(texto, id_accesorio=None):

    texto = (texto or "").strip()
    id_accesorio = (id_accesorio or "").strip().upper()

    sql = text("""
        SELECT
            id_activo,
            descripcion,
            categoria,
            marca,
            modelo,
            numero_serie,
            ubicacion
        FROM maquinarias
        WHERE estado = 'ACTIVO'
        AND COALESCE(es_contenedor, 0) = 0
        AND UPPER(
                TRIM(
                    COALESCE(categoria, '')
                )
            ) <> 'ACCESORIO'
        AND id_activo <> :id_accesorio
        AND (
                id_activo LIKE :texto
                OR descripcion LIKE :texto
                OR marca LIKE :texto
                OR modelo LIKE :texto
                OR numero_serie LIKE :texto
                OR ubicacion LIKE :texto
                )
        
        ORDER BY id_activo
        LIMIT 20
    """)

    with engine.connect() as conn:

        resultado = (
            conn.execute(sql, {"texto": f"%{texto}%", "id_accesorio": id_accesorio})
            .mappings()
            .all()
        )

        return [dict(maquinaria) for maquinaria in resultado]


def crear_categoria_y_clasificar_accesorio(id_activo, nombre, descripcion, usuario):

    id_activo = (id_activo or "").strip().upper()
    nombre = (nombre or "").strip()
    descripcion = (descripcion or "").strip() or None

    if not nombre:
        raise ValueError("Debe escribir el nombre de la nueva categoría.")

    if len(nombre) > 100:
        raise ValueError("El nombre de la categoría es demasiado largo.")

    if descripcion and len(descripcion) > 255:
        raise ValueError("La descripción de la categoría es demasiado larga.")

    nombre_normalizado = unicodedata.normalize("NFKD", nombre)

    codigo = nombre_normalizado.encode("ascii", "ignore").decode("ascii")

    codigo = re.sub(r"[^A-Za-z0-9]+", "_", codigo).strip("_").upper()

    codigo = codigo[:50].rstrip("_")

    if not codigo:
        raise ValueError("No fue posible generar el código de la categoría.")

    with engine.begin() as conn:

        accesorio = (
            conn.execute(
                text("""
                SELECT
                    id_activo,
                    categoria,
                    es_contenedor
                FROM maquinarias
                WHERE id_activo = :id_activo
                FOR UPDATE
            """),
                {"id_activo": id_activo},
            )
            .mappings()
            .first()
        )

        if not accesorio:
            raise ValueError("El accesorio no existe.")

        if accesorio["es_contenedor"]:
            raise ValueError(
                "Una caja contenedora no puede clasificarse como accesorio."
            )

        if (accesorio["categoria"] or "").strip().upper() != "ACCESORIO":
            raise ValueError("El activo no está registrado como accesorio.")

        categoria_existente = (
            conn.execute(
                text("""
                SELECT id, nombre, activo
                FROM categorias_accesorios
                WHERE codigo = :codigo
                OR nombre = :nombre
                FOR UPDATE
            """),
                {"codigo": codigo, "nombre": nombre},
            )
            .mappings()
            .first()
        )

        if categoria_existente:

            if categoria_existente["activo"]:
                raise ValueError(
                    "Esa categoría ya existe. " "Selecciónela en la lista."
                )

            raise ValueError("Esa categoría existe, pero está desactivada.")

        resultado = conn.execute(
            text("""
                INSERT INTO categorias_accesorios (
                    codigo,
                    nombre,
                    descripcion,
                    activo
                )
                VALUES (
                    :codigo,
                    :nombre,
                    :descripcion,
                    1
                )
            """),
            {"codigo": codigo, "nombre": nombre, "descripcion": descripcion},
        )

        categoria_id = resultado.lastrowid

        conn.execute(
            text("""
                UPDATE maquinarias
                SET categoria_accesorio_id = :categoria_id
                WHERE id_activo = :id_activo
            """),
            {"categoria_id": categoria_id, "id_activo": id_activo},
        )

        registrar_movimiento(
            usuario=usuario,
            accion=(f"Creó la categoría {nombre} " f"y clasificó el accesorio"),
            modulo="Accesorios",
            referencia=id_activo,
            conn=conn,
        )

        return {"id": categoria_id, "codigo": codigo, "nombre": nombre}


def reabrir_revision_contenido(id_activo, usuario):

    with engine.begin() as conn:

        activo = (
            conn.execute(
                text("""
                SELECT
                    es_contenedor,
                    estado_revision_contenido
                FROM maquinarias
                WHERE id_activo = :id_activo
                FOR UPDATE
            """),
                {"id_activo": id_activo},
            )
            .mappings()
            .first()
        )

        if not activo:
            raise ValueError("El activo no existe.")

        if not activo["es_contenedor"]:
            raise ValueError("El activo no está marcado como contenedor.")

        if activo["estado_revision_contenido"] != "VERIFICADO":
            raise ValueError(
                "Solo puede iniciarse una nueva revisión " "desde el estado VERIFICADO."
            )

        conn.execute(
            text("""
                UPDATE maquinarias
                SET estado_revision_contenido = 'EN_REVISION'
                WHERE id_activo = :id_activo
            """),
            {"id_activo": id_activo},
        )

        registrar_movimiento(
            usuario=usuario,
            accion="Inició una nueva revisión de contenido",
            modulo="Maquinaria",
            referencia=id_activo,
            conn=conn,
        )
