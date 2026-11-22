"""Preparación de resultados y exportaciones para las rutas CSV."""

import json
from dataclasses import dataclass

import pandas as pd

from services.analytics import csv_bytes, project, report, summarize
from services.model import FEATURES, Model
from services.operations import LABEL_COLUMN, hourly, read_csv


@dataclass
class Batch:
    rows: pd.DataFrame
    original: pd.DataFrame
    summary: pd.DataFrame
    profiles: pd.DataFrame
    mode: str

    def export(self, kind: str) -> tuple[bytes, str, str]:
        if kind == "operations":
            return csv_bytes(self.rows), "text/csv", "minesight_operaciones.csv"
        if kind == "summary":
            return csv_bytes(self.summary.round(4)), "text/csv", "minesight_resumen.csv"
        return (
            report(self.summary, self.profiles, len(self.original), self.mode).encode("utf-8"),
            "text/markdown", "minesight_reporte.md",
        )


def analyze(model: Model, payload: bytes, separator: str, decimal: str, time_column: str) -> Batch:
    original = read_csv(payload, separator, decimal)
    if time_column and (time_column not in original or time_column in FEATURES):
        raise ValueError("Selecciona una columna de fecha y hora válida.")
    rows = hourly(original, time_column) if time_column else original.copy()
    if LABEL_COLUMN in rows:
        raise ValueError("La columna Cluster está reservada para el resultado. Renómbrala en el CSV.")
    rows[LABEL_COLUMN] = model.predict(rows)
    return Batch(
        rows, original, summarize(rows[LABEL_COLUMN]),
        rows.groupby(LABEL_COLUMN)[list(FEATURES)].mean(),
        "promedios por hora" if time_column else "una operación por fila",
    )


def preview(frame: pd.DataFrame, limit: int) -> dict:
    return {
        "columns": list(frame.columns),
        "rows": json.loads(frame.head(limit).to_json(orient="values", date_format="iso")),
    }


def serialize_batch(model: Model, batch: Batch, include_pca: bool) -> dict:
    pca = None
    pca_error = None
    if include_pca:
        try:
            # Ajuste con el lote completo. Se limita únicamente lo que dibuja el navegador.
            sample = batch.rows if len(batch.rows) <= 2000 else batch.rows.sample(2000, random_state=42)
            points, ratio = project(model, batch.rows, sample)
            pca = {
                "points": [{"x": x, "y": y, "cluster": int(cluster)} for x, y, cluster in points.itertuples(index=False, name=None)],
                "variance": float(ratio.sum()),
            }
        except ValueError as exc:
            pca_error = str(exc)
    return {
        "source_count": len(batch.original),
        "operation_count": len(batch.rows),
        "mode": batch.mode,
        "distribution": [
            {"cluster": cluster, "count": count, "share": share}
            for cluster, count, share in batch.summary.itertuples(index=False, name=None)
        ],
        "profiles": [
            {"cluster": int(cluster), "values": row.tolist()}
            for cluster, row in batch.profiles.iterrows()
        ],
        "preview": preview(batch.rows, 50),
        "pca": pca,
        "pca_error": pca_error,
    }
