from sqlalchemy import text

from database.conexion import engine


AVATAR_DEFAULT = "usuario"


def agregar_columna_avatar():

    with engine.begin() as conn:

        columnas = conn.execute(
            text("""
                SHOW COLUMNS
                FROM usuarios
                LIKE 'avatar'
            """)
        ).fetchall()

        if columnas:

            print(
                "La columna avatar ya existe. "
                "No se realizaron cambios."
            )

            return

        conn.execute(
            text("""
                ALTER TABLE usuarios
                ADD COLUMN avatar VARCHAR(30)
                NOT NULL DEFAULT 'usuario'
                AFTER correo
            """)
        )

        print(
            "Columna avatar creada correctamente."
        )


if __name__ == "__main__":

    agregar_columna_avatar()