import json
import unittest
from pathlib import Path

from services.formatos_digitales import (
    claves_plantilla,
    normalizar_procedimientos,
    obtener_plantilla_documento,
    obtener_plantilla_ejecucion,
    presentar_procedimientos,
    serializar_procedimientos,
)


ROOT = Path(__file__).resolve().parent.parent


class FormatosMantenimientoDigitalesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogo = json.loads(
            (ROOT / "config" / "formatos_mantenimiento_digitales.json").read_text(
                encoding="utf-8"
            )
        )["formatos"]

    def test_todos_los_formatos_relacionados_estan_habilitados(self):
        self.assertEqual(len(self.catalogo), 34)
        self.assertTrue(all(item["habilitado"] for item in self.catalogo.values()))

    def test_actividades_tienen_claves_unicas(self):
        total = 0
        for documento, plantilla in self.catalogo.items():
            claves = claves_plantilla(plantilla)
            self.assertTrue(claves, documento)
            self.assertEqual(len(claves), len(set(claves)), documento)
            self.assertEqual(len(plantilla["procedimientos"]), 3, documento)
            self.assertEqual(len(plantilla["materiales"]), 5, documento)
            total += len(claves)
        self.assertEqual(total, 426)

    def test_cada_documento_oficial_existe(self):
        carpeta = ROOT / "private" / "formatos_mantenimiento"
        for documento, plantilla in self.catalogo.items():
            self.assertTrue((carpeta / plantilla["archivo_fuente"]).is_file(), documento)

    def test_relacion_eps7_usa_su_documento_correcto(self):
        plantilla = self.catalogo["02-FOR-MTO-104"]
        self.assertEqual(plantilla["codigo_mantenimiento"], "EPS-7")
        self.assertEqual(plantilla["id_activo"], "ACT-0249")
        self.assertNotIn("02-FOR-MTO-80", self.catalogo)

    def test_ejecucion_prefiere_la_copia_historica(self):
        snapshot = dict(self.catalogo["02-FOR-MTO-84"])
        snapshot["version"] = "VERSIÓN HISTÓRICA"
        resultado = obtener_plantilla_ejecucion({
            "plantilla_json": snapshot,
            "codigo_documento": "02-FOR-MTO-84",
        })
        self.assertEqual(resultado["version"], "VERSIÓN HISTÓRICA")

    def test_formatos_anteriores_conservan_claves(self):
        eco = obtener_plantilla_documento("02-FOR-MTO-02")
        cc8 = obtener_plantilla_documento("02-FOR-MTO-89")
        self.assertEqual(claves_plantilla(eco)[0], "enc_01")
        self.assertEqual(claves_plantilla(cc8)[0], "cc8_01")

    def test_guardado_rapido_envia_csrf_y_valida_json(self):
        contenido = (ROOT / "templates" / "mantenimiento" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("'X-CSRFToken': csrfToken", contenido)
        self.assertIn("'Accept': 'application/json'", contenido)
        self.assertIn("contentType.includes('application/json')", contenido)

    def test_procedimientos_permiten_seleccion_multiple(self):
        permitidos = ["CONVENCIONAL", "KOSHER", "HALAL"]
        seleccion = normalizar_procedimientos(
            ["HALAL", "CONVENCIONAL", "OPCION INVALIDA"], permitidos
        )
        self.assertEqual(seleccion, ["CONVENCIONAL", "HALAL"])
        self.assertEqual(
            serializar_procedimientos(seleccion, permitidos),
            "CONVENCIONAL,HALAL",
        )
        self.assertEqual(
            presentar_procedimientos("CONVENCIONAL,KOSHER,HALAL"),
            "Convencional, Kosher y Halal",
        )

    def test_formulario_envia_procedimientos_como_casillas(self):
        contenido = (ROOT / "templates" / "mantenimiento" / "formato_digital.html").read_text(
            encoding="utf-8"
        )
        ruta = (ROOT / "routes" / "mantenimiento.py").read_text(encoding="utf-8")
        self.assertIn('type="checkbox"', contenido)
        self.assertIn('name="procedimiento"', contenido)
        self.assertIn('request.form.getlist("procedimiento")', ruta)


if __name__ == "__main__":
    unittest.main()
