"""Impide que el plan elimine formularios o documentos de mantenimiento."""

import re

from sqlalchemy import text

from database.conexion import engine


RELACIONES_PROTEGIDAS = (
    ("mantenimiento_ejecuciones", "mantenimiento_id", "fk_ejecucion_mantenimiento"),
    ("mantenimiento_documentos", "mantenimiento_id", "fk_documento_mantenimiento"),
)


def proteger_relacion(conn, tabla, columna, nombre_predeterminado):
    relacion = conn.execute(text("""
        SELECT kcu.CONSTRAINT_NAME nombre, rc.DELETE_RULE regla
        FROM information_schema.KEY_COLUMN_USAGE kcu
        INNER JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
            ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
           AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
           AND rc.TABLE_NAME = kcu.TABLE_NAME
        WHERE kcu.CONSTRAINT_SCHEMA = DATABASE()
          AND kcu.TABLE_NAME = :tabla
          AND kcu.COLUMN_NAME = :columna
          AND kcu.REFERENCED_TABLE_NAME = 'mantenimientos_programados'
          AND kcu.REFERENCED_COLUMN_NAME = 'id'
        LIMIT 1
    """), {"tabla": tabla, "columna": columna}).mappings().first()

    if relacion and relacion["regla"] in {"RESTRICT", "NO ACTION"}:
        return False

    nombre = relacion["nombre"] if relacion else nombre_predeterminado
    nombre_nuevo = f"{nombre_predeterminado}_protegido" if relacion else nombre
    if not all(
        re.fullmatch(r"[A-Za-z0-9_]+", valor)
        for valor in (nombre, nombre_nuevo)
    ):
        raise RuntimeError(f"Nombre de restricción no válido: {nombre}")
    if relacion:
        conn.execute(text(f"""
            ALTER TABLE `{tabla}`
            DROP FOREIGN KEY `{nombre}`,
            ADD CONSTRAINT `{nombre_nuevo}` FOREIGN KEY (`{columna}`)
                REFERENCES `mantenimientos_programados` (`id`)
                ON DELETE RESTRICT
        """))
    else:
        conn.execute(text(f"""
            ALTER TABLE `{tabla}`
            ADD CONSTRAINT `{nombre}` FOREIGN KEY (`{columna}`)
                REFERENCES `mantenimientos_programados` (`id`)
                ON DELETE RESTRICT
        """))
    return True


if __name__ == "__main__":
    cambios = 0
    with engine.begin() as conexion:
        for tabla, columna, nombre in RELACIONES_PROTEGIDAS:
            cambios += proteger_relacion(conexion, tabla, columna, nombre)
    print(f"Protección del historial aplicada. Relaciones actualizadas: {cambios}")
