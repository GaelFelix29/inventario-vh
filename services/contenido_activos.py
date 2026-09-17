"""Registros individuales y pertenencia a conjuntos, sin borrar activos."""
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database.conexion import engine
from models.auditoria_model import registrar_movimiento


def _id(valor):
    valor = str(valor or '').strip().upper()
    if not valor or len(valor) > 50:
        raise ValueError('Seleccione un activo válido.')
    return valor


def _campo(datos, nombre, limite, obligatorio=False):
    valor = str(datos.get(nombre) or '').strip()
    if obligatorio and not valor:
        raise ValueError('La descripción del accesorio es obligatoria.')
    if len(valor) > limite:
        raise ValueError(f'{nombre}: máximo {limite} caracteres.')
    return valor


def _validar_contenedor(activo):
    if not activo or not activo['es_contenedor']:
        raise ValueError('El activo debe estar configurado como conjunto de accesorios.')
    if activo['estado'] != 'ACTIVO':
        raise ValueError('El conjunto debe estar activo.')
    if activo['estado_revision_contenido'] != 'EN_REVISION':
        raise ValueError('Inicie o reabra la revisión antes de cambiar el contenido.')


def vincular_en_transaccion(conn, origen, hijo, usuario, observaciones=None):
    origen, hijo = _id(origen), _id(hijo)
    if origen == hijo:
        raise ValueError('Un conjunto no puede contenerse a sí mismo.')
    # Lock both records in a consistent order, including the child: two boxes
    # cannot simultaneously claim the same accessory through this service.
    filas = conn.execute(text('''SELECT id_activo, categoria,
        categoria_accesorio_id, es_contenedor, estado, estado_revision_contenido
        FROM maquinarias WHERE id_activo IN (:origen, :hijo)
        ORDER BY id_activo FOR UPDATE'''), {'origen': origen, 'hijo': hijo}).mappings().all()
    activos = {a['id_activo']: a for a in filas}
    _validar_contenedor(activos.get(origen))
    accesorio = activos.get(hijo)
    if not accesorio or accesorio['estado'] != 'ACTIVO':
        raise ValueError('Seleccione un accesorio activo.')
    if accesorio['es_contenedor']:
        raise ValueError('No se permiten conjuntos dentro de otros conjuntos.')
    if (accesorio['categoria'] or '').strip().upper() not in ('ACCESORIO', 'ACCESORIOS') and not accesorio['categoria_accesorio_id']:
        raise ValueError('El registro seleccionado no es un accesorio.')
    padre = conn.execute(text('''SELECT activo_origen FROM relaciones_activos
        WHERE activo_relacionado = :hijo AND tipo_relacion = 'CONTIENE'
        AND estado = 'ACTIVA' FOR UPDATE'''), {'hijo': hijo}).scalar()
    if padre:
        raise ValueError(f'El accesorio ya pertenece al conjunto {padre}. Retírelo primero.')
    conn.execute(text('''INSERT INTO relaciones_activos
        (activo_origen, activo_relacionado, tipo_relacion, estado, observaciones, creado_por)
        VALUES (:origen, :hijo, 'CONTIENE', 'ACTIVA', :notas, :usuario)'''),
        {'origen': origen, 'hijo': hijo, 'notas': (observaciones or '')[:2000], 'usuario': usuario})
    for referencia in (origen, hijo):
        registrar_movimiento(usuario=usuario, accion=f'Vinculó {hijo} al conjunto {origen}',
                             modulo='Accesorios', referencia=referencia, conn=conn)


def registrar_accesorio_contenido(origen, datos, usuario):
    from database.maquinarias import insertar_maquinaria
    origen = _id(origen)
    campos = {n: _campo(datos, n, limite, n == 'descripcion') for n, limite in
              [('descripcion', 255), ('marca', 100), ('modelo', 100),
               ('numero_serie', 100), ('observaciones', 2000)]}
    # On ID collision with another creation path, roll back EVERYTHING and retry.
    for intento in range(3):
        try:
            with engine.begin() as conn:
                padre = conn.execute(text('''SELECT * FROM maquinarias
                    WHERE id_activo = :id FOR UPDATE'''), {'id': origen}).mappings().first()
                _validar_contenedor(padre)
                numero = conn.execute(text('''SELECT COALESCE(MAX(
                    CAST(SUBSTRING(id_activo, 5) AS UNSIGNED)), 0) + 1
                    FROM maquinarias WHERE id_activo REGEXP '^ACT-[0-9]+$' ''')).scalar()
                nuevo = f'ACT-{int(numero):04d}'
                insertar_maquinaria(dict(campos, id_activo=nuevo, categoria='ACCESORIO',
                    cantidad=1, serie_interna=f'SN-{int(numero):04d}', proveedor='',
                    ubicacion=padre['ubicacion'] or '', fecha_alta=date.today(),
                    precio_unitario_us=0, total_us=0, valor_mx=0), conn=conn)
                vincular_en_transaccion(conn, origen, nuevo, usuario, campos['observaciones'])
                registrar_movimiento(usuario=usuario,
                    accion=f'Registró accesorio individual desde {origen}; valor pendiente de validar, no distribuido del conjunto',
                    modulo='Accesorios', referencia=nuevo, conn=conn)
                return nuevo
        except IntegrityError as error:
            codigo = getattr(error.orig, 'args', [None])[0]
            if codigo != 1062 or intento == 2:
                raise


def convertir_en_conjunto(id_activo, usuario):
    id_activo = _id(id_activo)
    with engine.begin() as conn:
        activo = conn.execute(text('''SELECT * FROM maquinarias
            WHERE id_activo = :id FOR UPDATE'''), {'id': id_activo}).mappings().first()
        if not activo or activo['estado'] != 'ACTIVO':
            raise ValueError('Seleccione un accesorio activo.')
        if activo['es_contenedor']:
            raise ValueError('El activo ya es un conjunto.')
        if (activo['categoria'] or '').strip().upper() not in ('ACCESORIO', 'ACCESORIOS') and not activo['categoria_accesorio_id']:
            raise ValueError('Solo un accesorio puede convertirse en conjunto.')
        asignacion = conn.execute(text('''SELECT id FROM asignaciones_accesorios
            WHERE id_accesorio = :id AND estado = 'ACTIVA' FOR UPDATE'''), {'id': id_activo}).scalar()
        padre = conn.execute(text('''SELECT id FROM relaciones_activos
            WHERE activo_relacionado = :id AND tipo_relacion = 'CONTIENE'
            AND estado = 'ACTIVA' FOR UPDATE'''), {'id': id_activo}).scalar()
        if asignacion or padre:
            raise ValueError('Primero libere la asignación o pertenencia actual. No se eliminará automáticamente.')
        conn.execute(text('''UPDATE maquinarias SET es_contenedor = 1,
            estado_revision_contenido = 'PENDIENTE' WHERE id_activo = :id'''), {'id': id_activo})
        registrar_movimiento(usuario=usuario, accion='Configuró como conjunto; contenido pendiente de verificar',
                             modulo='Accesorios', referencia=id_activo, conn=conn)


def contexto_contenido(id_activo):
    with engine.connect() as conn:
        historial = conn.execute(text('''SELECT r.*, m.descripcion
            FROM relaciones_activos r JOIN maquinarias m ON m.id_activo = r.activo_relacionado
            WHERE r.activo_origen = :id AND r.tipo_relacion = 'CONTIENE'
            ORDER BY r.fecha_inicio DESC, r.id DESC'''), {'id': id_activo}).mappings().all()
        padre = conn.execute(text('''SELECT r.activo_origen, m.descripcion
            FROM relaciones_activos r JOIN maquinarias m ON m.id_activo = r.activo_origen
            WHERE r.activo_relacionado = :id AND r.tipo_relacion = 'CONTIENE'
            AND r.estado = 'ACTIVA' LIMIT 1'''), {'id': id_activo}).mappings().first()
        return {'historial_contenido': [dict(r) for r in historial],
                'conjunto_padre': dict(padre) if padre else None}


def buscar_accesorios_disponibles(consulta):
    with engine.connect() as conn:
        filas = conn.execute(text('''SELECT m.id_activo AS id, m.descripcion,
            m.categoria, m.ubicacion FROM maquinarias m
            WHERE m.estado = 'ACTIVO' AND COALESCE(m.es_contenedor, 0) = 0
            AND (UPPER(TRIM(m.categoria)) IN ('ACCESORIO','ACCESORIOS')
                 OR m.categoria_accesorio_id IS NOT NULL)
            AND NOT EXISTS (SELECT 1 FROM relaciones_activos r
                WHERE r.activo_relacionado=m.id_activo AND r.tipo_relacion='CONTIENE'
                AND r.estado='ACTIVA')
            AND (m.id_activo LIKE :q OR m.descripcion LIKE :q OR m.marca LIKE :q
                 OR m.numero_serie LIKE :q)
            ORDER BY m.id_activo LIMIT 20'''), {'q': f'%{consulta[:100]}%'}).mappings().all()
        return [dict(fila) for fila in filas]
