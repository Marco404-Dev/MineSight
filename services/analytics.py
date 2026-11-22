"""Resumen, proyección y exportación de resultados observados."""

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from services.model import CLUSTERS, FEATURES, Model
from services.operations import LABEL_COLUMN


def summarize(assignments: pd.Series) -> pd.DataFrame:
    counts = assignments.value_counts().reindex(CLUSTERS, fill_value=0)
    return pd.DataFrame({
        "Cluster": list(CLUSTERS),
        "Operaciones": counts.to_numpy(),
        "Participación (%)": (100 * counts / len(assignments)).to_numpy(),
    })


def project(model: Model, reference: pd.DataFrame, operations: pd.DataFrame):
    scaled_reference = model.scale(reference)
    distinct = np.unique(scaled_reference, axis=0)
    if len(distinct) < 3:
        raise ValueError("El PCA necesita al menos tres operaciones de referencia distintas.")
    pca = PCA(n_components=2, svd_solver="full").fit(scaled_reference)
    if pca.explained_variance_ratio_[1] < 1e-12:
        raise ValueError("La referencia no tiene variación suficiente en dos componentes.")
    coordinates = pca.transform(model.scale(operations))
    plot_data = pd.DataFrame(coordinates, columns=["CP1", "CP2"])
    plot_data["Cluster"] = operations[LABEL_COLUMN].astype(str).to_numpy()
    return plot_data, pca.explained_variance_ratio_


def csv_bytes(frame: pd.DataFrame, index: bool = False) -> bytes:
    # Protege texto operativo que una hoja de cálculo podría tratar como fórmula.
    safe = frame.copy()
    for name in safe.select_dtypes(include=["object", "string"]).columns:
        safe[name] = safe[name].map(protect_cell)
    safe.columns = [protect_cell(name) for name in safe.columns]
    return safe.to_csv(index=index).encode("utf-8-sig")


def protect_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def report(summary: pd.DataFrame, profiles: pd.DataFrame, source_rows: int, granularity: str) -> str:
    lines = [
        "# MineSight | Reporte de segmentación operativa",
        "",
        f"Se procesaron {source_rows:,} registros de entrada como {granularity}.",
        f"El modelo asignó {summary['Operaciones'].sum():,} operaciones.",
        "",
        "## Distribución observada",
        "",
    ]
    for cluster, count, share in summary.itertuples(index=False, name=None):
        lines.append(f"- Cluster {cluster}: {count:,} operaciones ({share:.1f} %).")
    lines += ["", "## Perfil observado de los clusters presentes", ""]
    for cluster, values in profiles.iterrows():
        details = ", ".join(f"{feature} = {values[feature]:.4g}" for feature in FEATURES)
        lines.append(f"- Cluster {cluster}: {details}.")
    lines += [
        "",
        "## Método y alcance",
        "",
        "Asignación al centro más cercano por K-Means, después de aplicar el StandardScaler "
        "entrenado. Los perfiles son promedios de las operaciones de este lote.",
        "",
        "La separación histórica entre grupos es limitada (Silhouette = 0.2262). "
        "Los grupos describen similitud operativa y requieren interpretación de un especialista. "
        "No constituyen diagnósticos de riesgo o fallas, instrucciones de dosificación "
        "ni predicciones de calidad del mineral.",
    ]
    return "\n".join(lines) + "\n"
