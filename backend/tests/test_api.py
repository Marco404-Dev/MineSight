import io
import unittest

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import MAX_UPLOAD, app
from services.model import FEATURES, load_model


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()
        cls.info = cls.client.get("/api/model-info").json()
        cls.legacy = load_model()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def fixtures(self):
        frame = self.legacy.profiles().iloc[:4].reset_index(drop=True)
        frame.iloc[3] = frame.iloc[2] * 1.0001
        frame["date"] = [
            "2017-03-10 01:05:00", "2017-03-10 02:05:00",
            "2017-03-10 03:05:00", "2017-03-10 03:15:00",
        ]
        return frame

    def upload(self, path, payload, settings=None, name="operaciones.csv"):
        return self.client.post(path, files={"file": (name, payload, "text/csv")}, data=settings)

    def test_model_and_openapi(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok", "model_ready": True})
        self.assertEqual(self.info["features"], list(FEATURES))
        self.assertEqual(self.info["training_hours"], 4097)
        self.assertEqual(len(self.info["clusters"]), 7)
        self.assertEqual(self.info["metrics"]["ari"], 0.9959)
        self.assertIn("/api/predict", self.client.get("/openapi.json").json()["paths"])

    def test_prediction_matches_legacy_pipeline(self):
        references = pd.concat([
            self.legacy.profiles(),
            pd.DataFrame([self.legacy.scaler.mean_], columns=FEATURES),
        ])
        expected = self.legacy.predict(references)
        for values, cluster in zip(references.to_numpy(), expected):
            payload = dict(zip(self.info["input_keys"], values.tolist()))
            response = self.client.post("/api/predict", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            self.assertEqual(result["cluster"], int(cluster))
            self.assertEqual(len(result["descriptors"]), 3)
            nearest = min(result["distances"], key=lambda entry: entry["distance"])
            self.assertEqual(nearest["cluster"], int(cluster))
        response = self.client.post("/api/predict", json={"iron_feed": "texto"})
        self.assertEqual(response.status_code, 422)

    def test_preview_hourly_pca_and_exports(self):
        frame = self.fixtures()
        payload = frame.to_csv(index=False).encode()
        preview = self.upload("/api/preview-csv", payload).json()
        self.assertEqual(preview["temporal_candidates"], ["date"])
        self.assertEqual(preview["source_count"], 4)
        settings = {"time_column": "date"}
        response = self.upload("/api/analyze-csv", payload, settings)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["operation_count"], 3)
        self.assertEqual(len(result["pca"]["points"]), 3)
        self.assertEqual(sum(item["count"] for item in result["distribution"]), 3)
        for kind in ("operations", "summary", "report"):
            with self.subTest(kind=kind):
                exported = self.upload("/api/export-csv/" + kind, payload, settings)
                self.assertEqual(exported.status_code, 200, exported.text)
                self.assertIn("attachment", exported.headers["content-disposition"])
                if kind == "operations":
                    rows = pd.read_csv(io.BytesIO(exported.content))
                    self.assertEqual(rows["Mediciones"].tolist(), [1, 1, 2])
                    np.testing.assert_array_equal(rows["Cluster"], self.legacy.predict(rows))
                else:
                    self.assertIn("Cluster", exported.text)

    def test_rejects_invalid_uploads(self):
        self.assertEqual(self.upload("/api/analyze-csv", b"col\n1").status_code, 422)
        self.assertEqual(self.upload("/api/analyze-csv", b"col\n1", name="x.pkl").status_code, 415)
        oversized = b"x" * (MAX_UPLOAD + 128 * 1024 + 1)
        self.assertEqual(self.upload("/api/analyze-csv", oversized).status_code, 413)

    def test_configured_cors(self):
        good = self.client.get("/api/health", headers={"Origin": "http://localhost:3000"})
        bad = self.client.get("/api/health", headers={"Origin": "https://example.invalid"})
        self.assertEqual(good.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertNotIn("access-control-allow-origin", bad.headers)
