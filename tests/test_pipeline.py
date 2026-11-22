import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from services.analytics import csv_bytes, project, report, summarize
from services.model import FEATURES, load_model
from services.operations import hourly, read_csv


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load_model()

    def test_artifacts_and_inference_for_new_rows(self):
        rows = self.model.profiles() + self.model.scaler.scale_ * 0.001
        reordered = rows.loc[:, list(reversed(FEATURES))]
        expected = self.model.estimator.predict(self.model.scaler.transform(rows))
        np.testing.assert_array_equal(self.model.predict(reordered), expected)
        np.testing.assert_array_equal(expected, np.arange(7))
        self.assertEqual(self.model.training_counts().sum(), 4097)

    def test_rejects_altered_artifacts_before_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "minesight_kmeans.pkl").write_bytes(b"invalid")
            with self.assertRaisesRegex(ValueError, "original"):
                load_model(directory)

    def test_hourly_averages_and_counts(self):
        rows = self.model.profiles().iloc[:3].reset_index(drop=True)
        rows["date"] = ["2017-03-10 01:03:00", "2017-03-10 01:53:30", "2017-03-10 02:00:00"]
        loaded = read_csv(rows.to_csv(index=False).encode(), ",", ".")
        grouped = hourly(loaded, "date")
        self.assertEqual(grouped["Mediciones"].tolist(), [2, 1])
        np.testing.assert_allclose(grouped.loc[0, list(FEATURES)].astype(float), rows.iloc[:2, :7].mean())
        self.assertEqual(len(self.model.predict(grouped)), 2)
        with self.assertRaisesRegex(ValueError, "fechas"):
            hourly(loaded.assign(date="inválida"), "date")

    def test_validates_csv(self):
        header = ",".join(FEATURES) + "\n"
        for body, expected in [
            ("", "al menos una"),
            ("1,2,3", "campos"),
            ("1,2,3,4,5,6,", "faltante"),
            ("1,2,inf,4,5,6,7", "inválido"),
            ("1,2,error,4,5,6,7", "inválido"),
        ]:
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, expected):
                read_csv((header + body).encode(), ",", ".")
        with self.assertRaisesRegex(ValueError, "duplicados"):
            read_csv((",".join(FEATURES + (FEATURES[0],)) + "\n").encode(), ",", ".")
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            read_csv(b"foo,bar\n1,2", ",", ".")

    def test_decimal_comma_csv(self):
        payload = ";".join(FEATURES) + "\n" + ";".join(["1,25"] * 7)
        loaded = read_csv(payload.encode(), ";", ",")
        np.testing.assert_allclose(loaded.iloc[0], [1.25] * 7)

    def test_pca_and_exports(self):
        rows = self.model.profiles().reset_index(drop=True)
        rows["Cluster"] = self.model.predict(rows)
        points, ratio = project(self.model, rows, rows)
        self.assertEqual(len(points), len(rows))
        self.assertTrue(0 < ratio.sum() <= 1)
        with self.assertRaisesRegex(ValueError, "tres"):
            project(self.model, rows.iloc[:1], rows)
        summary = summarize(rows["Cluster"])
        self.assertEqual(int(summary["Operaciones"].sum()), 7)
        self.assertIn("Cluster 6", report(summary, self.model.profiles(), 7, "por fila"))
        self.assertIn("Cluster", csv_bytes(rows).decode("utf-8-sig"))
        self.assertIn("'=1+4", csv_bytes(pd.DataFrame({"nota": ["=1+4"]})).decode("utf-8-sig"))
