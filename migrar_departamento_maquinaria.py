from sqlalchemy import text

from database.conexion import engine


def agregar_departamento_maquinaria():
    """Agrega el departamento opcional al activo si todavía no existe."""
    with engine.begin() as conn:
        existente = conn.execute(text(
            "SHOW COLUMNS FROM maquinarias LIKE 'departamento'"
        )).mappings().first()
        if existente:
            print("La columna departamento ya existe.")
            return

        conn.execute(text(
            "ALTER TABLE maquinarias "
            "ADD COLUMN departamento VARCHAR(100) NULL AFTER voltaje"
        ))
        print("Columna departamento creada correctamente.")


if __name__ == "__main__":
    agregar_departamento_maquinaria()
