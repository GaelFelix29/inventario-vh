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

        tablas = conn.execute(
            text("SHOW TABLES")
        ).fetchall()

        with open(
            archivo,
            "w",
            encoding="utf-8"
        ) as sql:

            sql.write("-- ======================================\n")
            sql.write("-- RESPALDO VITAL HEALTH\n")
            sql.write(f"-- Fecha: {fecha}\n")
            sql.write("-- ======================================\n\n")

    return archivo