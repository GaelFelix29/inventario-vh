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


def listar_movimientos(estado_id, buscar="", tipo="todos", pagina=1,
                       por_pagina=100, concepto="todos", fecha_desde=None,
                       fecha_hasta=None):
    condiciones = ["estado_cuenta_id=:estado_id"]
    parametros = {"estado_id": estado_id, "buscar": f"%{buscar}%"}
    if buscar:
        condiciones.append("(descripcion LIKE :buscar OR referencia LIKE :buscar)")
    if tipo == "cargos": condiciones.append("cargo > 0")
    if tipo == "abonos": condiciones.append("abono > 0")
    if concepto in ("PAGOSA", "PAGOS"):
        condiciones.append(
            "UPPER(descripcion) REGEXP :patron_concepto"
        )
        parametros["patron_concepto"] = (
            rf"(^|[^[:alnum:]_]){concepto}([^[:alnum:]_]|$)"
        )
    if fecha_desde:
        condiciones.append("fecha >= :fecha_desde")
        parametros["fecha_desde"] = fecha_desde
    if fecha_hasta:
        condiciones.append("fecha <= :fecha_hasta")
        parametros["fecha_hasta"] = fecha_hasta
    filtro = " AND ".join(condiciones)
    pagina = max(1, int(pagina))
    por_pagina = max(10, min(int(por_pagina), 200))
    parametros.update({"limite": por_pagina, "offset": (pagina - 1) * por_pagina})
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM movimientos_bancarios WHERE " + filtro), parametros).scalar()
        filas = conn.execute(text("SELECT * FROM movimientos_bancarios WHERE " + filtro +
                                  " ORDER BY renglon_origen LIMIT :limite OFFSET :offset"), parametros).mappings().all()
        return filas, int(total or 0)


def listar_movimientos_exportacion(estado_id, buscar="", tipo="todos",
                                   concepto="todos", fecha_desde=None,
                                   fecha_hasta=None):
    """Devuelve todos los movimientos que coinciden con los filtros del reporte."""
    filas = []
    pagina = 1
    while True:
        lote, total = listar_movimientos(
            estado_id, buscar, tipo, pagina, 200, concepto,
            fecha_desde, fecha_hasta
        )
        filas.extend(lote)
        if len(filas) >= total or not lote:
            return filas
        pagina += 1


def obtener_movimiento_bancario(movimiento_id):
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT m.*, e.periodo_inicio, e.periodo_fin,
                   c.banco, c.numero_cuenta
            FROM movimientos_bancarios m
            JOIN estados_cuenta e ON e.id=m.estado_cuenta_id
            JOIN cuentas_bancarias c ON c.id=e.cuenta_bancaria_id
            WHERE m.id=:id
        """), {"id": movimiento_id}).mappings().first()


def listar_observaciones_movimiento(movimiento_id):
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT o.*, u.nombre AS usuario_nombre
            FROM movimiento_observaciones o
            JOIN usuarios u ON u.id=o.usuario_id
            WHERE o.movimiento_id=:movimiento_id
            ORDER BY o.creada_en DESC, o.id DESC
        """), {"movimiento_id": movimiento_id}).mappings().all()


def guardar_observacion_movimiento(movimiento_id, observacion, usuario_id):
    observacion = (observacion or "").strip()
    if not observacion:
        raise ValueError("Escribe una observación.")
    if len(observacion) > 2000:
        raise ValueError("La observación no puede superar 2,000 caracteres.")
    with engine.begin() as conn:
        existe = conn.execute(text(
            "SELECT id FROM movimientos_bancarios WHERE id=:id"
        ), {"id": movimiento_id}).scalar()
        if not existe:
            raise ValueError("El movimiento no existe.")
        conn.execute(text("""
            INSERT INTO movimiento_observaciones
                (movimiento_id, observacion, usuario_id)
            VALUES (:movimiento_id, :observacion, :usuario_id)
        """), {"movimiento_id": movimiento_id, "observacion": observacion,
                 "usuario_id": usuario_id})


def editar_observacion_movimiento(observacion_id, observacion):
    observacion = (observacion or "").strip()
    if not observacion:
        raise ValueError("Escribe una observación.")
    if len(observacion) > 2000:
        raise ValueError("La observación no puede superar 2,000 caracteres.")
    with engine.begin() as conn:
        movimiento_id = conn.execute(text("""
            SELECT movimiento_id FROM movimiento_observaciones WHERE id=:id
        """), {"id": observacion_id}).scalar()
        if not movimiento_id:
            raise ValueError("La observación no existe.")
        conn.execute(text("""
            UPDATE movimiento_observaciones
            SET observacion=:observacion WHERE id=:id
        """), {"id": observacion_id, "observacion": observacion})
        return movimiento_id


def eliminar_observacion_movimiento(observacion_id):
    with engine.begin() as conn:
        movimiento_id = conn.execute(text("""
            SELECT movimiento_id FROM movimiento_observaciones WHERE id=:id
        """), {"id": observacion_id}).scalar()
        if not movimiento_id:
            raise ValueError("La observación no existe.")
        conn.execute(text(
            "DELETE FROM movimiento_observaciones WHERE id=:id"
        ), {"id": observacion_id})
        return movimiento_id


def listar_archivos_movimiento(movimiento_id):
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT a.*, u.nombre AS usuario_nombre
            FROM movimiento_archivos a
            JOIN usuarios u ON u.id=a.usuario_id
            WHERE a.movimiento_id=:movimiento_id
            ORDER BY a.creado_en DESC, a.id DESC
        """), {"movimiento_id": movimiento_id}).mappings().all()


def guardar_archivo_movimiento(movimiento_id, nombre_original, ruta_storage,
                               url, tipo_mime, tamano_bytes, usuario_id):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO movimiento_archivos
                (movimiento_id, nombre_original, ruta_storage, url,
                 tipo_mime, tamano_bytes, usuario_id)
            VALUES (:movimiento_id, :nombre_original, :ruta_storage, :url,
                    :tipo_mime, :tamano_bytes, :usuario_id)
        """), {"movimiento_id": movimiento_id,
                 "nombre_original": nombre_original,
                 "ruta_storage": ruta_storage, "url": url,
                 "tipo_mime": tipo_mime, "tamano_bytes": tamano_bytes,
                 "usuario_id": usuario_id})


def obtener_archivo_movimiento(archivo_id):
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT a.* FROM movimiento_archivos a
            JOIN movimientos_bancarios m ON m.id=a.movimiento_id
            WHERE a.id=:id
        """), {"id": archivo_id}).mappings().first()


def renombrar_archivo_movimiento(archivo_id, nombre):
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("Escribe un nombre para el archivo.")
    if len(nombre) > 255:
        raise ValueError("El nombre no puede superar 255 caracteres.")
    with engine.begin() as conn:
        movimiento_id = conn.execute(text("""
            SELECT movimiento_id FROM movimiento_archivos WHERE id=:id
        """), {"id": archivo_id}).scalar()
        if not movimiento_id:
            raise ValueError("El archivo no existe.")
        conn.execute(text("""
            UPDATE movimiento_archivos SET nombre_original=:nombre WHERE id=:id
        """), {"id": archivo_id, "nombre": nombre})
        return movimiento_id


def eliminar_archivo_movimiento(archivo_id):
    with engine.begin() as conn:
        movimiento_id = conn.execute(text("""
            SELECT movimiento_id FROM movimiento_archivos WHERE id=:id
        """), {"id": archivo_id}).scalar()
        if not movimiento_id:
            raise ValueError("El archivo no existe.")
        conn.execute(text(
            "DELETE FROM movimiento_archivos WHERE id=:id"
        ), {"id": archivo_id})
        return movimiento_id
