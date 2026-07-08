from datetime import datetime
import os

from sqlalchemy import text

from database.conexion import engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BACKUPS = os.path.join(BASE_DIR, "backups")

os.makedirs(BACKUPS, exist_ok=True)

from decimal import Decimal
from datetime import date, datetime


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

        with open(
            archivo,
            "w",
            encoding="utf-8"
        ) as f:

            # =====================================
            # ENCABEZADO
            # =====================================

            f.write("-- ======================================\n")
            f.write("-- RESPALDO VITAL HEALTH\n")
            f.write(f"-- Fecha: {fecha}\n")
            f.write("-- Generado automáticamente\n")
            f.write("-- ======================================\n\n")

            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

            # =====================================
            # RECORRER TABLAS
            # =====================================

            for tabla in tablas:

                nombre = tabla[0]

                print(f"Respaldando tabla: {nombre}")

                # -----------------------------
                # CREATE TABLE
                # -----------------------------

                create = conn.execute(
                    text(f"SHOW CREATE TABLE `{nombre}`")
                ).fetchone()

                f.write("-- ======================================\n")
                f.write(f"-- TABLA: {nombre}\n")
                f.write("-- ======================================\n\n")

                f.write(f"DROP TABLE IF EXISTS `{nombre}`;\n\n")

                sql_create = create[1]

                sql_create = sql_create.replace('"', '`')

                f.write(sql_create)
                f.write(";\n\n")

                # -----------------------------
                # DATOS
                # -----------------------------

                registros = conn.execute(
                    text(f"SELECT * FROM `{nombre}`")
                )

                filas = registros.fetchall()

                if filas:

                    columnas = registros.keys()

                    columnas_sql = ", ".join(
                        f"`{c}`"
                        for c in columnas
                    )

                    for fila in filas:

                        valores = ", ".join(
                            sql_value(v)
                            for v in fila
                        )

                        f.write(

                            f"INSERT INTO `{nombre}` "

                            f"({columnas_sql}) "

                            f"VALUES ({valores});\n"

                        )

                    f.write("\n")

            f.write("\nSET FOREIGN_KEY_CHECKS=1;\n")

    return os.path.basename(archivo)

def sql_value(valor):

    if valor is None:
        return "NULL"

    if isinstance(valor, bool):
        return "1" if valor else "0"

    if isinstance(valor, Decimal):
        return str(valor)

    if isinstance(valor, int):
        return str(valor)

    if isinstance(valor, float):
        return str(valor)

    if isinstance(valor, date):
        return f"'{valor}'"

    if isinstance(valor, datetime):
        return f"'{valor.strftime('%Y-%m-%d %H:%M:%S')}'"

    texto = str(valor)

    texto = texto.replace("\\", "\\\\")

    texto = texto.replace("'", "''")

    texto = texto.replace("\n", "\\n")

    texto = texto.replace("\r", "")

    return f"'{texto}'"