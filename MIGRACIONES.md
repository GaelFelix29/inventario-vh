# Migraciones de base de datos

El proyecto conserva cada cambio de estructura como un script idempotente dentro
del repositorio. Los scripts revisan primero el esquema, por lo que pueden
ejecutarse nuevamente sin duplicar columnas.

## Orden actual

1. `migrar_datos_mantenimiento.py`
   - Agrega `codigo_mantenimiento`, `nombre_mantenimiento` y `voltaje`.
2. `migrar_departamento_maquinaria.py`
   - Agrega `departamento` como `VARCHAR(100) NULL`.
3. `migrar_mensajes.py`
   - Crea las conversaciones privadas, mensajes e índices de lectura.
4. `migrar_estados_cuenta.py`
   - Crea cuentas bancarias, estados mensuales y movimientos conciliados.
5. `migrar_detalle_movimientos_bancarios.py`
   - Crea observaciones y archivos asociados a cada movimiento bancario.

El módulo financiero también requiere un bucket **privado** de Supabase llamado
`finanzas`. Los archivos se organizan por estado y movimiento. La aplicación
genera enlaces temporales de cinco minutos únicamente para usuarios autorizados.
El servidor debe tener la variable `SUPABASE_SERVICE_ROLE_KEY`; esta credencial
se configura en `.env` y en Render, y nunca se guarda en Git.

Ambas migraciones ya fueron aplicadas manualmente en la base de producción el
22 de septiembre de 2026. Los scripts permanecen en Git para instalaciones
nuevas, recuperación de respaldos y trazabilidad.

`migrar_mensajes.py` queda pendiente de aplicar antes de desplegar el módulo de
mensajería. La aplicación conserva el contador en cero mientras esas tablas no
existan, para no afectar las pantallas actuales durante el despliegue.

## Procedimiento para cada despliegue

1. Crear y comprobar un respaldo de la base de datos.
2. Ejecutar las migraciones pendientes en el orden indicado.
3. Verificar las columnas o tablas creadas.
4. Desplegar la versión de la aplicación que utiliza esos cambios.
5. Probar creación, edición y consulta de un activo.

La estructura se actualiza antes que la aplicación para evitar que una versión
nueva consulte columnas todavía inexistentes.

## Regla para cambios futuros

- Crear un script nuevo; no modificar ni borrar migraciones ya aplicadas.
- Hacer que el script compruebe primero si el cambio ya existe.
- No ejecutar migraciones automáticamente al iniciar la aplicación web.
- No incluir cargas masivas de datos dentro de una migración de estructura.
- Conservar las cargas de datos en scripts separados y transaccionales.

Las cargas actuales están separadas en:

- `cargar_relacion_mantenimiento.py`
- `cargar_departamentos_maquinaria.py`
- `cargar_estado_cuenta.py`
# Roles de Compras y Finanzas

Si la base de datos fue creada antes de incorporar los módulos financieros,
ejecute una vez:

```powershell
python migrar_roles_financieros.py
```

La migración amplía `usuarios.rol` para aceptar `Compras` y `Finanzas`. Es
seguro volver a ejecutarla porque primero comprueba la definición existente.
# Mantenimiento preventivo

Ejecutar una sola vez para crear el plan base de Naranjo 2026 y vincular las
maquinarias que ya existen en esa ubicación:

```powershell
python migrar_mantenimiento_preventivo.py
```

La migración no crea ni modifica maquinarias. Los equipos quedan con
periodicidad y prioridad `POR DEFINIR` hasta realizar la conciliación con el
plan de Mantenimiento.

Para conservar los colores originales del Excel, ejecutar después:

```powershell
python migrar_colores_plan_mantenimiento.py
```

Después, Administrador y Mantenimiento pueden asignar manualmente cada estado
semanal desde la cuadrícula. Esta función no crea ni modifica maquinarias.
