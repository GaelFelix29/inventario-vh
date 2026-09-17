# Conjuntos de accesorios

## Uso

1. Abrir el expediente de un accesorio individual (categoría ACCESORIO o ACCESORIOS).
2. En Identidad y pertenencia, abrir «¿Este registro representa una caja con varias piezas?».
3. Configurar como conjunto. Se mantiene ID, clasificación, documentos y valor; no se crean piezas automáticamente.
4. Iniciar revisión. Registrar cada pieza identificable (cantidad 1, nuevo ACT y SN) o vincular su ID existente.
5. Entrar al expediente de cada pieza para sus fotografías, documentos, clasificación y asignaciones.
6. Finalizar solo después de la revisión física. Si se necesita cambiar el contenido, reabrir.

No convertir automáticamente todos los ACCESORIOS: puede haber piezas individuales.
Un accesorio asignado debe liberarse antes de convertirlo en conjunto; no se eliminan asignaciones automáticamente.
Un conjunto no puede contener otro conjunto. Cada accesorio puede pertenecer a un solo conjunto vigente.
La pertenencia no equivale a presencia física: se muestra por separado la maquinaria a la que presta servicio.
Retirar solo desactiva la relación y deja fecha e historial; conserva el activo y sus documentos/asignaciones.
No se reparte el valor de la caja automáticamente. Los nuevos registros tienen valores 0 pendientes de validación por finanzas.

## Verificación realizada

Pruebas aisladas de reglas y rollback con SQLite (sin cargar credenciales).
Plantillas para lectura y gestión, tres estados de revisión, vista de escritorio y móvil.
Vista visual aislada con datos ficticios: escritorio y 390 px de ancho.

## Antes de publicar

No se ejecutaron migraciones ni escrituras en producción. Se reutilizan columnas/tablas ya empleadas por el módulo anterior.
En una base MySQL de PRUEBAS, comprobar el esquema real, los tamaños de campos y el motor transaccional InnoDB de
maquinarias, relaciones_activos, categorias_accesorios, asignaciones_accesorios y auditoria.
Comprobar clave única de maquinarias.id_activo y revisar posibles relaciones activas duplicadas preexistentes.
Probar dos usuarios vinculando simultáneamente la misma pieza y creando registros al mismo tiempo.
SQLite no valida bloqueos FOR UPDATE, interbloqueos ni las restricciones particulares del esquema real MySQL.
Antes del despliegue, disponer de respaldo recuperable de la base.

Consultas de diagnóstico de solo lectura para la base de pruebas:

```sql
SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN
('maquinarias','relaciones_activos','categorias_accesorios','asignaciones_accesorios','auditoria');
SHOW INDEX FROM maquinarias;
SELECT activo_relacionado, COUNT(*) AS relaciones_activas
FROM relaciones_activos WHERE tipo_relacion='CONTIENE' AND estado='ACTIVA'
GROUP BY activo_relacionado HAVING COUNT(*) > 1;
```

Los duplicados históricos deben revisarse manualmente, no eliminarse automáticamente.
