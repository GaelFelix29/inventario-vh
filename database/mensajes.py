from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database.conexion import engine


LIMITE_CONVERSACIONES = 30
LIMITE_MENSAJES = 50


def listar_usuarios_mensajeria(usuario_actual_id):
    sql = text("""
        SELECT id, nombre, usuario, rol, avatar
        FROM usuarios
        WHERE activo = 1 AND id <> :usuario_actual_id
        ORDER BY nombre
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "usuario_actual_id": usuario_actual_id,
        }).mappings().all()


def obtener_o_crear_conversacion(usuario_actual_id, destinatario_id):
    if usuario_actual_id == destinatario_id:
        raise ValueError("No puedes iniciar una conversación contigo mismo.")

    usuario_uno, usuario_dos = sorted((usuario_actual_id, destinatario_id))
    with engine.begin() as conn:
        destinatario = conn.execute(text("""
            SELECT id FROM usuarios WHERE id = :id AND activo = 1
        """), {"id": destinatario_id}).scalar()
        if not destinatario:
            raise ValueError("El usuario seleccionado no está disponible.")

        conn.execute(text("""
            INSERT IGNORE INTO conversaciones
                (usuario_uno_id, usuario_dos_id)
            VALUES (:usuario_uno, :usuario_dos)
        """), {
            "usuario_uno": usuario_uno,
            "usuario_dos": usuario_dos,
        })
        return conn.execute(text("""
            SELECT id FROM conversaciones
            WHERE usuario_uno_id = :usuario_uno
              AND usuario_dos_id = :usuario_dos
        """), {
            "usuario_uno": usuario_uno,
            "usuario_dos": usuario_dos,
        }).scalar_one()


def obtener_conversacion(conversacion_id, usuario_id):
    sql = text("""
        SELECT
            c.id,
            CASE WHEN c.usuario_uno_id = :usuario_id
                 THEN u2.id ELSE u1.id END AS contacto_id,
            CASE WHEN c.usuario_uno_id = :usuario_id
                 THEN u2.nombre ELSE u1.nombre END AS contacto_nombre,
            CASE WHEN c.usuario_uno_id = :usuario_id
                 THEN u2.rol ELSE u1.rol END AS contacto_rol,
            CASE WHEN c.usuario_uno_id = :usuario_id
                 THEN u2.avatar ELSE u1.avatar END AS contacto_avatar
        FROM conversaciones c
        JOIN usuarios u1 ON u1.id = c.usuario_uno_id
        JOIN usuarios u2 ON u2.id = c.usuario_dos_id
        WHERE c.id = :conversacion_id
          AND (:usuario_id = c.usuario_uno_id
               OR :usuario_id = c.usuario_dos_id)
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "conversacion_id": conversacion_id,
            "usuario_id": usuario_id,
        }).mappings().first()


def listar_conversaciones(usuario_id, limite=LIMITE_CONVERSACIONES):
    sql = text("""
        SELECT
            c.id,
            c.ultimo_mensaje_en,
            CASE WHEN c.usuario_uno_id = :usuario_id
                 THEN u2.nombre ELSE u1.nombre END AS contacto_nombre,
            CASE WHEN c.usuario_uno_id = :usuario_id
                 THEN u2.rol ELSE u1.rol END AS contacto_rol,
            (
                SELECT m.contenido FROM mensajes m
                WHERE m.conversacion_id = c.id
                ORDER BY m.id DESC LIMIT 1
            ) AS ultimo_mensaje,
            (
                SELECT COUNT(*) FROM mensajes m
                WHERE m.conversacion_id = c.id
                  AND m.remitente_id <> :usuario_id
                  AND m.leido_en IS NULL
            ) AS no_leidos
        FROM conversaciones c
        JOIN usuarios u1 ON u1.id = c.usuario_uno_id
        JOIN usuarios u2 ON u2.id = c.usuario_dos_id
        WHERE c.usuario_uno_id = :usuario_id
           OR c.usuario_dos_id = :usuario_id
        ORDER BY c.ultimo_mensaje_en DESC
        LIMIT :limite
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "usuario_id": usuario_id,
            "limite": limite,
        }).mappings().all()


def listar_mensajes(conversacion_id, usuario_id, limite=LIMITE_MENSAJES):
    if not obtener_conversacion(conversacion_id, usuario_id):
        return None
    sql = text("""
        SELECT m.id, m.remitente_id, m.contenido, m.enviado_en,
               u.nombre AS remitente_nombre
        FROM mensajes m
        JOIN usuarios u ON u.id = m.remitente_id
        WHERE m.conversacion_id = :conversacion_id
        ORDER BY m.id DESC
        LIMIT :limite
    """)
    with engine.connect() as conn:
        filas = conn.execute(sql, {
            "conversacion_id": conversacion_id,
            "limite": limite,
        }).mappings().all()
        return list(reversed(filas))


def enviar_mensaje(conversacion_id, remitente_id, contenido):
    contenido = (contenido or "").strip()
    if not contenido:
        raise ValueError("Escribe un mensaje antes de enviarlo.")
    if len(contenido) > 2000:
        raise ValueError("El mensaje no puede superar 2000 caracteres.")

    with engine.begin() as conn:
        participante = conn.execute(text("""
            SELECT id FROM conversaciones
            WHERE id = :conversacion_id
              AND (:remitente_id = usuario_uno_id
                   OR :remitente_id = usuario_dos_id)
            FOR UPDATE
        """), {
            "conversacion_id": conversacion_id,
            "remitente_id": remitente_id,
        }).scalar()
        if not participante:
            raise PermissionError("No tienes acceso a esta conversación.")

        resultado = conn.execute(text("""
            INSERT INTO mensajes (conversacion_id, remitente_id, contenido)
            VALUES (:conversacion_id, :remitente_id, :contenido)
        """), {
            "conversacion_id": conversacion_id,
            "remitente_id": remitente_id,
            "contenido": contenido,
        })
        conn.execute(text("""
            UPDATE conversaciones SET ultimo_mensaje_en = CURRENT_TIMESTAMP
            WHERE id = :conversacion_id
        """), {"conversacion_id": conversacion_id})
        return resultado.lastrowid


def obtener_mensaje(mensaje_id, usuario_id):
    sql = text("""
        SELECT m.id, m.remitente_id, m.contenido, m.enviado_en,
               u.nombre AS remitente_nombre
        FROM mensajes m
        JOIN conversaciones c ON c.id = m.conversacion_id
        JOIN usuarios u ON u.id = m.remitente_id
        WHERE m.id = :mensaje_id
          AND (:usuario_id = c.usuario_uno_id
               OR :usuario_id = c.usuario_dos_id)
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "mensaje_id": mensaje_id,
            "usuario_id": usuario_id,
        }).mappings().first()


def listar_mensajes_nuevos(conversacion_id, usuario_id, despues_de):
    """Devuelve solo mensajes posteriores al último visible y marca recibidos."""
    sql = text("""
        SELECT m.id, m.remitente_id, m.contenido, m.enviado_en,
               u.nombre AS remitente_nombre
        FROM mensajes m
        JOIN conversaciones c ON c.id = m.conversacion_id
        JOIN usuarios u ON u.id = m.remitente_id
        WHERE m.conversacion_id = :conversacion_id
          AND m.id > :despues_de
          AND (:usuario_id = c.usuario_uno_id
               OR :usuario_id = c.usuario_dos_id)
        ORDER BY m.id
        LIMIT 50
    """)
    with engine.begin() as conn:
        filas = conn.execute(sql, {
            "conversacion_id": conversacion_id,
            "usuario_id": usuario_id,
            "despues_de": despues_de,
        }).mappings().all()
        if filas:
            conn.execute(text("""
                UPDATE mensajes m
                JOIN conversaciones c ON c.id = m.conversacion_id
                SET m.leido_en = CURRENT_TIMESTAMP
                WHERE m.conversacion_id = :conversacion_id
                  AND m.id > :despues_de
                  AND m.remitente_id <> :usuario_id
                  AND m.leido_en IS NULL
                  AND (:usuario_id = c.usuario_uno_id
                       OR :usuario_id = c.usuario_dos_id)
            """), {
                "conversacion_id": conversacion_id,
                "usuario_id": usuario_id,
                "despues_de": despues_de,
            })
        return filas


def marcar_como_leidos(conversacion_id, usuario_id):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE mensajes m
            JOIN conversaciones c ON c.id = m.conversacion_id
            SET m.leido_en = CURRENT_TIMESTAMP
            WHERE m.conversacion_id = :conversacion_id
              AND m.remitente_id <> :usuario_id
              AND m.leido_en IS NULL
              AND (:usuario_id = c.usuario_uno_id
                   OR :usuario_id = c.usuario_dos_id)
        """), {
            "conversacion_id": conversacion_id,
            "usuario_id": usuario_id,
        })


def contar_no_leidos(usuario_id):
    sql = text("""
        SELECT COUNT(*)
        FROM mensajes m
        JOIN conversaciones c ON c.id = m.conversacion_id
        WHERE m.remitente_id <> :usuario_id
          AND m.leido_en IS NULL
          AND (:usuario_id = c.usuario_uno_id
               OR :usuario_id = c.usuario_dos_id)
    """)
    try:
        with engine.connect() as conn:
            return int(conn.execute(sql, {"usuario_id": usuario_id}).scalar() or 0)
    except SQLAlchemyError:
        return 0
