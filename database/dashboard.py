from database.maquinarias import obtener_maquinarias
from database.aduanas import obtener_aduanas
from sqlalchemy import text
from database.conexion import engine

def obtener_kpis_dashboard():

    maquinarias = obtener_maquinarias()

    aduanas = obtener_aduanas()

    # ==========================
    # Expedientes
    # ==========================

    completos = 0
    pendientes = 0

    for _, fila in aduanas.iterrows():

        doc = str(
            fila["documentacion_completa"]
        ).strip().upper()

        if doc == "SI":

            completos += 1

        else:

            pendientes += 1

    # ==========================
    # KPIs
    # ==========================

    return {

        "total_activos": len(maquinarias),

        "importados": len(

            aduanas[
                ~aduanas["origen"]
                .fillna("")
                .str.upper()
                .isin(["NACIONAL", "MEXICO"])
            ]

        ),

        "expedientes_completos": completos,

        "expedientes_pendientes": pendientes

    }


def obtener_actividad_dashboard():

    sql = text("""

        SELECT

            usuario,

            accion,

            modulo,

            referencia,

            fecha

        FROM auditoria

        ORDER BY fecha DESC

        LIMIT 5

    """)

    with engine.begin() as conn:

        actividad = conn.execute(sql).mappings().all()

    return actividad