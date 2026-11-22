"""Lectura, validación y agregación de mediciones operativas."""

import csv
import io

import numpy as np
import pandas as pd

from services.model import FEATURES

TIME_COLUMN = "Hora"
COUNT_COLUMN = "Mediciones"
LABEL_COLUMN = "Cluster"


def read_csv(payload: bytes, separator: str, decimal: str) -> pd.DataFrame:
    try:
        stream = io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8-sig", newline="")
        reader = csv.reader(stream, delimiter=separator, strict=True)
        header = next(reader, [])
        columns = [name.strip() for name in header]
        if not columns or any(not name for name in columns):
            raise ValueError("El CSV necesita una cabecera con nombres de columna.")
        if len(set(columns)) != len(columns):
            raise ValueError("La cabecera contiene nombres de columna duplicados.")
        missing = [name for name in FEATURES if name not in columns]
        if missing:
            raise ValueError("Faltan columnas requeridas: " + ", ".join(missing))
        for row in reader:
            if row and len(row) != len(columns):
                raise ValueError(f"La línea {reader.line_num} no tiene {len(columns)} campos.")
        stream.seek(0)
        frame = pd.read_csv(
            stream, sep=separator, header=0, names=columns,
            dtype={name: "string" for name in FEATURES},
        )
    except (UnicodeError, csv.Error, pd.errors.ParserError) as exc:
        raise ValueError("Guarda el CSV en UTF-8 y revisa el separador y las comillas.") from exc
    if frame.empty:
        raise ValueError("El CSV debe contener al menos una fila de datos.")
    return validate(frame, decimal)


def validate(frame: pd.DataFrame, decimal: str = ".") -> pd.DataFrame:
    clean = frame.copy()
    errors = []
    for name in FEATURES:
        raw = clean[name]
        if pd.api.types.is_bool_dtype(raw):
            errors.append(f"{name}: se esperaban números")
            continue
        if decimal == "," and not pd.api.types.is_numeric_dtype(raw):
            raw = raw.astype("string").str.strip()
            wrong_decimal = raw.str.contains(".", regex=False, na=False)
            raw = raw.str.replace(",", ".", regex=False)
        else:
            wrong_decimal = False
        numeric = pd.to_numeric(raw, errors="coerce").astype(float)
        missing = int(raw.isna().sum())
        invalid = int((raw.notna() & (~np.isfinite(numeric) | wrong_decimal)).sum())
        if missing or invalid:
            errors.append(f"{name}: {missing} faltante(s), {invalid} inválido(s)")
        clean[name] = numeric
    if errors:
        raise ValueError("Revisa los valores de entrada. " + " · ".join(errors))
    return clean


def hourly(frame: pd.DataFrame, time_column: str) -> pd.DataFrame:
    # Fechas sin zona conservan su hora de reloj; los desplazamientos se normalizan.
    timestamps = pd.to_datetime(frame[time_column].astype("string"), format="ISO8601", errors="coerce", utc=True)
    if timestamps.isna().any():
        raise ValueError(
            f"Hay {timestamps.isna().sum()} fechas faltantes o inválidas. "
            "Usa ISO 8601, por ejemplo 2017-03-10 01:00:00."
        )
    groups = frame.loc[:, list(FEATURES)].groupby(timestamps.dt.floor("h").rename(TIME_COLUMN))
    result = groups.mean()
    result[COUNT_COLUMN] = groups.size()
    return result.reset_index()


def available_times(frame: pd.DataFrame) -> list[str]:
    return [name for name in frame.columns if name not in FEATURES]
