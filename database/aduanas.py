import pandas as pd
from sqlalchemy import text
from database.conexion import engine


def obtener_aduanas():

    sql = """

        SELECT *

        FROM aduanas

    """

    return pd.read_sql(sql, engine)


def crear_registro_aduana_vacio(id_activo):

    sql = text("""

        INSERT INTO aduanas(

            id_activo

        )

        VALUES(

            :id_activo

        )

    """)

    with engine.begin() as conn:

        conn.execute(sql, {

            "id_activo": id_activo

        })

def guardar_aduana(
    id_activo,
    factura,
    pedimento,
    entrada_mtz,
    id_imp,
    inbond,
    origen,
    fecha_importacion,
    kg_bruto,
    total_bultos,
    documentacion_completa
):

    if fecha_importacion == "":
        fecha_importacion = None

    if kg_bruto == "":
        kg_bruto = None

    if total_bultos == "":
        total_bultos = None

    with engine.begin() as conn:

        existe = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM aduanas
                WHERE id_activo=:id
            """),
            {"id": id_activo}
        ).scalar()

        if existe:

            conn.execute(text("""

                UPDATE aduanas
                SET

                    factura=:factura,
                    pedimento=:pedimento,
                    entrada_mtz=:entrada_mtz,
                    id_imp=:id_imp,
                    inbond=:inbond,
                    origen=:origen,
                    fecha_importacion=:fecha_importacion,
                    kg_bruto=:kg_bruto,
                    total_bultos=:total_bultos,
                    documentacion_completa=:documentacion_completa

                WHERE id_activo=:id_activo

            """),{

                "id_activo": id_activo,
                "factura": factura,
                "pedimento": pedimento,
                "entrada_mtz": entrada_mtz,
                "id_imp": id_imp,
                "inbond": inbond,
                "origen": origen,
                "fecha_importacion": fecha_importacion,
                "kg_bruto": kg_bruto,
                "total_bultos": total_bultos,
                "documentacion_completa": documentacion_completa

            })

        else:

            conn.execute(text("""

                INSERT INTO aduanas
                (

                    id_activo,
                    factura,
                    pedimento,
                    entrada_mtz,
                    id_imp,
                    inbond,
                    origen,
                    fecha_importacion,
                    kg_bruto,
                    total_bultos,
                    documentacion_completa

                )

                VALUES
                (

                    :id_activo,
                    :factura,
                    :pedimento,
                    :entrada_mtz,
                    :id_imp,
                    :inbond,
                    :origen,
                    :fecha_importacion,
                    :kg_bruto,
                    :total_bultos,
                    :documentacion_completa

                )

            """),{

                "id_activo": id_activo,
                "factura": factura,
                "pedimento": pedimento,
                "entrada_mtz": entrada_mtz,
                "id_imp": id_imp,
                "inbond": inbond,
                "origen": origen,
                "fecha_importacion": fecha_importacion,
                "kg_bruto": kg_bruto,
                "total_bultos": total_bultos,
                "documentacion_completa": documentacion_completa

            })



def obtener_aduana(id_activo):

    sql = text("""
        SELECT *
        FROM aduanas
        WHERE id_activo = :id
        LIMIT 1
    """)

    with engine.begin() as conn:

        fila = conn.execute(
            sql,
            {"id": id_activo}
        ).mappings().first()

    return fila

def actualizar_aduana(
    id_activo,
    factura,
    pedimento,
    entrada_mtz,
    id_imp,
    inbond,
    origen,
    fecha_importacion,
    kg_bruto,
    total_bultos,
    documentacion_completa
):

    if fecha_importacion == "":
        fecha_importacion = None

    if kg_bruto == "":
        kg_bruto = None

    if total_bultos == "":
        total_bultos = None

    sql = text("""

        UPDATE aduanas

        SET

            factura=:factura,
            pedimento=:pedimento,
            entrada_mtz=:entrada_mtz,
            id_imp=:id_imp,
            inbond=:inbond,
            origen=:origen,
            fecha_importacion=:fecha_importacion,
            kg_bruto=:kg_bruto,
            total_bultos=:total_bultos,
            documentacion_completa=:documentacion_completa

        WHERE id_activo=:id_activo

    """)

    with engine.begin() as conn:

        conn.execute(sql, {

            "id_activo": id_activo,
            "factura": factura,
            "pedimento": pedimento,
            "entrada_mtz": entrada_mtz,
            "id_imp": id_imp,
            "inbond": inbond,
            "origen": origen,
            "fecha_importacion": fecha_importacion,
            "kg_bruto": kg_bruto,
            "total_bultos": total_bultos,
            "documentacion_completa": documentacion_completa

        })

def estado_expediente_aduanal(aduana):

    if not aduana:

        campos = [
            ("factura", "Factura"),
            ("pedimento", "Pedimento"),
            ("entrada_mtz", "Entrada MTZ"),
            ("id_imp", "ID IMP"),
            ("inbond", "Inbond"),
            ("origen", "Origen"),
            ("fecha_importacion", "Fecha de Importación"),
            ("kg_bruto", "Kg Bruto"),
            ("total_bultos", "Total Bultos"),
            ("documentacion_completa", "Documentación Completa")
        ]

        return {
            "porcentaje": 0,
            "estado": "Sin expediente",
            "color": "danger",
            "completos": 0,
            "pendientes": len(campos),
            "total": len(campos),
            "faltantes": [c[1] for c in campos]
        }

    origen = str(aduana.get("origen", "")).strip().upper()

    # ============================================
    # MAQUINARIA NACIONAL
    # ============================================

    if origen == "NACIONAL":

        campos = [

            ("factura", "Factura"),

            ("origen", "Origen"),

            ("documentacion_completa", "Documentación Completa")

        ]

    # ============================================
    # MAQUINARIA IMPORTADA
    # ============================================

    else:

        campos = [

            ("factura", "Factura"),

            ("pedimento", "Pedimento"),

            ("entrada_mtz", "Entrada MTZ"),

            ("id_imp", "ID IMP"),

            ("inbond", "Inbond"),

            ("origen", "Origen"),

            ("fecha_importacion", "Fecha de Importación"),

            ("kg_bruto", "Kg Bruto"),

            ("total_bultos", "Total Bultos"),

            ("documentacion_completa", "Documentación Completa")

        ]

    completos = 0
    faltantes = []

    for campo, nombre in campos:

        valor = aduana.get(campo)

        texto = "" if valor is None else str(valor).strip().upper()

        # ===========================
        # DOCUMENTACIÓN COMPLETA
        # ===========================

        if campo == "documentacion_completa":

            if texto == "SI":
                completos += 1
            else:
                faltantes.append(nombre)

        # ===========================
        # FACTURA
        # ===========================

        elif campo == "factura":

            # Para nosotros "NA" significa "No aplica",
            # por lo tanto sí cuenta como válido.

            if texto != "":
                completos += 1
            else:
                faltantes.append(nombre)

        # ===========================
        # RESTO DE CAMPOS
        # ===========================

        else:

            if texto != "":
                completos += 1
            else:
                faltantes.append(nombre)

    pendientes = len(campos) - completos

    porcentaje = round((completos / len(campos)) * 100)

    if porcentaje == 100:

        estado = "Completo"
        color = "success"

    elif porcentaje == 0:

        estado = "Sin expediente"
        color = "danger"

    else:

        estado = "Incompleto"
        color = "warning"

    return {

        "porcentaje": porcentaje,

        "estado": estado,

        "color": color,

        "completos": completos,

        "pendientes": pendientes,

        "total": len(campos),

        "faltantes": faltantes

    }

def obtener_aduanas_mobile_filtrado(
    q="",
    origen="",
    tipo="",
    limite=20,
    offset=0
):

    sql = """
    SELECT
        a.*,
        m.descripcion,
        m.estado
    FROM aduanas a
    LEFT JOIN maquinarias m
        ON a.id_activo = m.id_activo
    WHERE 1=1
    """

    params = {}

    # ==========================================
    # BUSCADOR
    # ==========================================

    if q:

        sql += """
        AND (
            a.id_activo LIKE :q
            OR m.descripcion LIKE :q
            OR a.factura LIKE :q
            OR a.pedimento LIKE :q
            OR a.origen LIKE :q
        )
        """

        params["q"] = f"%{q}%"

    # ==========================================
    # FILTRO ORIGEN
    # ==========================================

    if origen:

        sql += """
        AND a.origen = :origen
        """

        params["origen"] = origen

    # ==========================================
    # FILTRO TIPO
    # ==========================================

    if tipo:

        if tipo == "Importado":

            sql += """
            AND UPPER(a.origen) <> 'NACIONAL'
            """

        elif tipo == "Nacional":

            sql += """
            AND UPPER(a.origen) = 'NACIONAL'
            """

    # ==========================================
    # ORDEN Y PAGINACIÓN
    # ==========================================

    sql += """

        ORDER BY a.id_activo

        LIMIT :limite OFFSET :offset

    """

    params["limite"] = limite
    params["offset"] = offset

    return pd.read_sql(
        text(sql),
        engine,
        params=params
    )

def obtener_origenes():

    sql = text("""

        SELECT DISTINCT origen

        FROM aduanas

        WHERE origen IS NOT NULL
        AND TRIM(origen) <> ''

        ORDER BY origen

    """)

    with engine.connect() as conn:

        return conn.execute(sql).scalars().all()