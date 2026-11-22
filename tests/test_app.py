import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / 'app.py'


class AppTests(unittest.TestCase):
    def test_dashboard_navigation_and_manual_prediction(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(app.title[0].value, "Inteligencia aplicada a operaciones mineras")
        self.assertTrue(any("Registros originales" in item.value for item in app.html))
        app.button[0].click().run()
        self.assertEqual(app.title[0].value, "Análisis de operaciones")
        self.assertFalse(app.exception)
        app.radio[0].set_value("Predicción manual").run()
        self.assertEqual(len(app.number_input), 7)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(any("Cluster asignado" in item.value for item in app.html))
        app.radio[0].set_value("Panel ejecutivo").run()
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Método y alcance")

    def test_csv_upload_hourly_processing_and_pca(self):
        from services.model import load_model

        sample = load_model().profiles().iloc[:4].reset_index(drop=True)
        sample["date"] = [
            "2017-03-10 01:05:00", "2017-03-10 02:05:00",
            "2017-03-10 03:05:00", "2017-03-10 03:15:00",
        ]
        app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
        app.radio[0].set_value("Análisis CSV").run()
        app.file_uploader[0].upload("lote.csv", sample.to_csv(index=False).encode(), "text/csv").run()
        app.radio(key="granularity").set_value("Promedios por hora").run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual([metric.value for metric in app.metric[:2]], ["4", "3"])
        app.checkbox[0].check().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Varianza explicada" in item.value for item in app.caption))
        self.assertEqual(len(app.get("download_button")), 3)
