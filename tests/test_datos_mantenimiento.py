import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def cargar_normalizador():
    arbol = ast.parse((ROOT / "database/maquinarias.py").read_text(encoding="utf-8"))
    funcion = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef)
        and nodo.name == "normalizar_datos_mantenimiento"
    )
    modulo = ast.Module(body=[funcion], type_ignores=[])
    entorno = {}
    exec(compile(ast.fix_missing_locations(modulo), "normalizador", "exec"), entorno)
    return entorno["normalizar_datos_mantenimiento"]


def cargar_relacion():
    arbol = ast.parse((ROOT / "cargar_relacion_mantenimiento.py").read_text(encoding="utf-8"))
    asignacion = next(
        nodo for nodo in arbol.body
        if isinstance(nodo, ast.Assign)
        and any(isinstance(objetivo, ast.Name) and objetivo.id == "RELACION"
                for objetivo in nodo.targets)
    )
    return ast.literal_eval(asignacion.value)


class DatosMantenimientoTest(unittest.TestCase):
    def test_normaliza_codigo_nombre_y_voltaje(self):
        normalizar = cargar_normalizador()
        self.assertEqual(
            normalizar(" tc-2 ", "  Túnel   de calor #2 ", " 220 v  "),
            {
                "codigo_mantenimiento": "TC-2",
                "nombre_mantenimiento": "Túnel de calor #2",
                "voltaje": "220 V",
            },
        )

    def test_acepta_campos_vacios(self):
        normalizar = cargar_normalizador()
        self.assertEqual(
            normalizar(None, "", None),
            {
                "codigo_mantenimiento": "",
                "nombre_mantenimiento": "",
                "voltaje": "",
            },
        )

    def test_rechaza_valores_mayores_al_limite(self):
        normalizar = cargar_normalizador()
        with self.assertRaises(ValueError):
            normalizar("X" * 31, "Equipo", "220 V")
        with self.assertRaises(ValueError):
            normalizar("TC-2", "X" * 151, "220 V")
        with self.assertRaises(ValueError):
            normalizar("TC-2", "Equipo", "X" * 31)

    def test_relacion_inicial_es_completa_y_sin_duplicados(self):
        relacion = cargar_relacion()
        self.assertEqual(len(relacion), 17)
        self.assertEqual(len({fila["id"] for fila in relacion}), 17)
        self.assertEqual(len({fila["codigo"] for fila in relacion}), 17)
        mm2 = next(fila for fila in relacion if fila["id"] == "ACT-0241")
        self.assertEqual(mm2, {
            "id": "ACT-0241",
            "codigo": "MM-2",
            "nombre": "Marmita mezcladora #2",
            "voltaje": "220 V",
        })
        self.assertNotIn("ACT-0291", {fila["id"] for fila in relacion})
        tc2 = next(fila for fila in relacion if fila["id"] == "ACT-0261")
        self.assertEqual(tc2, {
            "id": "ACT-0261",
            "codigo": "TC-2",
            "nombre": "Túnel de calor #2",
            "voltaje": "220 V",
        })

    def test_formularios_y_vistas_contienen_los_tres_campos(self):
        formularios = [
            "templates/nueva_maquinaria.html",
            "templates/maquinaria_qr/nueva_maquinaria_mobile.html",
            "templates/maquinaria_qr/editar_maquinaria_mobile.html",
        ]
        for ruta in formularios:
            contenido = (ROOT / ruta).read_text(encoding="utf-8")
            for campo in ("codigo_mantenimiento", "nombre_mantenimiento", "voltaje"):
                self.assertIn(f'name="{campo}"', contenido, ruta)

            self.assertIn('name="departamento"', contenido, ruta)

        vistas = [
            "templates/expediente_maquinaria.html",
            "templates/maquinaria_qr/inicio.html",
            "templates/etiquetas.html",
            "templates/fichas.html",
            "templates/qr_maquinaria.html",
        ]
        for ruta in vistas:
            contenido = (ROOT / ruta).read_text(encoding="utf-8")
            for campo in ("codigo_mantenimiento", "nombre_mantenimiento", "voltaje"):
                self.assertIn(campo, contenido, ruta)

        vistas_con_departamento = [
            ruta for ruta in vistas
            if ruta not in ("templates/etiquetas.html", "templates/fichas.html")
        ]
        for ruta in vistas_con_departamento:
            self.assertIn(
                "departamento",
                (ROOT / ruta).read_text(encoding="utf-8"),
                ruta,
            )
        self.assertNotIn(
            "departamento",
            (ROOT / "templates/etiquetas.html").read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "departamento",
            (ROOT / "templates/fichas.html").read_text(encoding="utf-8"),
        )

    def test_persistencia_y_busquedas_incluyen_campos_nuevos(self):
        contenido = (ROOT / "database/maquinarias.py").read_text(encoding="utf-8")
        self.assertIn("codigo_mantenimiento = :codigo_mantenimiento", contenido)
        self.assertIn("nombre_mantenimiento = :nombre_mantenimiento", contenido)
        self.assertIn("voltaje = :voltaje", contenido)
        self.assertGreaterEqual(contenido.count("codigo_mantenimiento LIKE"), 3)

        rutas = (ROOT / "routes/maquinaria.py").read_text(encoding="utf-8")
        self.assertEqual(
            rutas.count('"codigo_mantenimiento": request.form.get('), 4
        )
        self.assertEqual(rutas.count('"departamento": request.form.get('), 4)

        self.assertIn("departamento = :departamento", contenido)

    def test_departamento_es_opcional_y_tiene_migracion_idempotente(self):
        contenido = (ROOT / "database/maquinarias.py").read_text(encoding="utf-8")
        self.assertIn("return departamento or None", contenido)

        migracion = (ROOT / "migrar_departamento_maquinaria.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("SHOW COLUMNS FROM maquinarias LIKE 'departamento'", migracion)
        self.assertIn("VARCHAR(100) NULL", migracion)

        carga = (ROOT / "cargar_departamentos_maquinaria.py").read_text(
            encoding="utf-8"
        )
        arbol = ast.parse(carga)
        asignacion = next(
            nodo for nodo in arbol.body
            if isinstance(nodo, ast.Assign)
            and any(
                isinstance(objetivo, ast.Name)
                and objetivo.id == "DEPARTAMENTOS"
                for objetivo in nodo.targets
            )
        )
        departamentos = ast.literal_eval(asignacion.value)
        self.assertEqual(len(departamentos), 17)
        self.assertEqual(departamentos["ACT-0241"], "Envasado de líquidos")
        self.assertNotIn("ACT-0291", departamentos)

    def test_migracion_es_idempotente_y_carga_valida_antes_de_actualizar(self):
        migracion = (ROOT / "migrar_datos_mantenimiento.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("SHOW COLUMNS FROM maquinarias", migracion)
        self.assertIn("if nombre in existentes", migracion)

        carga = (ROOT / "cargar_relacion_mantenimiento.py").read_text(
            encoding="utf-8"
        )
        self.assertLess(carga.index("if faltantes:"), carga.index("UPDATE maquinarias"))

    def test_archivos_python_modificados_tienen_sintaxis_valida(self):
        rutas = [
            "database/maquinarias.py",
            "routes/maquinaria.py",
            "routes/etiquetas.py",
            "migrar_datos_mantenimiento.py",
            "cargar_relacion_mantenimiento.py",
            "migrar_departamento_maquinaria.py",
            "cargar_departamentos_maquinaria.py",
        ]
        for ruta in rutas:
            ast.parse((ROOT / ruta).read_text(encoding="utf-8"), filename=ruta)


if __name__ == "__main__":
    unittest.main()
