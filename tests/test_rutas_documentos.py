import unittest
from unittest.mock import ANY, Mock, patch

from flask import Flask, get_flashed_messages

from routes.documentos import _eliminar_archivo_supabase, registrar_rutas_documentos


def permitir_acceso(func):
    return func


class RutasDocumentosTest(unittest.TestCase):
    def test_conserva_urls_metodos_y_endpoints(self):
        app = Flask(__name__)
        registrar_rutas_documentos(
            app,
            permitir_acceso,
            lambda **kwargs: None,
        )

        rutas = {
            (
                regla.rule,
                regla.endpoint,
                tuple(sorted(regla.methods - {"HEAD", "OPTIONS"})),
            )
            for regla in app.url_map.iter_rules()
        }
        esperadas = {
            (
                "/maquinarias/<id_activo>/documentos",
                "subir_documento",
                ("POST",),
            ),
            (
                "/documentos/<int:id_documento>/eliminar",
                "borrar_documento",
                ("POST",),
            ),
            (
                "/qr/<id_activo>/documento/<tipo>",
                "qr_documento",
                ("GET",),
            ),
        }
        self.assertTrue(esperadas.issubset(rutas))

    def test_eliminacion_storage_exige_confirmacion_del_archivo(self):
        bucket = Mock()
        bucket.remove.return_value = [{"name": "ACT-1/documento.pdf"}]
        cliente = Mock()
        cliente.storage.from_.return_value = bucket

        _eliminar_archivo_supabase(cliente, "ACT-1/documento.pdf")

        bucket.remove.assert_called_once_with(["ACT-1/documento.pdf"])

    def test_eliminacion_storage_rechaza_respuesta_sin_confirmacion(self):
        bucket = Mock()
        bucket.remove.return_value = []
        cliente = Mock()
        cliente.storage.from_.return_value = bucket

        with self.assertRaisesRegex(RuntimeError, "no confirmó"):
            _eliminar_archivo_supabase(cliente, "ACT-1/documento.pdf")

    def test_si_falla_storage_no_borra_registro(self):
        app = Flask(__name__)
        app.secret_key = "prueba"
        app.config["WTF_CSRF_ENABLED"] = False

        @app.get("/maquinarias/<id_activo>", endpoint="expediente_maquinaria")
        def expediente(id_activo):
            mensajes = get_flashed_messages(with_categories=True)
            return "|".join(mensaje for _, mensaje in mensajes)

        registrar_rutas_documentos(app, permitir_acceso, lambda **kwargs: None)
        documento = {
            "id": 9,
            "id_activo": "ACT-1",
            "nombre_original": "documento.pdf",
            "public_id": "ACT-1/documento.pdf",
        }

        with (
            patch("routes.documentos.obtener_documento", return_value=documento),
            patch("routes.documentos.supabase_privado", object()),
            patch(
                "routes.documentos._eliminar_archivo_supabase",
                side_effect=RuntimeError("sin permiso"),
            ),
            patch("routes.documentos.eliminar_documento") as borrar_bd,
            patch("routes.documentos.traceback.print_exc"),
        ):
            cliente = app.test_client()
            with cliente.session_transaction() as sesion:
                sesion["rol"] = "Administrador"
                sesion["nombre"] = "Gael"
            respuesta = cliente.post(
                "/documentos/9/eliminar",
                follow_redirects=True,
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"se conserv", respuesta.data)
        borrar_bd.assert_not_called()

    def test_elimina_storage_bd_y_registra_actividad(self):
        app = Flask(__name__)
        app.secret_key = "prueba"
        app.config["WTF_CSRF_ENABLED"] = False

        @app.get("/maquinarias/<id_activo>", endpoint="expediente_maquinaria")
        def expediente(id_activo):
            mensajes = get_flashed_messages(with_categories=True)
            return "|".join(mensaje for _, mensaje in mensajes)

        auditoria = Mock()
        registrar_rutas_documentos(app, permitir_acceso, auditoria)
        documento = {
            "id": 9,
            "id_activo": "ACT-1",
            "nombre_original": "documento.pdf",
            "public_id": "ACT-1/documento.pdf",
        }

        with (
            patch("routes.documentos.obtener_documento", return_value=documento),
            patch("routes.documentos.supabase_privado", object()),
            patch("routes.documentos._eliminar_archivo_supabase") as borrar_storage,
            patch("routes.documentos.eliminar_documento") as borrar_bd,
        ):
            cliente = app.test_client()
            with cliente.session_transaction() as sesion:
                sesion["rol"] = "Administrador"
                sesion["nombre"] = "Gael"
            respuesta = cliente.post(
                "/documentos/9/eliminar",
                follow_redirects=True,
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"eliminado", respuesta.data)
        borrar_storage.assert_called_once_with(
            ANY,
            "ACT-1/documento.pdf",
        )
        borrar_bd.assert_called_once_with(9)
        auditoria.assert_called_once()

    def test_plantilla_lleva_csrf_explicito_en_eliminacion(self):
        from pathlib import Path

        plantilla = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "expediente_maquinaria.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'name="csrf_token" value="{{ csrf_token() }}"',
            plantilla,
        )


if __name__ == "__main__":
    unittest.main()
