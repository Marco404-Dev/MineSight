"""Carga verificada e inferencia con los artefactos originales de MineSight."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

FEATURES = (
    "% Iron Feed", "% Silica Feed", "Starch Flow", "Amina Flow",
    "Ore Pulp Flow", "Ore Pulp pH", "Ore Pulp Density",
)
CLUSTERS = tuple(range(7))
MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
HASHES = {
    "kmeans": "594db5324bd0d893e86eecc381c40d863712405c6edb3dd19c65871a4f13c70e",
    "scaler": "c7b65f32d6a9c230fed4c5973cc85445070d57f8ce9c631e76a4344f965f6235",
    "variables": "6795af3f91f53dc8024fe26157a0fec4ae7e0a64aa0619806bd5087fbe9a36c4",
}


@dataclass
class Model:
    estimator: KMeans
    scaler: StandardScaler

    def scale(self, rows: pd.DataFrame) -> np.ndarray:
        try:
            with np.errstate(over="ignore", invalid="ignore"):
                scaled = self.scaler.transform(rows.loc[:, list(FEATURES)])
        except ValueError as exc:
            raise ValueError("No se pudieron escalar las variables. Revisa los valores numéricos.") from exc
        if not np.isfinite(scaled).all() or (np.abs(scaled) > 1e150).any():
            raise ValueError("Hay valores demasiado grandes para calcular distancias con el modelo.")
        return scaled

    def predict(self, rows: pd.DataFrame) -> np.ndarray:
        return self.estimator.predict(self.scale(rows))

    def profiles(self) -> pd.DataFrame:
        centers = self.scaler.inverse_transform(self.estimator.cluster_centers_)
        return pd.DataFrame(centers, index=pd.Index(CLUSTERS, name="Cluster"), columns=FEATURES)

    def training_counts(self) -> pd.Series:
        return pd.Series(np.bincount(self.estimator.labels_, minlength=len(CLUSTERS)), index=CLUSTERS)


def load_model(directory: Path = MODEL_DIR) -> Model:
    if sklearn.__version__ != "1.6.1":
        raise RuntimeError("Instala scikit-learn 1.6.1 para abrir los artefactos de entrenamiento.")
    payloads = {}
    for name, expected in HASHES.items():
        payload = (directory / f"minesight_{name}.pkl").read_bytes()
        if sha256(payload).hexdigest() != expected:
            raise ValueError(f"El artefacto {name} no coincide con el archivo original verificado.")
        payloads[name] = payload

    model = joblib.load(BytesIO(payloads["kmeans"]))
    scaler = joblib.load(BytesIO(payloads["scaler"]))
    variables = joblib.load(BytesIO(payloads["variables"]))
    if not isinstance(model, KMeans) or not isinstance(scaler, StandardScaler):
        raise ValueError("Los artefactos no corresponden a K-Means y StandardScaler.")
    check_is_fitted(model)
    check_is_fitted(scaler)
    if (
        tuple(variables) != FEATURES
        or tuple(scaler.feature_names_in_) != FEATURES
        or model.n_features_in_ != len(FEATURES)
        or scaler.n_features_in_ != len(FEATURES)
        or model.n_clusters != len(CLUSTERS)
        or model.cluster_centers_.shape != (len(CLUSTERS), len(FEATURES))
        or not np.isfinite(model.cluster_centers_).all()
        or not np.isfinite(scaler.mean_).all()
        or not np.isfinite(scaler.scale_).all()
        or (scaler.scale_ <= 0).any()
        or len(model.labels_) != 4097
        or set(model.labels_) != set(CLUSTERS)
    ):
        raise ValueError("Las variables, las dimensiones o los parámetros entrenados son incompatibles.")
    return Model(model, scaler)
