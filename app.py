"""Portal de segmentación operativa de MineSight."""

import pandas as pd
import streamlit as st

from components import charts, ui
from services.analytics import csv_bytes, project, report, summarize
from services.model import CLUSTERS, FEATURES, load_model
from services.operations import LABEL_COLUMN, available_times, hourly, read_csv, validate

st.set_page_config(page_title="MineSight · Inteligencia operativa", layout="wide")

PAGES = ("Panel ejecutivo", "Análisis CSV", "Predicción manual", "Información del modelo")
FORM_GROUPS = (
    ("Alimentación", FEATURES[:2]),
    ("Dosificación", FEATURES[2:4]),
    ("Pulpa", FEATURES[4:]),
)
CHART_CONFIG = {"displayModeBar": False, "locale": "es"}


@st.cache_resource
def get_model():
    return load_model()


def navigate(page):
    st.session_state["navigation"] = page


def chart(figure, key):
    st.plotly_chart(figure, width="stretch", theme=None, key=key, config=CHART_CONFIG)


def standardized_profiles(model):
    return pd.DataFrame(model.estimator.cluster_centers_, index=CLUSTERS, columns=FEATURES)


def dashboard(model):
    with st.container(key="mine_hero"):
        ui.eyebrow("MineSight / Flotación de hierro")
        st.title("Inteligencia aplicada a operaciones mineras")
        st.write("Analiza condiciones de flotación con machine learning y compara el comportamiento de tu operación con siete grupos históricos.")
        primary, secondary = st.columns(2)
        primary.button("Analizar operaciones", type="primary", width="stretch", on_click=navigate, args=(PAGES[1],))
        secondary.button("Explorar el modelo", width="stretch", on_click=navigate, args=(PAGES[3],))

    counts = model.training_counts()
    batch = st.session_state.get("batch")
    session_count = len(batch["rows"]) if batch is not None else 0
    ui.kpis([
        ("Registros originales", 737453, "stack", "Mediciones del conjunto original antes de agregar por hora.", 1),
        ("Horas de entrenamiento", counts.sum(), "clock", "Promedios horarios asignados durante el entrenamiento.", 1),
        ("Clusters identificados", len(counts), "nodes", "Grupos representados en el modelo entrenado.", 1),
        ("Operaciones en sesión", session_count, "pulse", "Operaciones segmentadas en el último lote de esta sesión.", 1 if session_count else 0),
    ])

    distribution, profiles = st.columns(2, gap="medium")
    with distribution, st.container(key="history_panel"):
        ui.section("Distribución histórica", "Operaciones por cluster en el conjunto de entrenamiento.")
        summary = pd.DataFrame({
            "Cluster": counts.index, "Operaciones": counts.values,
            "Participación (%)": 100 * counts.values / counts.sum(),
        })
        chart(charts.distribution(summary), "historical-distribution")

    with profiles, st.container(key="center_panel"):
        ui.section("Huella de los clusters", "Centroides estandarizados. 0 = media histórica, 1σ = una desviación estándar.")
        selected = st.multiselect(
            "Clusters para comparar", CLUSTERS, default=[0, 1, 2], format_func=lambda group: f"Cluster {group}",
            key="dashboard_clusters",
        )
        if selected:
            chart(charts.radar(standardized_profiles(model).loc[selected]), "historical-radar")
        else:
            st.info("Selecciona al menos un cluster para ver su perfil.")

    with st.container(key="comparison_panel"):
        ui.section("Centroides históricos", "Compara cada variable en la escala original del entrenamiento.")
        feature = st.selectbox("Variable para comparar", FEATURES, key="overview_feature")
        chart(charts.comparison(feature, model.profiles()), "historical-comparison")
    ui.section("Cómo se segmenta una operación")
    ui.pipeline()


def upload_settings():
    with st.container(key="upload_panel"):
        ui.eyebrow("Datos de entrada")
        ui.section("Importar mediciones", "Carga un CSV UTF-8 con las siete variables operativas. Límite de 160 MB.")
        uploaded = st.file_uploader(
            "Archivo CSV de operaciones", type=["csv"], key="operations_csv",
            help="Añade una columna ISO 8601 si necesitas agrupar mediciones por hora.",
        )
        settings_a, settings_b = st.columns(2)
        separator = settings_a.selectbox("Separador de campos", [",", ";", "\t"], format_func={
            ",": "Coma (,)", ";": "Punto y coma (;)", "\t": "Tabulación",
        }.get)
        decimal = settings_b.selectbox("Separador decimal", [".", ","], format_func={
            ".": "Punto (.)", ",": "Coma (,)",
        }.get)
        with st.expander("Ver columnas requeridas"):
            st.code(",".join(FEATURES), language=None)
        if uploaded is None:
            return None
        try:
            with st.spinner("Validando cabecera y variables operativas…"):
                frame = cached_csv(uploaded.getvalue(), separator, decimal)
        except ValueError as exc:
            st.error(str(exc), icon=":material/error:")
            return None
        st.success(f"Archivo validado · {len(frame):,} filas", icon=":material/check_circle:")
        with st.expander("Vista previa de datos", expanded=True):
            st.dataframe(frame.head(8), width="stretch", hide_index=True)
        return frame


@st.cache_data(max_entries=4, scope="session")
def cached_csv(payload, separator, decimal):
    return read_csv(payload, separator, decimal)


def analyze(model):
    ui.eyebrow("Segmentación por lote")
    st.title("Análisis de operaciones")
    st.write("Valida las mediciones, asigna clusters y exporta los resultados del lote.")
    st.info(
        "El modelo se entrenó con promedios horarios. Si tu archivo contiene mediciones individuales, "
        "puedes agruparlas por hora o segmentar las filas en su granularidad de entrada.",
        icon=":material/schedule:",
    )
    frame = upload_settings()
    if frame is not None:
        ui.section("Preparar lote")
        mode = st.radio("Granularidad", ["Una operación por fila", "Promedios por hora"], horizontal=True, key="granularity")
        time_column = None
        if mode == "Promedios por hora":
            candidates = available_times(frame)
            if candidates:
                defaults = [name for name in candidates if name.casefold() in {"date", "fecha", "timestamp", "datetime", "hora"}]
                time_column = st.selectbox(
                    "Columna de fecha y hora", candidates,
                    index=candidates.index(defaults[0]) if defaults else None,
                    placeholder="Selecciona una columna",
                )
                st.caption("Las fechas con desplazamiento horario se convierten a UTC.")
            else:
                st.warning("Incluye una columna temporal para habilitar la agregación horaria.")
        if st.button("Segmentar operaciones", type="primary", disabled=mode == "Promedios por hora" and time_column is None):
            st.session_state.pop("batch", None)
            progress = st.progress(0, text="Preparando operaciones…")
            try:
                rows = hourly(frame, time_column) if time_column else frame.copy()
                if LABEL_COLUMN in rows:
                    raise ValueError("La columna Cluster está reservada para el resultado. Renómbrala en el CSV.")
                progress.progress(50, text="Asignando clusters con el modelo entrenado…")
                rows[LABEL_COLUMN] = model.predict(rows)
                st.session_state["batch"] = {
                    "rows": rows, "source_count": len(frame), "mode": mode.lower(),
                    "filename": st.session_state["operations_csv"].name,
                }
                progress.progress(100, text="Segmentación completada.")
            except ValueError as exc:
                st.error(str(exc), icon=":material/error:")
            finally:
                progress.empty()
    batch = st.session_state.get("batch")
    if batch is not None:
        batch_results(model, batch)


def batch_results(model, batch):
    rows = batch["rows"]
    summary = summarize(rows[LABEL_COLUMN])
    profiles = rows.groupby(LABEL_COLUMN)[list(FEATURES)].mean()
    st.divider()
    ui.section("Último lote procesado", f"{batch['filename']} · {batch['mode']}")
    st.success("El lote está segmentado y disponible para exportar.", icon=":material/check_circle:")
    for col, (label, value) in zip(st.columns(3), [
        ("Registros del CSV", batch["source_count"]),
        ("Operaciones asignadas", len(rows)),
        ("Clusters presentes", len(profiles)),
    ]):
        col.metric(label, value, border=True)

    distribution, profile_tab, projection, table = st.tabs(
        ["Distribución", "Perfiles", "PCA", "Operaciones"], key="batch_tabs", on_change="rerun",
    )
    with distribution:
        chart(charts.distribution(summary), "batch-distribution")
    with profile_tab:
        feature = st.selectbox("Variable para comparar", FEATURES, key="batch_feature")
        chart(charts.comparison(feature, model.profiles(), profiles), "batch-comparison")
        st.caption("Las barras rayadas representan el promedio observado en el lote.")
        st.dataframe(profiles.round(4), width="stretch")
    with projection:
        st.caption("PCA ajustado con las operaciones de este lote después de aplicar el escalador entrenado.")
        if st.checkbox("Calcular proyección PCA", key="calculate_pca"):
            try:
                with st.spinner("Calculando componentes principales…"):
                    points, ratio = project(model, rows, rows)
                chart(charts.scatter(points, ratio), "batch-pca")
                st.caption(f"Varianza explicada en dos componentes en este lote: {ratio.sum():.2%}.")
            except ValueError as exc:
                st.info(str(exc))
    with table:
        st.caption(f"Vista previa de {min(len(rows), 10_000):,} operaciones. El CSV incluye el lote completo.")
        st.dataframe(rows.head(10_000), width="stretch", hide_index=True)

    ui.section("Exportar resultados")
    for col, (label, data, filename, mime) in zip(st.columns(3), [
        ("Descargar operaciones", csv_bytes(rows), "minesight_operaciones.csv", "text/csv"),
        ("Descargar resumen", csv_bytes(summary.round(4)), "minesight_resumen.csv", "text/csv"),
        ("Descargar reporte", report(summary, profiles, batch["source_count"], batch["mode"]),
         "minesight_reporte.md", "text/markdown"),
    ]):
        col.download_button(label, data, filename, mime, icon=":material/download:", width="stretch")


def manual(model):
    ui.eyebrow("Segmentación individual")
    st.title("Predicción de cluster")
    st.write("Compara una condición operativa con los grupos históricos de la planta.")
    st.caption("Los campos se precargan con la media de entrenamiento. Para una comparación directa, usa promedios horarios en las unidades originales.")
    means = dict(zip(FEATURES, model.scaler.mean_))
    with st.form("manual_operation"):
        inputs = {}
        for column, (title, variables) in zip(st.columns(3), FORM_GROUPS):
            with column:
                st.markdown(f"**{title}**")
                for feature in variables:
                    inputs[feature] = st.number_input(
                        feature, value=float(means[feature]), format="%.6f",
                        help=f"Media histórica: {means[feature]:.6g}",
                    )
        submitted = st.form_submit_button("Asignar cluster", type="primary", icon=":material/analytics:")

    if submitted:
        st.session_state.pop("manual_result", None)
        try:
            with st.spinner("Estandarizando y asignando cluster…"):
                operation = validate(pd.DataFrame([inputs]))
                cluster = int(model.predict(operation)[0])
                st.session_state["manual_result"] = (cluster, inputs)
        except ValueError as exc:
            st.error(str(exc), icon=":material/error:")
    if "manual_result" not in st.session_state:
        return

    cluster, values = st.session_state["manual_result"]
    profiles = model.profiles()
    centroid = profiles.loc[cluster]
    standardized = standardized_profiles(model)
    offsets = standardized.loc[cluster]
    ui.result_card(cluster, charts.COLOR_MAP[str(cluster)], int(model.training_counts()[cluster]))

    radar, description = st.columns([3, 2], gap="medium")
    with radar:
        ui.section("Operación frente al centroide", "Valores estandarizados en desviaciones respecto de la media histórica (0σ).")
        standardized_input = model.scale(pd.DataFrame([values]))[0]
        chart(charts.radar(standardized.loc[[cluster]], operation=standardized_input), "manual-radar")
    with description:
        ui.section(f"Perfil del cluster {cluster}")
        for name in offsets.abs().nlargest(3).index:
            direction = "por encima" if offsets[name] >= 0 else "por debajo"
            st.write(
                f"**{name}** · centroide {centroid[name]:.4g}, "
                f"{abs(offsets[name]):.2f}σ {direction} de la media histórica."
            )
        comparison = pd.DataFrame(
            {"Entrada": values, "Centroide del cluster": centroid, "Media histórica": model.scaler.mean_},
            index=FEATURES,
        )
        st.dataframe(comparison.round(4), width="stretch")
    feature = st.selectbox("Comparar con los siete centroides", FEATURES, key="manual_feature")
    chart(charts.comparison(feature, profiles, value=values[feature]), "manual-comparison")


def model_info():
    ui.eyebrow("Machine learning no supervisado")
    st.title("Método y alcance")
    st.write("MineSight identifica grupos de operaciones similares en flotación de hierro. Proyecto de la UPCH para el Challenge 4 de Clustering y Segmentación.")
    ui.section("Pipeline de segmentación", "Entrenado con Quality Prediction in a Mining Process.")
    ui.pipeline()

    ui.section("Evaluación histórica")
    for col, (label, value, help_text) in zip(st.columns(4), [
        ("Silhouette", "0.2262", "Mide la cohesión y separación de los clusters. Valores mayores indican mejor separación."),
        ("Davies–Bouldin", "1.3357", "Resume el solapamiento y la dispersión de los grupos. Menor es mejor."),
        ("Calinski–Harabasz", "917.3293", "Compara dispersión entre clusters con dispersión interna. Mayor es mejor."),
        ("Varianza PCA (2 CP)", "58.89 %", "Varianza acumulada de los dos componentes del PCA histórico."),
    ]):
        col.metric(label, value, help=help_text, border=True)

    left, right = st.columns(2, gap="medium")
    with left, st.container(key="eval_panel"):
        ui.section("Comparación de algoritmos", "Resultado relativo reportado por el notebook.")
        st.dataframe(pd.DataFrame({
            "Métrica": ["Silhouette", "Davies–Bouldin", "Calinski–Harabasz"],
            "Mejor resultado": ["K-Means", "K-Means", "K-Means"],
            "Criterio": ["Mayor", "Menor", "Mayor"],
        }), hide_index=True, width="stretch")
        st.caption("El resumen disponible registra la comparación relativa con MiniBatch K-Means.")
    with right, st.container(key="stability_panel"):
        ui.section("Estabilidad ante inicializaciones", "El ARI compara la coincidencia entre agrupamientos. Un valor de 1 indica concordancia perfecta.")
        ui.ari_card()
        st.caption("Promedio reportado por el notebook. La escala representa el índice, sin una serie por ejecución.")

    ui.section("Interpretación minera")
    st.write("Las agrupaciones fueron estables ante cambios de inicialización y mostraron una separación limitada. Los números de cluster identifican grupos de similitud operativa.")
    st.info(
        "Alcance exploratorio. Los grupos requieren interpretación en el contexto de planta y carecen de validación como "
        "diagnóstico de riesgo o fallas, recomendación de dosificación o predicción de calidad.",
        icon=":material/info:",
    )


def main():
    ui.theme()
    with st.sidebar:
        ui.brand()
        st.caption("Inteligencia operativa minera")
        page = st.radio("Navegación", PAGES, key="navigation", label_visibility="collapsed")
        st.divider()
        st.caption("UPCH · Challenge 4")
    if page == PAGES[3]:
        model_info()
        return
    try:
        model = get_model()
    except (OSError, ValueError, RuntimeError, AttributeError, ImportError, TypeError, EOFError):
        st.error("No se pudo cargar el modelo. Comprueba los artefactos originales y las versiones en el README.")
        return
    views = dict(zip(PAGES, (dashboard, analyze, manual)))
    views[page](model)


main()
