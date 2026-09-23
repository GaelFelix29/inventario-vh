from sqlalchemy import text

from database.conexion import engine


def crear_tablas_mensajes():
    """Crea la mensajería privada y sus índices si todavía no existen."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversaciones (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                usuario_uno_id INT NOT NULL,
                usuario_dos_id INT NOT NULL,
                creada_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ultimo_mensaje_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uq_conversacion_usuarios
                    (usuario_uno_id, usuario_dos_id),
                KEY ix_conversaciones_ultimo (ultimo_mensaje_en),
                CONSTRAINT fk_conversacion_usuario_uno
                    FOREIGN KEY (usuario_uno_id) REFERENCES usuarios(id),
                CONSTRAINT fk_conversacion_usuario_dos
                    FOREIGN KEY (usuario_dos_id) REFERENCES usuarios(id),
                CONSTRAINT chk_conversacion_orden
                    CHECK (usuario_uno_id < usuario_dos_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                conversacion_id BIGINT UNSIGNED NOT NULL,
                remitente_id INT NOT NULL,
                contenido VARCHAR(2000) NOT NULL,
                enviado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                leido_en DATETIME NULL,
                PRIMARY KEY (id),
                KEY ix_mensajes_conversacion (conversacion_id, id),
                KEY ix_mensajes_no_leidos
                    (conversacion_id, remitente_id, leido_en),
                CONSTRAINT fk_mensaje_conversacion
                    FOREIGN KEY (conversacion_id)
                    REFERENCES conversaciones(id) ON DELETE CASCADE,
                CONSTRAINT fk_mensaje_remitente
                    FOREIGN KEY (remitente_id) REFERENCES usuarios(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        print("Tablas de mensajes verificadas correctamente.")


if __name__ == "__main__":
    crear_tablas_mensajes()
