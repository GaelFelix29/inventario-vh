"""Activa las plantillas digitales revisadas y conserva su versión histórica."""

import json

from sqlalchemy import text

from database.conexion import engine
from models.auditoria_model import registrar_movimiento
from services.formatos_digitales import cargar_catalogo_digital


COLUMNAS_EJECUCION = {
    "formato_catalogo_id": "INT NULL",
    "codigo_documento": "VARCHAR(50) NULL",
    "version_documento": "VARCHAR(30) NULL",
    "plantilla_json": "JSON NULL",
}


catalogo = cargar_catalogo_digital()
cambios_relacion = 0
ejecuciones_actualizadas = 0

with engine.begin() as conn:
    columnas = {
        fila["Field"] for fila in conn.execute(
            text("SHOW COLUMNS FROM mantenimiento_ejecuciones")
        ).mappings()
    }
    for nombre, definicion in COLUMNAS_EJECUCION.items():
        if nombre not in columnas:
            conn.execute(text(
                f"ALTER TABLE mantenimiento_ejecuciones ADD COLUMN {nombre} {definicion}"
            ))

    codigos_digitales = list(catalogo)
    for plantilla in catalogo.values():
        formato_id = conn.execute(text("""
            SELECT id FROM formatos_mantenimiento
            WHERE codigo_documento = :codigo AND activo = 1 LIMIT 1
        """), {"codigo": plantilla["codigo_documento"]}).scalar()
        if not formato_id:
            raise RuntimeError(
                f"No existe {plantilla['codigo_documento']} en formatos_mantenimiento."
            )
        existe_activo = conn.execute(text("""
            SELECT COUNT(*) FROM maquinarias WHERE id_activo = :activo
        """), {"activo": plantilla["id_activo"]}).scalar_one()
        if not existe_activo:
            raise RuntimeError(
                f"El activo {plantilla['id_activo']} no existe en el inventario."
            )
        anterior = conn.execute(text("""
            SELECT formato_id FROM maquinaria_formatos
            WHERE id_activo = :activo LIMIT 1
        """), {"activo": plantilla["id_activo"]}).scalar()
        if anterior != formato_id:
            cambios_relacion += 1
        conn.execute(text("""
            UPDATE formatos_mantenimiento
            SET version = :version, digitalizado = 1, activo = 1
            WHERE id = :id
        """), {
            "version": plantilla["version"],
            "id": formato_id,
        })
        conn.execute(text("""
            INSERT INTO maquinaria_formatos (id_activo, formato_id, confirmado)
            VALUES (:activo, :formato, 1)
            ON DUPLICATE KEY UPDATE formato_id = VALUES(formato_id), confirmado = 1,
                confirmado_en = CURRENT_TIMESTAMP
        """), {"activo": plantilla["id_activo"], "formato": formato_id})

        resultado = conn.execute(text("""
            UPDATE mantenimiento_ejecuciones me
            INNER JOIN mantenimientos_programados mp
                ON mp.id = me.mantenimiento_id
            INNER JOIN plan_mantenimiento_equipos pe
                ON pe.id = mp.plan_equipo_id
            SET me.formato_catalogo_id = COALESCE(me.formato_catalogo_id, :formato),
                me.codigo_documento = COALESCE(me.codigo_documento, :codigo),
                me.version_documento = COALESCE(me.version_documento, :version),
                me.plantilla_json = COALESCE(me.plantilla_json, :plantilla)
            WHERE pe.id_activo = :activo
              AND (me.plantilla_json IS NULL OR me.codigo_documento IS NULL
                   OR me.version_documento IS NULL)
        """), {
            "formato": formato_id,
            "codigo": plantilla["codigo_documento"],
            "version": plantilla["version"],
            "plantilla": json.dumps(plantilla, ensure_ascii=False),
            "activo": plantilla["id_activo"],
        })
        ejecuciones_actualizadas += resultado.rowcount

    # Evita que un formato sin plantilla activa se anuncie como digital.
    parametros = {f"codigo_{i}": codigo for i, codigo in enumerate(codigos_digitales)}
    lugares = ", ".join(f":codigo_{i}" for i in range(len(codigos_digitales)))
    conn.execute(text(f"""
        UPDATE formatos_mantenimiento
        SET digitalizado = 0
        WHERE codigo_documento NOT IN ({lugares})
    """), parametros)

    if cambios_relacion:
        registrar_movimiento(
            "Sistema",
            f"Actualizó {cambios_relacion} relación(es) de formato preventivo",
            "Mantenimiento",
            "Plantillas digitales",
            conn=conn,
        )

print(f"Plantillas digitales activadas: {len(catalogo)}")
print(f"Relaciones corregidas: {cambios_relacion}")
print(f"Ejecuciones históricas completadas: {ejecuciones_actualizadas}")
