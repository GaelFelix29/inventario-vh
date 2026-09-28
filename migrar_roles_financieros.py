"""Amplía los roles permitidos para Compras y Finanzas.

Puede ejecutarse varias veces sin alterar usuarios existentes.
"""

from sqlalchemy import text

from database.conexion import engine


ROLES_REQUERIDOS = {
    "Administrador", "Visualizador", "Mantenimiento", "Compras", "Finanzas"
}


def migrar_roles_financieros():
    with engine.begin() as conn:
        columna = conn.execute(text("""
            SELECT COLUMN_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'usuarios'
              AND COLUMN_NAME = 'rol'
        """)).scalar()
        if not columna:
            raise RuntimeError("No se encontró la columna usuarios.rol.")

        faltantes = [rol for rol in ROLES_REQUERIDOS if f"'{rol}'" not in columna]
        if faltantes:
            conn.execute(text("""
                ALTER TABLE usuarios
                MODIFY COLUMN rol ENUM(
                    'Administrador',
                    'Visualizador',
                    'Mantenimiento',
                    'Compras',
                    'Finanzas'
                ) NOT NULL DEFAULT 'Visualizador'
            """))
            print("Roles agregados: " + ", ".join(sorted(faltantes)))
        else:
            print("Los roles Compras y Finanzas ya estaban disponibles.")

    print("Roles de usuario verificados correctamente.")


if __name__ == "__main__":
    migrar_roles_financieros()
