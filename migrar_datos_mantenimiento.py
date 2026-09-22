from sqlalchemy import text

from database.conexion import engine


COLUMNAS = {
    "codigo_mantenimiento": "VARCHAR(30) NULL AFTER serie_interna",
    "nombre_mantenimiento": "VARCHAR(150) NULL AFTER codigo_mantenimiento",
    "voltaje": "VARCHAR(30) NULL AFTER nombre_mantenimiento",
}


def agregar_datos_mantenimiento():
    """Agrega únicamente las columnas ausentes; puede ejecutarse más de una vez."""
    with engine.begin() as conn:
        existentes = {
            fila["Field"]
            for fila in conn.execute(text("SHOW COLUMNS FROM maquinarias")).mappings()
        }
        for nombre, definicion in COLUMNAS.items():
            if nombre in existentes:
                print(f"La columna {nombre} ya existe.")
                continue
            conn.execute(text(f"ALTER TABLE maquinarias ADD COLUMN {nombre} {definicion}"))
            print(f"Columna {nombre} creada correctamente.")


if __name__ == "__main__":
    agregar_datos_mantenimiento()
