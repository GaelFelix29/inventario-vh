"""Alta de accesorios ya existentes físicamente, desde su maquinaria."""
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database.conexion import engine
from database.maquinarias import insertar_maquinaria, asignar_accesorio_maquinaria
from models.auditoria_model import registrar_movimiento


def buscar_accesorios_asignables(consulta):
    consulta = str(consulta or '').strip()[:100]
    if len(consulta) < 2:
        return []
    with engine.connect() as conn:
        filas = conn.execute(text('''SELECT m.id_activo AS id, m.descripcion,
            m.categoria, m.marca, m.modelo, m.numero_serie, m.serie_interna
            FROM maquinarias m
            WHERE m.estado = 'ACTIVO' AND COALESCE(m.es_contenedor, 0) = 0
            AND UPPER(TRIM(m.categoria)) IN ('ACCESORIO', 'ACCESORIOS')
            AND NOT EXISTS (SELECT 1 FROM asignaciones_accesorios a
                WHERE a.id_accesorio = m.id_activo AND a.estado = 'ACTIVA')
            AND (m.id_activo LIKE :q OR m.descripcion LIKE :q
                OR m.marca LIKE :q OR m.modelo LIKE :q
                OR m.numero_serie LIKE :q OR m.serie_interna LIKE :q)
            ORDER BY m.id_activo LIMIT 20'''), {'q': f'%{consulta}%'}).mappings().all()
        return [dict(fila) for fila in filas]


def registrar_accesorio_maquinaria(id_maquinaria, datos, usuario):
    id_maquinaria = str(id_maquinaria or '').strip().upper()
    if not id_maquinaria or len(id_maquinaria) > 20:
        raise ValueError('Seleccione una maquinaria válida.')
    campos = {}
    for nombre, limite in [('descripcion', 255), ('marca', 100), ('modelo', 100),
                           ('numero_serie', 150), ('observaciones', 500)]:
        valor = str(datos.get(nombre) or '').strip()
        if len(valor) > limite:
            raise ValueError(f'{nombre}: máximo {limite} caracteres.')
        campos[nombre] = valor or None
    if not campos['descripcion']:
        raise ValueError('La descripción del accesorio es obligatoria.')

    for intento in range(3):
        try:
            with engine.begin() as conn:
                maquina = conn.execute(text('''SELECT id_activo, categoria,
                    es_contenedor, estado, ubicacion FROM maquinarias
                    WHERE id_activo = :id FOR UPDATE'''),
                    {'id': id_maquinaria}).mappings().first()
                if (not maquina or maquina['es_contenedor']
                        or (maquina['categoria'] or '').strip().upper() in ('ACCESORIO', 'ACCESORIOS')
                        or (maquina['estado'] or '').strip().upper() != 'ACTIVO'):
                    raise ValueError('Seleccione una maquinaria activa, no un accesorio ni un conjunto.')
                numero = int(conn.execute(text('''SELECT COALESCE(MAX(
                    CAST(SUBSTRING(id_activo, 5) AS UNSIGNED)), 0) + 1
                    FROM maquinarias WHERE id_activo REGEXP '^ACT-[0-9]+$' ''')).scalar())
                nuevo = f'ACT-{numero:04d}'
                if len(nuevo) > 20:
                    raise ValueError('No se pudo generar un identificador válido.')
                insertar_maquinaria(dict(campos, id_activo=nuevo, categoria='ACCESORIO',
                    cantidad=1, serie_interna=f'SN-{numero:04d}', proveedor=None,
                    ubicacion=maquina['ubicacion'], fecha_alta=None,
                    precio_unitario_us=None, total_us=None, valor_mx=None), conn=conn)
                asignar_accesorio_maquinaria(nuevo, id_maquinaria, usuario,
                    observaciones='Registro de accesorio ya en uso; fecha original de asignación desconocida.',
                    conn=conn, permitir_reasignacion=False)
                for referencia in (nuevo, id_maquinaria):
                    registrar_movimiento(usuario=usuario,
                        accion=f'Registró {nuevo}, ya en uso en {id_maquinaria}; fecha original y valor pendientes',
                        modulo='Accesorios', referencia=referencia, conn=conn)
                return nuevo
        except IntegrityError as error:
            # A competing creation can reserve the same ACT number. Retry the
            # entire transaction; never leave an unassigned asset behind.
            if getattr(error.orig, 'args', [None])[0] != 1062 or intento == 2:
                raise
