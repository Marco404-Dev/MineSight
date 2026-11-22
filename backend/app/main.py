"""Servicio HTTP de MineSight."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .analysis import analyze, preview, serialize_batch
from .schemas import PredictionInput
from services.model import CLUSTERS, FEATURES, Model, load_model
from services.operations import available_times, read_csv

LOGGER = logging.getLogger(__name__)
MAX_UPLOAD = 20 * 1024 * 1024
UPLOAD_PATHS = {"/api/preview-csv", "/api/analyze-csv"}
ORIGINS = [origin.strip() for origin in os.getenv(
    "MINESIGHT_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000",
).split(",") if origin.strip() and origin.strip() != "*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = None
    try:
        app.state.model = load_model()
    except Exception:
        LOGGER.exception("No se pudo iniciar el modelo MineSight")
    yield


app = FastAPI(title="MineSight", version="2.0.0", lifespan=lifespan)


@app.middleware("http")
async def limit_upload(request: Request, call_next):
    path = request.url.path.rstrip("/")
    if request.method == "POST" and (path in UPLOAD_PATHS or path.startswith("/api/export-csv/")):
        length = request.headers.get("content-length", "")
        if not length.isdecimal():
            return JSONResponse({"detail": "La carga necesita un tamaño declarado."}, status_code=411)
        if len(length) > 10 or int(length) > MAX_UPLOAD + 128 * 1024:
            return JSONResponse({"detail": "El archivo supera el límite de 20 MiB."}, status_code=413)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, exc: RequestValidationError):
    fields = ", ".join(dict.fromkeys(str(error["loc"][-1]) for error in exc.errors()))
    return JSONResponse({"detail": f"Revisa los campos de la solicitud: {fields}."}, status_code=422)


@app.exception_handler(ValueError)
async def invalid_data(_request: Request, exc: ValueError):
    return JSONResponse({"detail": str(exc)}, status_code=422)


def model_dependency(request: Request) -> Model:
    model = request.app.state.model
    if model is None:
        raise HTTPException(503, "El modelo no está disponible. Revisa el registro del servidor.")
    return model


ReadyModel = Annotated[Model, Depends(model_dependency)]
Separator = Literal[",", ";", "\t"]
Decimal = Literal[".", ","]


def upload_content(file: UploadFile) -> bytes:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Selecciona un archivo con extensión .csv.")
    payload = file.file.read(MAX_UPLOAD + 1)
    if len(payload) > MAX_UPLOAD:
        raise HTTPException(413, "El archivo supera el límite de 20 MiB.")
    return payload


@app.get("/api/health")
def health(request: Request):
    ready = request.app.state.model is not None
    return JSONResponse({"status": "ok" if ready else "unavailable", "model_ready": ready}, 200 if ready else 503)


@app.get("/api/model-info")
def model_info(model: ReadyModel):
    counts = model.training_counts()
    centers = model.profiles()
    return {
        "algorithm": "K-Means",
        "features": list(FEATURES),
        "input_keys": list(PredictionInput.model_fields),
        "original_records": 737453,
        "training_hours": int(counts.sum()),
        "metrics": {"silhouette": 0.2262, "davies_bouldin": 1.3357, "calinski_harabasz": 917.3293, "ari": 0.9959, "pca_variance": 0.5889},
        "benchmark": {"alternative": "MiniBatch K-Means", "winner": "K-Means", "metrics": ["Silhouette", "Davies–Bouldin", "Calinski–Harabasz"]},
        "means": model.scaler.mean_.tolist(),
        "clusters": [
            {"cluster": cluster, "count": int(counts[cluster]), "share": float(100 * counts[cluster] / counts.sum()),
             "center": centers.loc[cluster].tolist(), "z": model.estimator.cluster_centers_[cluster].tolist()}
            for cluster in CLUSTERS
        ],
    }


@app.post("/api/predict")
def predict(payload: PredictionInput, model: ReadyModel):
    values = list(payload.model_dump().values())
    rows = pd.DataFrame([values], columns=FEATURES)
    cluster = int(model.predict(rows)[0])
    scaled = model.scale(rows)[0]
    centers = model.estimator.cluster_centers_
    distances = np.linalg.norm(centers - scaled, axis=1)
    top = np.argsort(-np.abs(centers[cluster]))[:3]
    return {
        "cluster": cluster,
        "values": values,
        "z": scaled.tolist(),
        "center": model.profiles().loc[cluster].tolist(),
        "center_z": centers[cluster].tolist(),
        "historical_hours": int(model.training_counts()[cluster]),
        "distances": [{"cluster": group, "distance": float(distances[group])} for group in CLUSTERS],
        "descriptors": [
            {"feature": FEATURES[index], "z": float(centers[cluster, index])}
            for index in top
        ],
    }


@app.post("/api/preview-csv")
def preview_csv(
    file: Annotated[UploadFile, File()],
    separator: Annotated[Separator, Form()] = ",",
    decimal: Annotated[Decimal, Form()] = ".",
):
    frame = read_csv(upload_content(file), separator, decimal)
    return {"source_count": len(frame), "temporal_candidates": available_times(frame), "preview": preview(frame, 8)}


@app.post("/api/analyze-csv")
def analyze_csv(
    model: ReadyModel, file: Annotated[UploadFile, File()],
    separator: Annotated[Separator, Form()] = ",",
    decimal: Annotated[Decimal, Form()] = ".",
    time_column: Annotated[str, Form()] = "",
    include_pca: Annotated[bool, Form()] = True,
):
    batch = analyze(model, upload_content(file), separator, decimal, time_column)
    return serialize_batch(model, batch, include_pca)


@app.post("/api/export-csv/{kind}")
def export_csv(
    kind: Literal["operations", "summary", "report"],
    model: ReadyModel, file: Annotated[UploadFile, File()],
    separator: Annotated[Separator, Form()] = ",",
    decimal: Annotated[Decimal, Form()] = ".",
    time_column: Annotated[str, Form()] = "",
):
    batch = analyze(model, upload_content(file), separator, decimal, time_column)
    data, mime, filename = batch.export(kind)
    return Response(data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
