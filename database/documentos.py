import os
from sqlalchemy import text
from database.conexion import engine

# ==========================================
# RUTA ABSOLUTA DE DOCUMENTOS
# ==========================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUTA_DOCUMENTOS = os.path.join(
    BASE_DIR,
    "static",
    "documentos"
)

# ==========================================
# CREAR CARPETA DEL ACTIVO
# ==========================================

def crear_carpeta_activo(id_activo):

    carpeta = os.path.join(
        RUTA_DOCUMENTOS,
        id_activo
    )

    os.makedirs(carpeta, exist_ok=True)

    return carpeta


# ==========================================
# GUARDAR DOCUMENTO EN BD
# ==========================================

def guardar_documento_bd(
    id_activo,
    nombre_original,
    nombre_archivo,
    tipo,
    url,
    public_id,
    usuario
):

    sql = text("""

        INSERT INTO documentos_maquinaria(

            id_activo,
            nombre_original,
            nombre_archivo,
            tipo,
            url,
            public_id,
            subido_por

        )

        VALUES(

            :id_activo,
            :nombre_original,
            :nombre_archivo,
            :tipo,
            :url,
            :public_id,
            :usuario

        )

    """)

    with engine.begin() as conn:

        conn.execute(

            sql,

            {
                "id_activo": id_activo,
                "nombre_original": nombre_original,
                "nombre_archivo": nombre_archivo,
                "tipo": tipo,
                "url": url,
                "public_id": public_id,
                "usuario": usuario
            }

        )


# ==========================================
# LISTAR DOCUMENTOS
# ==========================================

def listar_documentos(id_activo):

    sql = text("""

        SELECT *

        FROM documentos_maquinaria

        WHERE id_activo = :id

        ORDER BY fecha_subida DESC

    """)

    with engine.connect() as conn:

        return conn.execute(

            sql,

            {"id": id_activo}

        ).mappings().all()


# ==========================================
# ELIMINAR DOCUMENTO
# ==========================================

def eliminar_documento(id_documento):

    sql = text("""

        SELECT *

        FROM documentos_maquinaria

        WHERE id=:id

    """)

    with engine.begin() as conn:

        doc = conn.execute(

            sql,

            {"id": id_documento}

        ).mappings().first()

        if not doc:
            return None

        sql = text("""

            DELETE

            FROM documentos_maquinaria

            WHERE id=:id

        """)

        conn.execute(

            sql,

            {"id": id_documento}

        )

    return doc