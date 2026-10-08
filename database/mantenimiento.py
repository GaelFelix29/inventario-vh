import json
from pathlib import Path

from sqlalchemy import text

from database.conexion import engine
from models.auditoria_model import registrar_movimiento
from services.proteccion_historial_mantenimiento import (
    mantenimiento_protegido,
    validar_cambio_mantenimiento,
)


FORMATOS_DIR = Path(__file__).resolve().parent.parent / "private" / "formatos_mantenimiento"


def usuario_puede_editar_plan(usuario_id):
    if not usuario_id:
        return False
    with engine.connect() as conn:
        return bool(conn.execute(text("""
            SELECT edita_plan_mantenimiento
            FROM usuarios
            WHERE id = :id AND activo = 1
            LIMIT 1
        """), {"id": usuario_id}).scalar())


def obtener_formato_activo(id_activo):
    """Devuelve el formato preventivo confirmado para una maquinaria."""
    with engine.connect() as conn:
        fila = conn.execute(text("""
            SELECT fm.id, fm.codigo_documento, fm.nombre, fm.familia,
                   fm.version, fm.archivo, fm.digitalizado
            FROM maquinaria_formatos mf
            INNER JOIN formatos_mantenimiento fm ON fm.id = mf.formato_id
            WHERE mf.id_activo = :id AND fm.activo = 1
            LIMIT 1
        """), {"id": id_activo}).mappings().first()
    return dict(fila) if fila else None


def obtener_archivo_formato(formato_id):
    """Resuelve únicamente archivos registrados dentro del catálogo privado."""
    with engine.connect() as conn:
        fila = conn.execute(text("""
            SELECT id, archivo FROM formatos_mantenimiento
            WHERE id = :id AND activo = 1 LIMIT 1
        """), {"id": formato_id}).mappings().first()
    if not fila:
        return None
    ruta = (FORMATOS_DIR / fila["archivo"]).resolve()
    if FORMATOS_DIR.resolve() not in ruta.parents or not ruta.is_file():
        return None
    return ruta


def obtener_registro_mantenimiento(mantenimiento_id):
    with engine.connect() as conn:
        registro = conn.execute(text("""
            SELECT mp.id mantenimiento_id, mp.semana, mp.estado estado_programado,
                   mp.fecha_programada, mp.fecha_realizada, mp.tecnico,
                   mp.iniciado_manual_en, mp.finalizado_manual_en,
                   p.anio, pe.id_activo,
                   COALESCE(NULLIF(TRIM(m.codigo_mantenimiento), ''), m.id_activo) codigo,
                   COALESCE(NULLIF(TRIM(m.nombre_mantenimiento), ''), m.descripcion) equipo,
                   COALESCE(NULLIF(TRIM(m.departamento), ''), 'Sin asignar') departamento,
                   me.id ejecucion_id, me.estado estado_ejecucion,
                   me.tecnico_nombre,
                   COALESCE(me.iniciado_en, mp.iniciado_manual_en) iniciado_en,
                   COALESCE(me.finalizado_en, mp.finalizado_manual_en) finalizado_en,
                   me.fecha_realizacion, me.formato, me.procedimiento,
                   me.formato_catalogo_id, me.codigo_documento,
                   me.version_documento, me.plantilla_json,
                   me.respuestas_json, me.materiales_json, me.observaciones,
                   me.firma_tecnico, me.firma_supervisor
            FROM mantenimientos_programados mp
            INNER JOIN plan_mantenimiento_equipos pe ON pe.id = mp.plan_equipo_id
            INNER JOIN planes_mantenimiento p ON p.id = pe.plan_id
            INNER JOIN maquinarias m ON m.id_activo = pe.id_activo
            LEFT JOIN mantenimiento_ejecuciones me ON me.mantenimiento_id = mp.id
            WHERE mp.id = :id LIMIT 1
        """), {"id": mantenimiento_id}).mappings().first()
        if not registro:
            return None, []
        documentos = conn.execute(text("""
            SELECT md.id, md.nombre_original, md.tipo_mime, md.subido_en,
                   u.nombre subido_por_nombre
            FROM mantenimiento_documentos md
            LEFT JOIN usuarios u ON u.id = md.subido_por
            WHERE md.mantenimiento_id = :id ORDER BY md.subido_en DESC
        """), {"id": mantenimiento_id}).mappings().all()
    resultado = dict(registro)
    for campo, defecto in (("respuestas_json", {}), ("materiales_json", []),
                           ("plantilla_json", None)):
        valor = resultado.get(campo)
        if isinstance(valor, str):
            try:
                resultado[campo] = json.loads(valor)
            except (TypeError, ValueError):
                resultado[campo] = defecto
        elif valor is None:
            resultado[campo] = defecto
    return resultado, [dict(d) for d in documentos]


def actualizar_datos_historicos_mantenimiento(mantenimiento_id, tecnico,
                                               fecha_realizada, inicio, fin,
                                               usuario):
    with engine.begin() as conn:
        registro = conn.execute(text("""
            SELECT mp.id, mp.estado, me.id ejecucion_id
            FROM mantenimientos_programados mp
            LEFT JOIN mantenimiento_ejecuciones me ON me.mantenimiento_id = mp.id
            WHERE mp.id = :id FOR UPDATE
        """), {"id": mantenimiento_id}).mappings().first()
        if not registro:
            raise ValueError("El mantenimiento no existe.")
        if registro["ejecucion_id"]:
            raise ValueError("Los datos de un formulario digital no se editan manualmente.")
        if registro["estado"] != "REALIZADO":
            raise ValueError("Sólo pueden editarse registros históricos realizados.")
        if inicio and fin and fin < inicio:
            raise ValueError("La finalización no puede ser anterior al inicio.")
        conn.execute(text("""
            UPDATE mantenimientos_programados
            SET tecnico = :tecnico, fecha_realizada = :fecha,
                iniciado_manual_en = :inicio, finalizado_manual_en = :fin
            WHERE id = :id
        """), {"tecnico": tecnico, "fecha": fecha_realizada,
                 "inicio": inicio, "fin": fin, "id": mantenimiento_id})
        registrar_movimiento(
            usuario, "Actualizó datos de un mantenimiento histórico",
            "Mantenimiento", str(mantenimiento_id), conn=conn,
        )


def guardar_documento_mantenimiento(mantenimiento_id, nombre, ruta, tipo_mime,
                                    usuario_id, usuario):
    with engine.begin() as conn:
        existe = conn.execute(text(
            "SELECT id FROM mantenimientos_programados WHERE id = :id"
        ), {"id": mantenimiento_id}).scalar()
        if not existe:
            raise ValueError("El mantenimiento no existe.")
        conn.execute(text("""
            INSERT INTO mantenimiento_documentos
                (mantenimiento_id, nombre_original, ruta_storage, tipo_mime, subido_por)
            VALUES (:id, :nombre, :ruta, :tipo, :usuario_id)
        """), {"id": mantenimiento_id, "nombre": nombre, "ruta": ruta,
               "tipo": tipo_mime, "usuario_id": usuario_id})
        registrar_movimiento(usuario, f"Adjuntó documento de mantenimiento: {nombre}",
                             "Mantenimiento", str(mantenimiento_id), conn=conn)


def obtener_documento_mantenimiento(documento_id):
    with engine.connect() as conn:
        fila = conn.execute(text("""
            SELECT id, mantenimiento_id, nombre_original, ruta_storage, tipo_mime
            FROM mantenimiento_documentos WHERE id = :id LIMIT 1
        """), {"id": documento_id}).mappings().first()
    return dict(fila) if fila else None


def listar_asignacion_formatos():
    """Lista el inventario Naranjo y el catálogo disponible para administración."""
    with engine.connect() as conn:
        maquinas = conn.execute(text("""
            SELECT m.id_activo,
                   COALESCE(NULLIF(TRIM(m.codigo_mantenimiento), ''), m.id_activo) codigo,
                   COALESCE(NULLIF(TRIM(m.nombre_mantenimiento), ''), m.descripcion) equipo,
                   COALESCE(NULLIF(TRIM(m.departamento), ''), 'Sin asignar') departamento,
                   fm.id formato_id, fm.codigo_documento, fm.nombre formato_nombre,
                   fm.version, fm.digitalizado
            FROM maquinarias m
            LEFT JOIN maquinaria_formatos mf ON mf.id_activo = m.id_activo
            LEFT JOIN formatos_mantenimiento fm ON fm.id = mf.formato_id AND fm.activo = 1
            WHERE UPPER(TRIM(m.ubicacion)) = 'NARANJO'
            ORDER BY departamento, codigo
        """)).mappings().all()
        formatos = conn.execute(text("""
            SELECT fm.id, fm.codigo_documento, fm.nombre, fm.familia,
                   fm.version, fm.digitalizado, mf.id_activo asignado_a
            FROM formatos_mantenimiento fm
            LEFT JOIN maquinaria_formatos mf ON mf.formato_id = fm.id
            WHERE fm.activo = 1
            ORDER BY fm.familia, fm.nombre, fm.codigo_documento
        """)).mappings().all()
    return [dict(f) for f in maquinas], [dict(f) for f in formatos]


def actualizar_formato_mantenimiento(formato_id, codigo_documento, nombre,
                                      version, archivo, usuario):
    """Actualiza los datos controlados del catálogo y conserva su trazabilidad."""
    codigo_documento = " ".join((codigo_documento or "").upper().split())
    nombre = " ".join((nombre or "").split())
    version = " ".join((version or "").upper().split())
    if not codigo_documento or not nombre or not version:
        raise ValueError("Completa el código, el nombre y la versión del formato.")
    if len(codigo_documento) > 50 or len(nombre) > 180 or len(version) > 30:
        raise ValueError("Uno de los datos supera la longitud permitida.")

    with engine.begin() as conn:
        actual = conn.execute(text("""
            SELECT id, codigo_documento, nombre, version, archivo, digitalizado
            FROM formatos_mantenimiento
            WHERE id = :id AND activo = 1
            LIMIT 1 FOR UPDATE
        """), {"id": formato_id}).mappings().first()
        if not actual:
            raise ValueError("El formato seleccionado no existe.")
        repetido = conn.execute(text("""
            SELECT id FROM formatos_mantenimiento
            WHERE codigo_documento = :codigo AND id <> :id AND activo = 1
            LIMIT 1
        """), {"codigo": codigo_documento, "id": formato_id}).scalar()
        if repetido:
            raise ValueError("Ya existe otro formato con ese código.")

        cambio_version = (actual["version"] or "") != version
        cambio_archivo = bool(archivo and archivo != actual["archivo"])
        conn.execute(text("""
            UPDATE formatos_mantenimiento
            SET codigo_documento = :codigo,
                nombre = :nombre,
                version = :version,
                archivo = COALESCE(:archivo, archivo),
                digitalizado = CASE
                    WHEN :requiere_revision = 1 THEN 0
                    ELSE digitalizado
                END
            WHERE id = :id
        """), {
            "codigo": codigo_documento,
            "nombre": nombre,
            "version": version,
            "archivo": archivo,
            "requiere_revision": int(cambio_version or cambio_archivo),
            "id": formato_id,
        })

        cambios = []
        if actual["codigo_documento"] != codigo_documento:
            cambios.append(f"código {actual['codigo_documento']} → {codigo_documento}")
        if actual["nombre"] != nombre:
            cambios.append("nombre")
        if cambio_version:
            cambios.append(f"versión {actual['version'] or 'sin versión'} → {version}")
        if cambio_archivo:
            cambios.append("PDF oficial")
        if cambios:
            registrar_movimiento(
                usuario,
                f"Actualizó el formato {codigo_documento}: {', '.join(cambios)}",
                "Mantenimiento", codigo_documento, conn=conn,
            )
        return {
            "codigo_documento": codigo_documento,
            "archivo_anterior": actual["archivo"],
            "requiere_revision": cambio_version or cambio_archivo,
            "hubo_cambios": bool(cambios),
        }


def asignar_formato_activo(id_activo, formato_id, usuario):
    """Asigna, reemplaza o retira un formato con trazabilidad."""
    with engine.begin() as conn:
        maquina = conn.execute(text("""
            SELECT id_activo,
                   COALESCE(NULLIF(TRIM(codigo_mantenimiento), ''), id_activo) codigo
            FROM maquinarias
            WHERE id_activo = :id AND UPPER(TRIM(ubicacion)) = 'NARANJO'
            LIMIT 1 FOR UPDATE
        """), {"id": id_activo}).mappings().first()
        if not maquina:
            raise ValueError("La maquinaria no pertenece al inventario de Naranjo.")
        anterior = conn.execute(text("""
            SELECT fm.codigo_documento FROM maquinaria_formatos mf
            INNER JOIN formatos_mantenimiento fm ON fm.id = mf.formato_id
            WHERE mf.id_activo = :id
        """), {"id": id_activo}).scalar()
        if not formato_id:
            conn.execute(text("DELETE FROM maquinaria_formatos WHERE id_activo = :id"),
                         {"id": id_activo})
            accion = f"Retiró el formato {anterior or 'sin identificar'} de {maquina['codigo']}"
        else:
            formato = conn.execute(text("""
                SELECT id, codigo_documento FROM formatos_mantenimiento
                WHERE id = :id AND activo = 1 LIMIT 1
            """), {"id": formato_id}).mappings().first()
            if not formato:
                raise ValueError("El formato seleccionado no existe.")
            ocupado = conn.execute(text("""
                SELECT id_activo FROM maquinaria_formatos
                WHERE formato_id = :formato AND id_activo <> :activo LIMIT 1
            """), {"formato": formato_id, "activo": id_activo}).scalar()
            if ocupado:
                raise ValueError(f"Este formato ya está asignado a {ocupado}.")
            conn.execute(text("""
                INSERT INTO maquinaria_formatos (id_activo, formato_id, confirmado)
                VALUES (:activo, :formato, 1)
                ON DUPLICATE KEY UPDATE formato_id = VALUES(formato_id),
                    confirmado = 1, confirmado_en = CURRENT_TIMESTAMP
            """), {"activo": id_activo, "formato": formato_id})
            accion = (f"Asignó {formato['codigo_documento']} a {maquina['codigo']}"
                      if not anterior else
                      f"Cambió {maquina['codigo']} de {anterior} a {formato['codigo_documento']}")
        registrar_movimiento(usuario, accion, "Mantenimiento", id_activo, conn=conn)


def obtener_agenda_activo(id_activo, anio):
    """Devuelve las semanas programadas y su ejecución para un activo existente."""
    with engine.connect() as conn:
        equipo = conn.execute(text("""
            SELECT m.id_activo,
                   COALESCE(NULLIF(TRIM(m.codigo_mantenimiento), ''), m.id_activo) codigo,
                   COALESCE(NULLIF(TRIM(m.nombre_mantenimiento), ''), m.descripcion) equipo,
                   COALESCE(NULLIF(TRIM(m.departamento), ''), 'Sin asignar') departamento,
                   COALESCE(NULLIF(TRIM(m.voltaje), ''), 'Sin registrar') voltaje
            FROM maquinarias m WHERE m.id_activo = :id LIMIT 1
        """), {"id": id_activo}).mappings().first()
        if not equipo:
            return None, []
        agenda = conn.execute(text("""
            SELECT mp.id mantenimiento_id, p.anio, mp.semana, mp.estado,
                   mp.fecha_programada, mp.fecha_realizada, mp.tecnico,
                   me.id ejecucion_id, me.estado estado_ejecucion,
                   me.tecnico_nombre, me.iniciado_en, me.finalizado_en
            FROM planes_mantenimiento p
            INNER JOIN plan_mantenimiento_equipos pe ON pe.plan_id = p.id
            INNER JOIN mantenimientos_programados mp ON mp.plan_equipo_id = pe.id
            LEFT JOIN mantenimiento_ejecuciones me ON me.mantenimiento_id = mp.id
            WHERE pe.id_activo = :id AND p.anio = :anio AND pe.activo = 1
              AND mp.estado <> 'SIN_REQUERIMIENTO'
            ORDER BY mp.semana
        """), {"id": id_activo, "anio": anio}).mappings().all()
    return dict(equipo), [dict(fila) for fila in agenda]


def iniciar_ejecucion(mantenimiento_id, id_activo, usuario_id, usuario,
                      formato, plantilla):
    """Abre una sola ejecución por mantenimiento programado y registra su autor."""
    if not mantenimiento_id:
        raise ValueError("Selecciona un mantenimiento programado.")
    with engine.begin() as conn:
        fila = conn.execute(text("""
            SELECT mp.id, mp.semana, mp.estado, p.anio, pe.id_activo
            FROM mantenimientos_programados mp
            INNER JOIN plan_mantenimiento_equipos pe ON pe.id = mp.plan_equipo_id
            INNER JOIN planes_mantenimiento p ON p.id = pe.plan_id
            WHERE mp.id = :id AND pe.id_activo = :id_activo FOR UPDATE
        """), {"id": mantenimiento_id,
                 "id_activo": id_activo}).mappings().first()
        if not fila:
            raise ValueError("El mantenimiento programado ya no existe.")
        if fila["estado"] == "REALIZADO":
            raise ValueError("Este mantenimiento ya fue realizado. Consulta su registro y evidencia.")
        conn.execute(text("""
            INSERT INTO mantenimiento_ejecuciones
                (mantenimiento_id, tecnico_id, tecnico_nombre, formato,
                 formato_catalogo_id, codigo_documento, version_documento,
                 plantilla_json)
            VALUES (:id, :usuario_id, :usuario, :formato,
                    :formato_catalogo_id, :codigo_documento,
                    :version_documento, :plantilla_json)
            ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id),
                formato = COALESCE(formato, VALUES(formato)),
                formato_catalogo_id = COALESCE(formato_catalogo_id,
                                                VALUES(formato_catalogo_id)),
                codigo_documento = COALESCE(codigo_documento,
                                            VALUES(codigo_documento)),
                version_documento = COALESCE(version_documento,
                                             VALUES(version_documento)),
                plantilla_json = COALESCE(plantilla_json,
                                          VALUES(plantilla_json))
        """), {
            "id": mantenimiento_id,
            "usuario_id": usuario_id,
            "usuario": usuario,
            "formato": plantilla.get("codigo_mantenimiento"),
            "formato_catalogo_id": formato.get("id"),
            "codigo_documento": formato.get("codigo_documento"),
            "version_documento": plantilla.get("version") or formato.get("version"),
            "plantilla_json": json.dumps(plantilla, ensure_ascii=False),
        })
        ejecucion_id = conn.execute(text("SELECT LAST_INSERT_ID()" )).scalar()
        conn.execute(text("""
            UPDATE mantenimientos_programados SET tecnico = :usuario
            WHERE id = :id AND (tecnico IS NULL OR tecnico = '')
        """), {"id": mantenimiento_id, "usuario": usuario})
        registrar_movimiento(
            usuario=usuario, accion="Inició formato de mantenimiento",
            modulo="Mantenimiento",
            referencia=f"{fila['id_activo']} · Semana {fila['semana']} · {fila['anio']}",
            conn=conn,
        )
    return ejecucion_id


def obtener_ejecucion(ejecucion_id):
    with engine.connect() as conn:
        fila = conn.execute(text("""
            SELECT me.*, mp.semana, mp.estado estado_programado, p.anio,
                   pe.id_activo,
                   COALESCE(NULLIF(TRIM(m.codigo_mantenimiento), ''), m.id_activo) codigo,
                   COALESCE(NULLIF(TRIM(m.nombre_mantenimiento), ''), m.descripcion) equipo,
                   COALESCE(NULLIF(TRIM(m.departamento), ''), 'Sin asignar') departamento
            FROM mantenimiento_ejecuciones me
            INNER JOIN mantenimientos_programados mp ON mp.id = me.mantenimiento_id
            INNER JOIN plan_mantenimiento_equipos pe ON pe.id = mp.plan_equipo_id
            INNER JOIN planes_mantenimiento p ON p.id = pe.plan_id
            INNER JOIN maquinarias m ON m.id_activo = pe.id_activo
            WHERE me.id = :id LIMIT 1
        """), {"id": ejecucion_id}).mappings().first()
    if not fila:
        return None
    resultado = dict(fila)
    for campo in ("respuestas_json", "materiales_json", "plantilla_json"):
        valor = resultado.get(campo)
        if isinstance(valor, str):
            try:
                resultado[campo] = json.loads(valor)
            except (TypeError, ValueError):
                resultado[campo] = ({} if campo == "respuestas_json" else
                                    [] if campo == "materiales_json" else None)
        elif valor is None:
            resultado[campo] = ({} if campo == "respuestas_json" else
                                [] if campo == "materiales_json" else None)
    return resultado


def guardar_formato_digital(ejecucion_id, datos, usuario, finalizar=False,
                            codigo_formato=""):
    respuestas = datos.get("respuestas", {})
    materiales = datos.get("materiales", [])
    with engine.begin() as conn:
        fila = conn.execute(text("""
            SELECT me.id, me.mantenimiento_id, me.estado, mp.semana,
                   p.anio, pe.id_activo
            FROM mantenimiento_ejecuciones me
            INNER JOIN mantenimientos_programados mp ON mp.id = me.mantenimiento_id
            INNER JOIN plan_mantenimiento_equipos pe ON pe.id = mp.plan_equipo_id
            INNER JOIN planes_mantenimiento p ON p.id = pe.plan_id
            WHERE me.id = :id FOR UPDATE
        """), {"id": ejecucion_id}).mappings().first()
        if not fila:
            raise ValueError("El formato ya no existe.")
        if fila["estado"] == "COMPLETO":
            raise ValueError("Este formato ya fue finalizado.")
        if finalizar:
            if not datos.get("fecha_realizacion") or not datos.get("procedimiento"):
                raise ValueError("Indica la fecha y selecciona al menos un procedimiento.")
            if any(not respuestas.get(clave) for clave in datos.get("claves", [])):
                raise ValueError("Responde todas las actividades antes de finalizar.")
            if not datos.get("firma_tecnico") or not datos.get("firma_supervisor"):
                raise ValueError("Se requieren las firmas del técnico y del supervisor.")
        conn.execute(text("""
            UPDATE mantenimiento_ejecuciones SET
                formato = :formato, fecha_realizacion = :fecha,
                procedimiento = :procedimiento,
                respuestas_json = :respuestas,
                materiales_json = :materiales,
                observaciones = :observaciones,
                firma_tecnico = COALESCE(NULLIF(:firma_tecnico, ''), firma_tecnico),
                firma_supervisor = COALESCE(NULLIF(:firma_supervisor, ''), firma_supervisor),
                estado = :estado,
                finalizado_en = CASE WHEN :estado = 'COMPLETO' THEN NOW() ELSE NULL END
            WHERE id = :id
        """), {
            "fecha": datos.get("fecha_realizacion") or None,
            "formato": codigo_formato,
            "procedimiento": datos.get("procedimiento") or None,
            "respuestas": json.dumps(respuestas, ensure_ascii=False),
            "materiales": json.dumps(materiales, ensure_ascii=False),
            "observaciones": datos.get("observaciones", "").strip(),
            "firma_tecnico": datos.get("firma_tecnico", ""),
            "firma_supervisor": datos.get("firma_supervisor", ""),
            "estado": "COMPLETO" if finalizar else "BORRADOR",
            "id": ejecucion_id,
        })
        if finalizar:
            conn.execute(text("""
                UPDATE mantenimientos_programados
                SET estado = 'REALIZADO', fecha_realizada = :fecha,
                    tecnico = :usuario
                WHERE id = :id
            """), {"fecha": datos["fecha_realizacion"], "usuario": usuario,
                     "id": fila["mantenimiento_id"]})
        registrar_movimiento(
            usuario=usuario,
            accion="Finalizó formato de mantenimiento" if finalizar else
                   "Guardó borrador de mantenimiento",
            modulo="Mantenimiento",
            referencia=f"{fila['id_activo']} · Semana {fila['semana']} · {fila['anio']}",
            conn=conn,
        )


def obtener_anios_planes():
    with engine.connect() as conn:
        return [
            int(anio) for anio in conn.execute(text("""
                SELECT anio FROM planes_mantenimiento
                WHERE UPPER(TRIM(sede)) = 'NARANJO'
                ORDER BY anio DESC
            """)).scalars()
        ]


def obtener_plan_naranjo(anio=2026):
    with engine.connect() as conn:
        plan = conn.execute(text("""
            SELECT id, nombre, sede, anio, version, estado
            FROM planes_mantenimiento
            WHERE UPPER(TRIM(sede)) = 'NARANJO' AND anio = :anio
            LIMIT 1
        """), {"anio": anio}).mappings().first()
        if not plan:
            return None, []

        filas = conn.execute(text("""
            SELECT
                pe.id AS plan_equipo_id,
                pe.periodicidad,
                pe.prioridad,
                m.id_activo,
                COALESCE(NULLIF(TRIM(m.codigo_mantenimiento), ''), m.id_activo) AS codigo,
                COALESCE(NULLIF(TRIM(m.nombre_mantenimiento), ''), m.descripcion) AS equipo,
                COALESCE(NULLIF(TRIM(m.departamento), ''), 'Sin asignar') AS departamento,
                COALESCE(NULLIF(TRIM(m.voltaje), ''), 'Sin registrar') AS voltaje
            FROM plan_mantenimiento_equipos pe
            INNER JOIN maquinarias m ON m.id_activo = pe.id_activo
            WHERE pe.plan_id = :plan_id AND pe.activo = 1
            ORDER BY departamento, codigo
        """), {"plan_id": plan["id"]}).mappings().all()

        estados = conn.execute(text("""
            SELECT mp.id mantenimiento_id, mp.plan_equipo_id, mp.semana, mp.estado,
                   mp.color_excel, mp.estado_excel,
                   me.id ejecucion_id, me.estado estado_ejecucion,
                   EXISTS(
                       SELECT 1 FROM mantenimiento_documentos md
                       WHERE md.mantenimiento_id = mp.id
                   ) tiene_documentos
            FROM mantenimientos_programados mp
            INNER JOIN plan_mantenimiento_equipos pe
                ON pe.id = mp.plan_equipo_id
            LEFT JOIN mantenimiento_ejecuciones me
                ON me.mantenimiento_id = mp.id
            WHERE pe.plan_id = :plan_id
        """), {"plan_id": plan["id"]}).mappings().all()

    por_equipo = {}
    for estado in estados:
        por_equipo.setdefault(estado["plan_equipo_id"], {})[
            int(estado["semana"])
        ] = {
            "estado": estado["estado"],
            "color": estado["color_excel"],
            "etiqueta": estado["estado_excel"] or estado["estado"],
            "ejecucion_id": estado["ejecucion_id"],
            "estado_ejecucion": estado["estado_ejecucion"],
            "mantenimiento_id": estado["mantenimiento_id"],
            "protegido": bool(
                estado["ejecucion_id"]
                or estado["tiene_documentos"]
                or estado["estado"] == "REALIZADO"
            ),
        }

    equipos = []
    for fila in filas:
        equipo = dict(fila)
        equipo["semanas"] = por_equipo.get(equipo["plan_equipo_id"], {})
        equipos.append(equipo)
    return dict(plan), equipos


def resumen_plan(equipos):
    conteos = {"equipos": len(equipos), "programados": 0, "realizados": 0,
               "vencidos": 0, "por_definir": 0}
    for equipo in equipos:
        if equipo["periodicidad"] == "POR DEFINIR":
            conteos["por_definir"] += 1
        for dato in equipo["semanas"].values():
            estado = dato["estado"]
            if estado == "PROGRAMADO":
                conteos["programados"] += 1
            elif estado == "REALIZADO":
                conteos["realizados"] += 1
            elif estado == "NO_REALIZADO":
                conteos["vencidos"] += 1
    return conteos


OPCIONES_PLAN = {
    "SIN_REQUERIMIENTO": ("SIN_REQUERIMIENTO", "SIN REQUERIMIENTO", "FFFF00"),
    "PROGRAMADO": ("PROGRAMADO", "PROGRAMADO", "A9DCC1"),
    "REALIZADO": ("REALIZADO", "REALIZADO", "375623"),
    "REPROGRAMADO": ("REPROGRAMADO", "REPROGRAMADO", "70AD47"),
    "NO_PROGRAMADO": ("SIN_REQUERIMIENTO", "NO PROGRAMADO", "EDF1EF"),
    "NO_REALIZADO": ("NO_REALIZADO", "NO REALIZADO", "FF0000"),
    "DADO_BAJA": ("SIN_REQUERIMIENTO", "DADO DE BAJA", "F69E00"),
}


def guardar_semana_manual(plan_equipo_id, semana, opcion, usuario):
    if not 1 <= semana <= 52:
        raise ValueError("La semana debe estar entre 1 y 52.")
    with engine.begin() as conn:
        existe = conn.execute(text("""
            SELECT pe.id, p.anio,
                   COALESCE(NULLIF(TRIM(m.codigo_mantenimiento), ''), m.id_activo) codigo
            FROM plan_mantenimiento_equipos pe
            INNER JOIN planes_mantenimiento p ON p.id = pe.plan_id
            INNER JOIN maquinarias m ON m.id_activo = pe.id_activo
            WHERE pe.id = :id AND pe.activo = 1
              AND UPPER(TRIM(p.sede)) = 'NARANJO'
              AND UPPER(TRIM(m.ubicacion)) = 'NARANJO'
        """), {"id": plan_equipo_id}).mappings().first()
        if not existe:
            raise ValueError("La maquinaria no pertenece al plan de Naranjo.")
        registro_actual = conn.execute(text("""
            SELECT mp.id, mp.estado, mp.color_excel, mp.estado_excel,
                   EXISTS(
                       SELECT 1 FROM mantenimiento_ejecuciones me
                       WHERE me.mantenimiento_id = mp.id
                   ) tiene_ejecucion,
                   EXISTS(
                       SELECT 1 FROM mantenimiento_documentos md
                       WHERE md.mantenimiento_id = mp.id
                   ) tiene_documentos
            FROM mantenimientos_programados mp
            WHERE mp.plan_equipo_id = :id AND mp.semana = :semana
            FOR UPDATE
        """), {"id": plan_equipo_id, "semana": semana}).mappings().first()
        if opcion == "LIMPIAR":
            validar_cambio_mantenimiento(registro_actual, None)
            conn.execute(text("""
                DELETE FROM mantenimientos_programados
                WHERE plan_equipo_id = :id AND semana = :semana
            """), {"id": plan_equipo_id, "semana": semana})
            registrar_movimiento(
                usuario,
                f"Limpió la semana {semana} de {existe['codigo']} en el plan {existe['anio']}",
                "Mantenimiento", existe["codigo"], conn=conn,
            )
            return {"estado": "PENDIENTE", "etiqueta": "Sin programar",
                    "color": None}
        if opcion not in OPCIONES_PLAN:
            raise ValueError("Selecciona un estado válido.")
        estado, etiqueta, color = OPCIONES_PLAN[opcion]
        validar_cambio_mantenimiento(registro_actual, estado)
        if mantenimiento_protegido(registro_actual):
            return {
                "estado": registro_actual["estado"],
                "etiqueta": registro_actual["estado_excel"] or registro_actual["estado"],
                "color": registro_actual["color_excel"],
                "mantenimiento_id": registro_actual["id"],
                "protegido": True,
            }
        conn.execute(text("""
            INSERT INTO mantenimientos_programados
                (plan_equipo_id, semana, estado, color_excel, estado_excel)
            VALUES (:id, :semana, :estado, :color, :etiqueta)
            ON DUPLICATE KEY UPDATE estado = VALUES(estado),
                color_excel = VALUES(color_excel),
                estado_excel = VALUES(estado_excel)
        """), {"id": plan_equipo_id, "semana": semana, "estado": estado,
               "color": color, "etiqueta": etiqueta})
        mantenimiento_id = conn.execute(text("""
            SELECT id FROM mantenimientos_programados
            WHERE plan_equipo_id = :id AND semana = :semana
        """), {"id": plan_equipo_id, "semana": semana}).scalar_one()
        registrar_movimiento(
            usuario,
            f"Marcó {existe['codigo']} · semana {semana} como {etiqueta} "
            f"en el plan {existe['anio']}",
            "Mantenimiento", existe["codigo"], conn=conn,
        )
        return {"estado": estado, "etiqueta": etiqueta, "color": color,
                "mantenimiento_id": mantenimiento_id,
                "protegido": estado == "REALIZADO"}


def crear_plan_siguiente(anio_origen, usuario):
    anio_nuevo = anio_origen + 1
    with engine.begin() as conn:
        origen = conn.execute(text("""
            SELECT id FROM planes_mantenimiento
            WHERE UPPER(TRIM(sede)) = 'NARANJO' AND anio = :anio
        """), {"anio": anio_origen}).scalar()
        if not origen:
            raise ValueError("El plan de origen no existe.")
        if conn.execute(text("""
            SELECT id FROM planes_mantenimiento
            WHERE UPPER(TRIM(sede)) = 'NARANJO' AND anio = :anio
        """), {"anio": anio_nuevo}).scalar():
            raise ValueError(f"El plan {anio_nuevo} ya existe.")
        resultado = conn.execute(text("""
            INSERT INTO planes_mantenimiento
                (nombre, sede, anio, version, estado)
            VALUES ('Plan de mantenimiento preventivo maquinaria',
                    'NARANJO', :anio, 'Captura manual', 'BORRADOR')
        """), {"anio": anio_nuevo})
        plan_nuevo = resultado.lastrowid
        conn.execute(text("""
            INSERT INTO plan_mantenimiento_equipos
                (plan_id, id_activo, periodicidad, prioridad, activo)
            SELECT :nuevo, m.id_activo,
                   COALESCE(pe.periodicidad, 'POR DEFINIR'),
                   COALESCE(pe.prioridad, 'POR DEFINIR'), 1
            FROM maquinarias m
            LEFT JOIN plan_mantenimiento_equipos pe
              ON pe.id_activo = m.id_activo
             AND pe.plan_id = :origen
             AND pe.activo = 1
            WHERE UPPER(TRIM(m.ubicacion)) = 'NARANJO'
        """), {"nuevo": plan_nuevo, "origen": origen})
        registrar_movimiento(
            usuario, f"Creó el plan de mantenimiento {anio_nuevo}",
            "Mantenimiento", str(anio_nuevo), conn=conn,
        )
    return anio_nuevo


def vaciar_programacion(anio, usuario):
    with engine.begin() as conn:
        plan = conn.execute(text("""
            SELECT id FROM planes_mantenimiento
            WHERE UPPER(TRIM(sede)) = 'NARANJO' AND anio = :anio
        """), {"anio": anio}).scalar()
        if not plan:
            raise ValueError("El plan no existe.")
        protegidos = conn.execute(text("""
            SELECT COUNT(*)
            FROM mantenimientos_programados mp
            INNER JOIN plan_mantenimiento_equipos pe
                ON pe.id = mp.plan_equipo_id
            WHERE pe.plan_id = :plan
              AND (
                  mp.estado = 'REALIZADO'
                  OR EXISTS(
                      SELECT 1 FROM mantenimiento_ejecuciones me
                      WHERE me.mantenimiento_id = mp.id
                  )
                  OR EXISTS(
                      SELECT 1 FROM mantenimiento_documentos md
                      WHERE md.mantenimiento_id = mp.id
                  )
              )
        """), {"plan": plan}).scalar_one()
        resultado = conn.execute(text("""
            DELETE mp FROM mantenimientos_programados mp
            INNER JOIN plan_mantenimiento_equipos pe
                ON pe.id = mp.plan_equipo_id
            WHERE pe.plan_id = :plan
              AND mp.estado <> 'REALIZADO'
              AND NOT EXISTS(
                  SELECT 1 FROM mantenimiento_ejecuciones me
                  WHERE me.mantenimiento_id = mp.id
              )
              AND NOT EXISTS(
                  SELECT 1 FROM mantenimiento_documentos md
                  WHERE md.mantenimiento_id = mp.id
              )
        """), {"plan": plan})
        registrar_movimiento(
            usuario,
            f"Reinició la programación del plan {anio}: {resultado.rowcount} "
            f"semanas sin historial eliminadas y {protegidos} registros protegidos",
            "Mantenimiento", str(anio), conn=conn,
        )
    return {"eliminados": resultado.rowcount, "protegidos": protegidos}
