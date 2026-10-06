"""Agrega los datos originales del Excel a cada semana del plan."""
from sqlalchemy import text
from database.conexion import engine

with engine.begin() as conn:
    columnas = {
        fila["COLUMN_NAME"] for fila in conn.execute(text("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'mantenimientos_programados'
        """)).mappings()
    }
    if "color_excel" not in columnas:
        conn.execute(text("""ALTER TABLE mantenimientos_programados
                            ADD COLUMN color_excel CHAR(6) NULL AFTER estado"""))
    if "estado_excel" not in columnas:
        conn.execute(text("""ALTER TABLE mantenimientos_programados
                            ADD COLUMN estado_excel VARCHAR(30) NULL AFTER color_excel"""))

print("Colores originales del plan habilitados correctamente.")
