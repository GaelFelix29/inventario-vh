from sqlalchemy import text

from database.conexion import engine


def importar_estado_cuenta(estado, usuario_id):
    with engine.begin() as conn:
        cuenta_id = conn.execute(text("""
            SELECT id FROM cuentas_bancarias
            WHERE banco=:banco AND numero_cuenta=:numero_cuenta FOR UPDATE
        """), estado).scalar()
        if not cuenta_id:
            cuenta_id = conn.execute(text("""
                INSERT INTO cuentas_bancarias (banco, numero_cuenta, clabe, titular, rfc)
                VALUES (:banco, :numero_cuenta, :clabe, :titular, :rfc)
            """), estado).lastrowid
        existente = conn.execute(text("""
            SELECT id FROM estados_cuenta
            WHERE cuenta_bancaria_id=:cuenta_id AND periodo_inicio=:periodo_inicio
              AND periodo_fin=:periodo_fin
        """), {**estado, "cuenta_id": cuenta_id}).scalar()
        if existente:
            raise ValueError("Este estado de cuenta mensual ya fue importado.")
        estado_id = conn.execute(text("""
            INSERT INTO estados_cuenta
            (cuenta_bancaria_id, periodo_inicio, periodo_fin, saldo_inicial,
             saldo_final, total_cargos, total_abonos, cantidad_movimientos,
             nombre_archivo, archivo_hash, importado_por)
            VALUES (:cuenta_id, :periodo_inicio, :periodo_fin, :saldo_inicial,
                    :saldo_final, :total_cargos, :total_abonos, :cantidad,
                    :nombre_archivo, :archivo_hash, :usuario_id)
        """), {**estado, "cuenta_id": cuenta_id, "cantidad": len(estado["movimientos"]), "usuario_id": usuario_id}).lastrowid
        conn.execute(text("""
            INSERT INTO movimientos_bancarios
            (estado_cuenta_id, renglon_origen, fecha, descripcion, referencia,
             cargo, abono, saldo, clasificacion_banco, huella)
            VALUES (:estado_id, :renglon_origen, :fecha, :descripcion, :referencia,
                    :cargo, :abono, :saldo, :clasificacion_banco, :huella)
        """), [{**movimiento, "estado_id": estado_id} for movimiento in estado["movimientos"]])
        return estado_id


def listar_estados_cuenta():
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT e.*, c.banco, c.numero_cuenta, c.titular
            FROM estados_cuenta e JOIN cuentas_bancarias c ON c.id=e.cuenta_bancaria_id
            ORDER BY e.periodo_fin DESC, e.id DESC
        """)).mappings().all()


def obtener_estado_cuenta(estado_id):
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT e.*, c.banco, c.numero_cuenta, c.clabe, c.titular
            FROM estados_cuenta e JOIN cuentas_bancarias c ON c.id=e.cuenta_bancaria_id
            WHERE e.id=:id
        """), {"id": estado_id}).mappings().first()


def listar_movimientos(estado_id, buscar="", tipo="todos", pagina=1, por_pagina=100):
    condiciones = ["estado_cuenta_id=:estado_id"]
    parametros = {"estado_id": estado_id, "buscar": f"%{buscar}%"}
    if buscar:
        condiciones.append("(descripcion LIKE :buscar OR referencia LIKE :buscar)")
    if tipo == "cargos": condiciones.append("cargo > 0")
    if tipo == "abonos": condiciones.append("abono > 0")
    filtro = " AND ".join(condiciones)
    pagina = max(1, int(pagina))
    por_pagina = max(10, min(int(por_pagina), 200))
    parametros.update({"limite": por_pagina, "offset": (pagina - 1) * por_pagina})
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM movimientos_bancarios WHERE " + filtro), parametros).scalar()
        filas = conn.execute(text("SELECT * FROM movimientos_bancarios WHERE " + filtro +
                                  " ORDER BY renglon_origen LIMIT :limite OFFSET :offset"), parametros).mappings().all()
        return filas, int(total or 0)
