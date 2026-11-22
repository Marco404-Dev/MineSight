"""Gráficos interactivos y paleta compartida de clusters."""

import math

import plotly.express as px
import plotly.graph_objects as go

from services.model import CLUSTERS, FEATURES

COLORS = ("#F5A45D", "#38BDF8", "#ADA4FF", "#F4CE69", "#F293BA", "#67D8A1", "#D6A7ED")
COLOR_MAP = dict(zip(map(str, CLUSTERS), COLORS))
AXES = ("Fe · alim.", "Sílice · alim.", "Almidón", "Amina", "Caudal pulpa", "pH pulpa", "Densidad")


def styled(figure, height):
    return figure.update_layout(
        template="plotly_dark", height=height, autosize=True,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#D8E5F4", family="system-ui, sans-serif", size=12),
        margin=dict(l=12, r=12, t=20, b=14),
        hoverlabel=dict(bgcolor="#1A2F46", bordercolor="#3D5974", font_color="#F8FAFC"),
        legend=dict(orientation="h", y=-0.23, yanchor="top"),
    ).update_xaxes(gridcolor="#26384C", zerolinecolor="#26384C").update_yaxes(
        gridcolor="#26384C", zerolinecolor="#26384C",
    )


def distribution(summary):
    data = summary.assign(Grupo=summary["Cluster"].astype(str))
    figure = px.bar(
        data, x="Grupo", y="Operaciones", color="Grupo", color_discrete_map=COLOR_MAP,
        category_orders={"Grupo": list(COLOR_MAP)}, text="Operaciones",
        custom_data=["Participación (%)"], labels={"Grupo": "Cluster"},
    )
    figure.update_traces(
        textposition="outside", cliponaxis=False,
        hovertemplate="Cluster %{x}<br>%{y:,} operaciones<br>%{customdata[0]:.1f} % del total<extra></extra>",
    )
    return styled(figure.update_layout(
        showlegend=False, bargap=.38, barcornerradius=5,
        yaxis=dict(range=[0, max(summary["Operaciones"].max() * 1.2, 1)]),
    ), 310)


def comparison(feature, reference, observed=None, value=None):
    groups = reference.index.astype(str)
    figure = go.Figure(go.Bar(
        x=groups, y=reference[feature], name="Centroide histórico",
        marker_color=[COLOR_MAP[group] for group in groups],
        hovertemplate="Cluster %{x}<br>%{y:.4g}<extra>Centroide histórico</extra>",
    ))
    if observed is not None:
        groups = observed.index.astype(str)
        figure.add_bar(
            x=groups, y=observed[feature], name="Promedio del lote",
            marker=dict(
                color=[COLOR_MAP[group] for group in groups],
                pattern=dict(shape="/", solidity=.25, fgcolor="#080D16"),
            ),
            hovertemplate="Cluster %{x}<br>%{y:.4g}<extra>Promedio del lote</extra>",
        )
    if value is not None:
        figure.add_hline(y=value, line_dash="dash", line_color="#F8FAFC", annotation_text="Valor ingresado")
    return styled(figure.update_layout(
        barmode="group", barcornerradius=4, showlegend=observed is not None,
        yaxis_title=feature, xaxis_title="Cluster",
        xaxis=dict(type="category", categoryorder="array", categoryarray=list(COLOR_MAP)),
    ), 330)


def radar(standardized, operation=None):
    """Usa radio desplazado para mostrar z negativos sin reflejar los puntos."""
    vectors = [standardized.loc[group].tolist() for group in standardized.index]
    if operation is not None:
        vectors.append(operation.tolist())
    minimum = min(vector_value for vector in vectors for vector_value in vector)
    maximum = max(vector_value for vector in vectors for vector_value in vector)
    lower = min(math.floor(minimum), -1)
    upper = max(math.ceil(maximum), 1)
    ticks = sorted({lower, 0, upper, (lower + upper) / 2})
    figure = go.Figure()
    for group, vector in zip(standardized.index, vectors):
        add_radar_trace(figure, vector, lower, f"Cluster {group}", COLOR_MAP[str(group)])
    if operation is not None:
        add_radar_trace(figure, vectors[-1], lower, "Operación ingresada", "#F8FAFC", dash="dot")
    return styled(figure.update_layout(
        margin=dict(l=45, r=45, t=32, b=32),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, upper - lower], tickvals=[tick - lower for tick in ticks],
                            ticktext=[f"{tick:g}σ" for tick in ticks], gridcolor="#36506A", angle=90),
            angularaxis=dict(gridcolor="#36506A", linecolor="#36506A", tickfont=dict(size=10)),
        ),
        legend=dict(y=-.12),
    ), 365)


def add_radar_trace(figure, vector, lower, name, color, dash="solid"):
    figure.add_trace(go.Scatterpolar(
        theta=[*AXES, AXES[0]], r=[value - lower for value in [*vector, vector[0]]],
        customdata=[[feature, value] for feature, value in zip((*FEATURES, FEATURES[0]), [*vector, vector[0]])],
        mode="lines+markers", name=name, line=dict(color=color, width=2, dash=dash),
        marker=dict(size=5),
        hovertemplate="%{customdata[0]}<br>z = %{customdata[1]:+.2f} σ<extra>%{fullData.name}</extra>",
    ))


def scatter(points, ratio):
    figure = px.scatter(
        points, x="CP1", y="CP2", color="Cluster", color_discrete_map=COLOR_MAP,
        category_orders={"Cluster": list(COLOR_MAP)},
        labels={"CP1": f"CP1 ({ratio[0]:.1%})", "CP2": f"CP2 ({ratio[1]:.1%})"},
        render_mode="webgl",
    )
    return styled(figure.update_traces(marker=dict(size=7, opacity=.72)), 430)
