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
