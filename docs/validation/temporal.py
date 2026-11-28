"""Evalúa una partición cronológica sin cargar ni escribir los PKL."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from services.model import FEATURES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()

    readings = pd.read_csv(args.csv, decimal=",")
    readings["date"] = pd.to_datetime(readings["date"], errors="coerce")
    unique = readings.drop_duplicates()
    hourly = unique.groupby("date")[list(FEATURES)].mean().dropna()
    cutoff = pd.Timestamp("2017-07-01")
    train = hourly.loc[hourly.index < cutoff]
    holdout = hourly.loc[hourly.index >= cutoff]
    if min(len(train), len(holdout)) < 8:
        parser.error("El CSV necesita suficientes horas a ambos lados del corte.")

    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train)
    holdout_scaled = scaler.transform(holdout)
    estimator = KMeans(n_clusters=7, random_state=42, n_init=10)
    train_labels = estimator.fit_predict(train_scaled)
    holdout_labels = estimator.predict(holdout_scaled)
    train_distance = estimator.transform(train_scaled).min(axis=1)
    holdout_distance = estimator.transform(holdout_scaled).min(axis=1)
    threshold = float(np.percentile(train_distance, 95))

    print(f"Filas: {len(readings)}; únicas: {len(unique)}; horas: {len(hourly)}")
    for name, rows, scaled, labels, distances in (
        ("Ajuste", train, train_scaled, train_labels, train_distance),
        ("Evaluación", holdout, holdout_scaled, holdout_labels, holdout_distance),
    ):
        sizes = np.bincount(labels, minlength=7)
        silhouette = silhouette_score(scaled, labels) if 1 < np.count_nonzero(sizes) < len(rows) else float("nan")
        print(f"{name}: {rows.index.min()} a {rows.index.max()}; n={len(rows)}")
        print(f"  Clústeres 0–6: {sizes.tolist()}; silhouette={silhouette:.4f}")
        print(f"  Distancia mediana={np.median(distances):.4f}; sobre P95 ajuste={100*np.mean(distances > threshold):.2f}%")
    print(f"P95 de distancia en ajuste: {threshold:.4f}")


if __name__ == "__main__":
    main()
