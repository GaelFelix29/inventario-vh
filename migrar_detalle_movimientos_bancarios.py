from sqlalchemy import text

from database.conexion import engine


SENTENCIAS = [
    """CREATE TABLE IF NOT EXISTS movimiento_observaciones (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        movimiento_id BIGINT NOT NULL,
        observacion TEXT NOT NULL,
        usuario_id INT NOT NULL,
        creada_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_observacion_movimiento FOREIGN KEY (movimiento_id)
            REFERENCES movimientos_bancarios(id) ON DELETE CASCADE,
        CONSTRAINT fk_observacion_usuario FOREIGN KEY (usuario_id)
            REFERENCES usuarios(id),
        KEY ix_observacion_movimiento (movimiento_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS movimiento_archivos (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        movimiento_id BIGINT NOT NULL,
        nombre_original VARCHAR(255) NOT NULL,
        ruta_storage VARCHAR(600) NOT NULL,
        url VARCHAR(1000) NULL,
        tipo_mime VARCHAR(150) NULL,
        tamano_bytes BIGINT NOT NULL,
        usuario_id INT NOT NULL,
        creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_archivo_movimiento FOREIGN KEY (movimiento_id)
            REFERENCES movimientos_bancarios(id) ON DELETE CASCADE,
        CONSTRAINT fk_archivo_usuario FOREIGN KEY (usuario_id)
            REFERENCES usuarios(id),
        KEY ix_archivo_movimiento (movimiento_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

with engine.begin() as conn:
    for sentencia in SENTENCIAS:
        conn.execute(text(sentencia))

print("Tablas de observaciones y archivos financieros verificadas correctamente.")
