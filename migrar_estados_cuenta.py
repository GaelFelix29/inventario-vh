from sqlalchemy import text
from database.conexion import engine


SENTENCIAS = [
"""CREATE TABLE IF NOT EXISTS cuentas_bancarias (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, banco VARCHAR(80) NOT NULL,
 numero_cuenta VARCHAR(30) NOT NULL, clabe VARCHAR(18) NOT NULL,
 titular VARCHAR(200) NOT NULL, rfc VARCHAR(20) NULL, activa TINYINT(1) NOT NULL DEFAULT 1,
 creada_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_cuenta_banco (banco, numero_cuenta)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS estados_cuenta (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, cuenta_bancaria_id BIGINT NOT NULL,
 periodo_inicio DATE NOT NULL, periodo_fin DATE NOT NULL,
 saldo_inicial DECIMAL(18,2) NOT NULL, saldo_final DECIMAL(18,2) NOT NULL,
 total_cargos DECIMAL(18,2) NOT NULL, total_abonos DECIMAL(18,2) NOT NULL,
 cantidad_movimientos INT NOT NULL, nombre_archivo VARCHAR(255) NOT NULL,
 archivo_hash CHAR(64) NOT NULL, importado_por INT NOT NULL,
 importado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT fk_estado_cuenta FOREIGN KEY (cuenta_bancaria_id) REFERENCES cuentas_bancarias(id),
 CONSTRAINT fk_estado_usuario FOREIGN KEY (importado_por) REFERENCES usuarios(id),
 UNIQUE KEY uq_estado_periodo (cuenta_bancaria_id, periodo_inicio, periodo_fin),
 UNIQUE KEY uq_estado_archivo (archivo_hash)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS movimientos_bancarios (
 id BIGINT AUTO_INCREMENT PRIMARY KEY, estado_cuenta_id BIGINT NOT NULL,
 renglon_origen INT NOT NULL, fecha DATE NOT NULL, descripcion TEXT NOT NULL,
 referencia VARCHAR(255) NULL, cargo DECIMAL(18,2) NOT NULL DEFAULT 0,
 abono DECIMAL(18,2) NOT NULL DEFAULT 0, saldo DECIMAL(18,2) NOT NULL,
 clasificacion_banco VARCHAR(150) NULL, huella CHAR(64) NOT NULL,
 creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT fk_movimiento_estado FOREIGN KEY (estado_cuenta_id) REFERENCES estados_cuenta(id) ON DELETE CASCADE,
 UNIQUE KEY uq_movimiento_huella (estado_cuenta_id, huella),
 KEY ix_movimiento_fecha (fecha), KEY ix_movimiento_referencia (referencia)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
]

with engine.begin() as conn:
    for sentencia in SENTENCIAS:
        conn.execute(text(sentencia))
print("Tablas de estados de cuenta verificadas correctamente.")
