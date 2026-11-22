# MineSight 2.0

MineSight analiza la similitud entre condiciones operativas de flotación de hierro. La interfaz usa Next.js y FastAPI ejecuta el escalador y el K-Means originales.

## Ejecutar en Windows

Requiere Python 3.12 y Node.js 22 o posterior. Abre dos terminales en la raíz del repositorio.

**Terminal 1 · FastAPI**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Terminal 2 · Next.js**

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Abre [MineSight](http://localhost:3000). La [documentación interactiva de la API](http://127.0.0.1:8000/docs) muestra los endpoints y permite probarlos.

## Ejecutar en Linux

**Terminal 1**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload
```

**Terminal 2**

```bash
cd frontend
npm ci
npm run dev
```

## Configuración y solución de errores

- El frontend consulta `http://127.0.0.1:8000` por defecto. Configura `NEXT_PUBLIC_API_URL` en `frontend/.env.local` si cambias la dirección de la API. Después de editarla, reinicia el servidor de desarrollo o recompila la aplicación.
- Configura `MINESIGHT_CORS_ORIGINS` en el entorno del proceso de FastAPI para admitir orígenes adicionales separados por comas. El valor predeterminado admite solo `http://localhost:3000` y `http://127.0.0.1:3000`. Si Next.js cambia de puerto, incluye ese nuevo origen y reinicia FastAPI.
- Si PowerShell bloquea `npm.ps1`, usa `npm.cmd`. Si `py -3.12 --version` da error, instala Python 3.12 y vuelve a abrir la terminal antes de crear `.venv`.
- `npm run dev` inicia el entorno de desarrollo. Para levantar la compilación de producción ejecuta `npm run build` y luego `npm run start` dentro de `frontend/`. En PowerShell utiliza `npm.cmd`.
- Si la interfaz no conecta con FastAPI, abre [el endpoint de salud](http://127.0.0.1:8000/api/health) para confirmar el puerto y el estado del modelo.

## Arquitectura

| Ruta | Responsabilidad |
| --- | --- |
| `frontend/src/app/` | Panel ejecutivo, análisis CSV, predicción manual e información del modelo con App Router |
| `frontend/src/components/` | Componentes de interfaz, gráficos Recharts, Motion e iconos Lucide |
| `backend/app/` | API FastAPI, validación Pydantic, segmentación CSV y exportaciones |
| `services/` | Inferencia, preprocesamiento y análisis compartidos con Streamlit |
| `models/` | Artefactos originales locales. Se comprueban por SHA-256 antes de deserializar |
| `backend/tests/` y `tests/` | Pruebas de la API y de la versión Streamlit |

### Flujo de datos

1. El navegador envía las variables o el CSV a FastAPI.
2. La API valida los campos y aplica, si se solicita, agregación por hora.
3. El StandardScaler original transforma las variables en el orden de entrenamiento. K-Means asigna el centroide más cercano.
4. La API devuelve distribuciones, centroides y perfiles. Para una operación también devuelve las distancias a los siete centroides. Son distancias en el espacio estandarizado, no probabilidades.

| Método | Endpoint | Función |
| --- | --- | --- |
| GET | `/api/health` | Estado de API y del modelo |
| GET | `/api/model-info` | Características, métricas, medias, centroides y distribución histórica |
| POST | `/api/predict` | Segmentación individual mediante JSON |
| POST | `/api/preview-csv` | Validación y vista previa mediante multipart |
| POST | `/api/analyze-csv` | Segmentación por lote, distribución, perfiles y PCA opcional |
| POST | `/api/export-csv/{kind}` | Exporta `operations`, `summary` o `report` |

El CSV admite UTF-8, un máximo de 20 MiB y las siete cabeceras exactas que aparecen en la interfaz. La vista previa muestra hasta ocho filas de entrada y cincuenta filas segmentadas. La descarga contiene todas las operaciones. Las exportaciones reutilizan el archivo y los parámetros seleccionados, y vuelven a ejecutar el pipeline sin guardar lotes en el servidor. El PCA se ajusta con el lote completo y se muestran hasta 2 000 puntos. Si el lote tiene variación insuficiente, la interfaz explica el motivo. La barra de progreso mide la transferencia del archivo. El cálculo en FastAPI se muestra como un estado de espera.

## Pruebas

Desde la raíz, en Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
npm.cmd --prefix frontend run build
```

En Linux:

```bash
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m unittest discover -s backend/tests -v
npm --prefix frontend run build
```

La prueba de paridad compara FastAPI con el pipeline de Streamlit usando las medias y los centroides del modelo. Para la verificación manual también se utilizó una muestra de promedios horarios del conjunto público *Quality Prediction in a Mining Process*, obtenida de [la versión derivada documentada](https://github.com/baiheng2012/mine-ai-platform/blob/main/data/README.md). El conjunto completo queda fuera del repositorio.

## Alcance

Los clusters representan similitud operativa con el historial. Las métricas del notebook se muestran con sus valores documentados. La comparación con MiniBatch K-Means es relativa y la estabilidad se representa con el ARI medio. MineSight carece de validación como diagnóstico de fallas, evaluación de riesgo, recomendación de dosificación o estimación de calidad.

## Streamlit

La versión anterior sigue disponible en `app.py`. Instala las dependencias de `requirements.txt` de la raíz y ejecuta `python -m streamlit run app.py` con ese entorno. La ilustración de flotación es un SVG original reutilizado en ambas interfaces.
