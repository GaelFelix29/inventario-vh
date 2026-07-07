import os
from datetime import datetime

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

        # Verificamos que exista conexión
        conn.execute(text("SELECT 1"))
        
        tablas = conn.execute(text("SHOW TABLES")).fetchall()

        print(tablas)

        with open(
            archivo,
            "w",
            encoding="utf-8") as f:

            f.write("-- ======================================\n")
            f.write("-- RESPALDO VITAL HEALTH\n")
            f.write(f"-- Fecha: {fecha}\n")
            f.write("-- Generado automáticamente\n")
            f.write("-- ======================================\n\n")

            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

            f.write("-- Aquí comenzará el respaldo de las tablas.\n")

            f.write("\nSET FOREIGN_KEY_CHECKS=1;\n")

    return os.path.basename(archivo)


if __name__ == "__main__":

    print(crear_respaldo())