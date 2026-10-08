"""Crea la base del plan y vincula únicamente activos existentes de Naranjo."""
from sqlalchemy import text

from database.conexion import engine


DDL = [
    """CREATE TABLE IF NOT EXISTS planes_mantenimiento (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(150) NOT NULL,
        sede VARCHAR(100) NOT NULL,
        anio SMALLINT NOT NULL,
        version VARCHAR(30) NULL,
        estado ENUM('BORRADOR','ACTIVO','CERRADO') NOT NULL DEFAULT 'BORRADOR',
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_plan_sede_anio (sede, anio)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS plan_mantenimiento_equipos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        plan_id INT NOT NULL,
        id_activo VARCHAR(50) NOT NULL,
        periodicidad VARCHAR(20) NOT NULL DEFAULT 'POR DEFINIR',
        prioridad ENUM('ALTA','MEDIA','BAJA','POR DEFINIR') NOT NULL DEFAULT 'POR DEFINIR',
        activo TINYINT(1) NOT NULL DEFAULT 1,
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_plan_activo (plan_id, id_activo),
        CONSTRAINT fk_plan_equipo_plan FOREIGN KEY (plan_id)
            REFERENCES planes_mantenimiento(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS mantenimientos_programados (
        id INT AUTO_INCREMENT PRIMARY KEY,
        plan_equipo_id INT NOT NULL,
        semana TINYINT UNSIGNED NOT NULL,
        estado ENUM('PROGRAMADO','REALIZADO','NO_REALIZADO','REPROGRAMADO','SIN_REQUERIMIENTO')
            NOT NULL DEFAULT 'PROGRAMADO',
        fecha_programada DATE NULL,
        fecha_realizada DATE NULL,
        tecnico VARCHAR(150) NULL,
        iniciado_manual_en DATETIME NULL,
        finalizado_manual_en DATETIME NULL,
        observaciones TEXT NULL,
        formato VARCHAR(50) NULL,
        fecha_realizacion DATE NULL,
        procedimiento ENUM('CONVENCIONAL','KOSHER','HALAL') NULL,
        respuestas_json JSON NULL,
        materiales_json JSON NULL,
        firma_tecnico LONGTEXT NULL,
        firma_supervisor LONGTEXT NULL,
        actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_equipo_semana (plan_equipo_id, semana),
        CONSTRAINT fk_programado_equipo FOREIGN KEY (plan_equipo_id)
            REFERENCES plan_mantenimiento_equipos(id) ON DELETE CASCADE,
        CONSTRAINT chk_semana CHECK (semana BETWEEN 1 AND 53)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS mantenimiento_documentos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        mantenimiento_id INT NOT NULL,
        nombre_original VARCHAR(255) NOT NULL,
        ruta_storage VARCHAR(500) NOT NULL,
        tipo_mime VARCHAR(120) NULL,
        subido_por INT NULL,
        subido_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_documento_mantenimiento FOREIGN KEY (mantenimiento_id)
            REFERENCES mantenimientos_programados(id) ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS mantenimiento_ejecuciones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        mantenimiento_id INT NOT NULL,
        estado ENUM('BORRADOR','COMPLETO','CANCELADO') NOT NULL DEFAULT 'BORRADOR',
        tecnico_id INT NULL,
        tecnico_nombre VARCHAR(150) NOT NULL,
        iniciado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        finalizado_en DATETIME NULL,
        observaciones TEXT NULL,
        actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_ejecucion_mantenimiento (mantenimiento_id),
        CONSTRAINT fk_ejecucion_mantenimiento FOREIGN KEY (mantenimiento_id)
            REFERENCES mantenimientos_programados(id) ON DELETE RESTRICT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


with engine.begin() as conn:
    columnas_usuario = {
        fila["Field"] for fila in conn.execute(
            text("SHOW COLUMNS FROM usuarios")
        ).mappings()
    }
    if "edita_plan_mantenimiento" not in columnas_usuario:
        conn.execute(text("""
            ALTER TABLE usuarios
            ADD COLUMN edita_plan_mantenimiento TINYINT(1) NOT NULL DEFAULT 0
        """))
    conn.execute(text("""
        UPDATE usuarios
        SET edita_plan_mantenimiento = CASE
            WHEN LOWER(usuario) IN ('gael', 'alejandra') THEN 1 ELSE 0 END
    """))
    for sentencia in DDL:
        conn.execute(text(sentencia))
    columnas_ejecucion = {
        fila["Field"] for fila in conn.execute(
            text("SHOW COLUMNS FROM mantenimiento_ejecuciones")
        ).mappings()
    }
    columnas_digitales = {
        "formato": "VARCHAR(50) NULL",
        "formato_catalogo_id": "INT NULL",
        "codigo_documento": "VARCHAR(50) NULL",
        "version_documento": "VARCHAR(30) NULL",
        "plantilla_json": "JSON NULL",
        "fecha_realizacion": "DATE NULL",
        "procedimiento": "VARCHAR(30) NULL",
        "respuestas_json": "JSON NULL",
        "materiales_json": "JSON NULL",
        "firma_tecnico": "LONGTEXT NULL",
        "firma_supervisor": "LONGTEXT NULL",
    }
    for nombre, definicion in columnas_digitales.items():
        if nombre not in columnas_ejecucion:
            conn.execute(text(
                f"ALTER TABLE mantenimiento_ejecuciones ADD COLUMN {nombre} {definicion}"
            ))
    tipo_procedimiento = next(
        (
            fila["Type"]
            for fila in conn.execute(
                text("SHOW COLUMNS FROM mantenimiento_ejecuciones")
            ).mappings()
            if fila["Field"] == "procedimiento"
        ),
        "",
    ).lower()
    if not tipo_procedimiento.startswith("varchar(100)"):
        conn.execute(text("""
            ALTER TABLE mantenimiento_ejecuciones
            MODIFY COLUMN procedimiento VARCHAR(100) NULL
        """))
    columnas_programado = {
        fila["Field"] for fila in conn.execute(
            text("SHOW COLUMNS FROM mantenimientos_programados")
        ).mappings()
    }
    for nombre in ("iniciado_manual_en", "finalizado_manual_en"):
        if nombre not in columnas_programado:
            conn.execute(text(
                f"ALTER TABLE mantenimientos_programados ADD COLUMN {nombre} DATETIME NULL"
            ))
    conn.execute(text("""
        INSERT INTO planes_mantenimiento(nombre, sede, anio, version, estado)
        VALUES ('Plan de mantenimiento preventivo maquinaria', 'NARANJO', 2026,
                'Base para conciliación', 'BORRADOR')
        ON DUPLICATE KEY UPDATE nombre = VALUES(nombre)
    """))
    plan_id = conn.execute(text("""
        SELECT id FROM planes_mantenimiento
        WHERE sede = 'NARANJO' AND anio = 2026 LIMIT 1
    """)).scalar_one()
    resultado = conn.execute(text("""
        INSERT IGNORE INTO plan_mantenimiento_equipos(plan_id, id_activo)
        SELECT :plan_id, id_activo
        FROM maquinarias
        WHERE UPPER(TRIM(ubicacion)) = 'NARANJO'
    """), {"plan_id": plan_id})

print("Tablas de mantenimiento creadas correctamente.")
print(f"Activos de Naranjo vinculados al plan: {resultado.rowcount}")
