"""Crea el catálogo privado y vincula las coincidencias confirmadas de Naranjo."""

from sqlalchemy import text

from database.conexion import engine
from catalogo_formatos_preventivos import CATALOGO_FORMATOS


FORMATOS = [
    ("02-FOR-MTO-02", "Encapsuladora automática #1", "Encapsuladora automática", "VER.04", "02-FOR-MTO-02.pdf", 1, "ACT-0258"),
    ("02-FOR-MTO-19", "Termoselladora #2", "Termoselladora", "VER.02", "02-FOR-MTO-19.pdf", 0, "ACT-0271"),
    ("02-FOR-MTO-31", "Marmita mezcladora #2", "Marmita mezcladora", "VER.02", "02-FOR-MTO-31.pdf", 0, "ACT-0241"),
    ("02-FOR-MTO-35", "Túnel de calor #1", "Túnel de calor", "VER.02", "02-FOR-MTO-35.pdf", 0, "ACT-0252"),
    ("02-FOR-MTO-57", "Loteadora de banda automática #3", "Loteadora de banda", "VER.02", "02-FOR-MTO-57.pdf", 0, "ACT-0254"),
    ("02-FOR-MTO-72", "Envasadora de polvos semiautomática #11", "Envasadora de polvos", "VER.02", "02-FOR-MTO-72.pdf", 0, "ACT-0248"),
    ("02-FOR-MTO-73", "Túnel de calor #2", "Túnel de calor", "VER.02", "02-FOR-MTO-73.pdf", 0, "ACT-0261"),
    ("02-FOR-MTO-79", "Llenadora de líquidos de 4 bocas #2", "Llenadora de líquidos", "VER.02", "02-FOR-MTO-79.pdf", 0, "ACT-0242"),
    ("02-FOR-MTO-81", "Termoselladora #17", "Termoselladora", "VER.02", "02-FOR-MTO-81.pdf", 0, "ACT-0272"),
    ("02-FOR-MTO-82", "Termoselladora #18", "Termoselladora", "VER.02", "02-FOR-MTO-82.pdf", 0, "ACT-0274"),
    ("02-FOR-MTO-87", "Contadora de cápsulas #7", "Contadora de cápsulas", "VER.02", "02-FOR-MTO-87.pdf", 0, "ACT-0215"),
    ("02-FOR-MTO-88", "Envasadora de polvos semiautomática #12", "Envasadora de polvos", "VER.02", "02-FOR-MTO-88.pdf", 0, "ACT-0251"),
    ("02-FOR-MTO-89", "Contadora de cápsulas #8", "Contadora de cápsulas", "VER.02", "02-FOR-MTO-89.pdf", 1, "ACT-0056"),
    ("02-FOR-MTO-92", "Termoselladora #19", "Termoselladora", "VER.02", "02-FOR-MTO-92.pdf", 0, "ACT-0270"),
    ("02-FOR-MTO-93", "Termoselladora #20", "Termoselladora", "VER.02", "02-FOR-MTO-93.pdf", 0, "ACT-0273"),
    ("02-FOR-MTO-96", "Loteadora de banda automática #6", "Loteadora de banda", "VER.02", "02-FOR-MTO-96.pdf", 0, "ACT-0256"),
    ("02-FOR-MTO-101", "Termoselladora #22", "Termoselladora", "VER.03", "02-FOR-MTO-101.pdf", 0, "ACT-0269"),
]


with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS formatos_mantenimiento (
            id INT AUTO_INCREMENT PRIMARY KEY,
            codigo_documento VARCHAR(50) NOT NULL,
            nombre VARCHAR(180) NOT NULL,
            familia VARCHAR(120) NOT NULL,
            version VARCHAR(30) NULL,
            archivo VARCHAR(255) NOT NULL,
            digitalizado TINYINT(1) NOT NULL DEFAULT 0,
            activo TINYINT(1) NOT NULL DEFAULT 1,
            creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_formato_codigo (codigo_documento)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS maquinaria_formatos (
            id_activo VARCHAR(50) NOT NULL PRIMARY KEY,
            formato_id INT NOT NULL,
            confirmado TINYINT(1) NOT NULL DEFAULT 1,
            confirmado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_maquinaria_formato_catalogo FOREIGN KEY (formato_id)
                REFERENCES formatos_mantenimiento(id) ON DELETE RESTRICT,
            KEY idx_maquinaria_formato (formato_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """))
    for codigo, nombre, familia, version, archivo in CATALOGO_FORMATOS:
        conn.execute(text("""
            INSERT INTO formatos_mantenimiento
                (codigo_documento, nombre, familia, version, archivo, digitalizado)
            VALUES (:codigo, :nombre, :familia, :version, :archivo, 0)
            ON DUPLICATE KEY UPDATE nombre = VALUES(nombre), familia = VALUES(familia),
                version = VALUES(version), archivo = VALUES(archivo), activo = 1
        """), {"codigo": codigo, "nombre": nombre, "familia": familia,
               "version": version, "archivo": archivo})
    for codigo, nombre, familia, version, archivo, digitalizado, id_activo in FORMATOS:
        conn.execute(text("""
            INSERT INTO formatos_mantenimiento
                (codigo_documento, nombre, familia, version, archivo, digitalizado)
            VALUES (:codigo, :nombre, :familia, :version, :archivo, :digitalizado)
            ON DUPLICATE KEY UPDATE nombre = VALUES(nombre), familia = VALUES(familia),
                version = VALUES(version), archivo = VALUES(archivo),
                digitalizado = VALUES(digitalizado), activo = 1
        """), {"codigo": codigo, "nombre": nombre, "familia": familia,
               "version": version, "archivo": archivo,
               "digitalizado": digitalizado})
        formato_id = conn.execute(text("""
            SELECT id FROM formatos_mantenimiento WHERE codigo_documento = :codigo
        """), {"codigo": codigo}).scalar_one()
        existe = conn.execute(text("""
            SELECT COUNT(*) FROM maquinarias
            WHERE id_activo = :id AND UPPER(TRIM(ubicacion)) = 'NARANJO'
        """), {"id": id_activo}).scalar_one()
        if not existe:
            raise RuntimeError(f"No existe el activo confirmado {id_activo} en Naranjo.")
        conn.execute(text("""
            INSERT INTO maquinaria_formatos (id_activo, formato_id, confirmado)
            VALUES (:id, :formato, 1)
            ON DUPLICATE KEY UPDATE formato_id = VALUES(formato_id), confirmado = 1,
                confirmado_en = CURRENT_TIMESTAMP
        """), {"id": id_activo, "formato": formato_id})

print(f"Formatos preventivos asociados: {len(FORMATOS)}")
