import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import app as api


class DenunciasApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path_original = api.DB_PATH
        api.DB_PATH = Path(self.tempdir.name) / "test.db"
        self.client_context = TestClient(api.app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        api.DB_PATH = self.db_path_original
        self.tempdir.cleanup()

    def test_inicio_redirige_a_documentacion(self) -> None:
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/docs")

    def test_crear_denuncia_y_consultar_estado(self) -> None:
        response = self.client.post(
            "/denuncias",
            json={"categoria": "Corrupcion", "descripcion": "Se solicito un pago indebido para agilizar un tramite."},
        )

        self.assertEqual(response.status_code, 201)
        creada = response.json()
        self.assertEqual(creada["estado"], "recibida")

        estado = self.client.get(
            f"/denuncias/{creada['id']}/estado",
            headers={"X-Codigo-Seguimiento": creada["codigo_seguimiento"]},
        )
        self.assertEqual(estado.status_code, 200)
        self.assertEqual(estado.json()["estado"], "recibida")
        self.assertNotIn("descripcion", estado.json())

    def test_codigo_incorrecto_no_revela_la_denuncia(self) -> None:
        creada = self.client.post(
            "/denuncias",
            json={"categoria": "Corrupcion", "descripcion": "Se solicito un pago indebido para agilizar un tramite."},
        ).json()

        response = self.client.get(
            f"/denuncias/{creada['id']}/estado",
            headers={"X-Codigo-Seguimiento": "codigo-incorrecto"},
        )
        self.assertEqual(response.status_code, 404)

    def test_rechaza_descripcion_demasiado_corta(self) -> None:
        response = self.client.post(
            "/denuncias",
            json={"categoria": "Corrupcion", "descripcion": "Muy breve"},
        )
        self.assertEqual(response.status_code, 422)

    def test_rechaza_categoria_vacia_tras_quitar_espacios(self) -> None:
        response = self.client.post(
            "/denuncias",
            json={"categoria": "   ", "descripcion": "Se solicito un pago indebido para agilizar un tramite."},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()