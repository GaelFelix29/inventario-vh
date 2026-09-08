from sqlalchemy import text

from database.conexion import engine


def agregar_columna_password_temporal():
    with engine.begin() as conn:
        columnas = conn.execute(
            text("""
                SHOW COLUMNS
                FROM usuarios
                LIKE 'debe_cambiar_password'
            """)
        ).fetchall()

        if columnas:
            print(
                "La columna debe_cambiar_password ya existe. "
                "No se realizaron cambios."
            )
            return

        conn.execute(
            text("""
                ALTER TABLE usuarios
                ADD COLUMN debe_cambiar_password TINYINT(1)
                NOT NULL DEFAULT 0
                AFTER password
            """)
        )

        print(
            "Columna debe_cambiar_password creada correctamente."
        )


if __name__ == "__main__":
    agregar_columna_password_temporal()
