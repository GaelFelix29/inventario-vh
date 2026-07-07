from datetime import datetime
import os

from sqlalchemy import text

from database.conexion import engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BACKUPS = os.path.join(BASE_DIR, "backups")

os.makedirs(BACKUPS, exist_ok=True)


def crear_respaldo():

    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    archivo = os.path.join(
        BACKUPS,
        f"vitalhealth_{fecha}.sql"
    )

    with engine.begin() as conn:

        # Verificar conexión
        conn.execute(text("SELECT 1"))

        # Obtener todas las tablas
        tablas = conn.execute(
            text("SHOW TABLES")
        ).fetchall()

        with open(archivo, "w", encoding="utf-8") as f:

            # Encabezado
            f.write("-- ======================================\n")
            f.write("-- RESPALDO VITAL HEALTH\n")
            f.write(f"-- Fecha: {fecha}\n")
            f.write("-- Generado automáticamente\n")
            f.write("-- ======================================\n\n")

            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

            # Recorrer todas las tablas
            for tabla in tablas:

                nombre = tabla[0]

                print(f"Respaldando tabla: {nombre}")

                # Obtener CREATE TABLE
                create = conn.execute(
                    text(f"SHOW CREATE TABLE `{nombre}`")
                ).fetchone()

                f.write("-- ======================================\n")
                f.write(f"-- TABLA: {nombre}\n")
                f.write("-- ======================================\n\n")

                f.write(f"DROP TABLE IF EXISTS `{nombre}`;\n\n")

                f.write(create[1])
                f.write(";\n\n")

            f.write("\nSET FOREIGN_KEY_CHECKS=1;\n")

    return os.path.basename(archivo)