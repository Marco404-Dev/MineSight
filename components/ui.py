"""Componentes visuales compartidos del portal MineSight."""

from base64 import b64encode
from html import escape
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parents[1] / "assets"
ICONS = {
    "brand": '<path d="m2 19 7-12 4 6 3-9 6 15ZM9 19l4-6 5 6"/>',
    "stack": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "nodes": '<path d="m5 7 7 5 7-5m-7 5v7"/><circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="12" cy="20" r="2"/>',
    "pulse": '<path d="M2 12h5l3-7 4 14 3-7h5"/>',
    "upload": '<path d="M12 16V4m-4 4 4-4 4 4M4 16v4h16v-4"/>',
    "scale": '<path d="M4 5h16M4 12h16M4 19h16"/><circle cx="8" cy="5" r="2" fill="#111C2B"/><circle cx="15" cy="12" r="2" fill="#111C2B"/><circle cx="9" cy="19" r="2" fill="#111C2B"/>',
}


def icon(name):
    return f'<i class="ms-icon ms-icon-{name}" aria-hidden="true"></i>'


def svg_data(svg):
    return "data:image/svg+xml;base64," + b64encode(svg.encode("utf-8")).decode("ascii")


def theme():
    artwork = svg_data((ASSETS / "flotacion.svg").read_text(encoding="utf-8"))
    css = (ASSETS / "theme.css").read_text(encoding="utf-8")
    icon_rules = []
    for name, path in ICONS.items():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" '
            'stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round">' + path + '</svg>'
        )
        icon_rules.append(f'.ms-icon-{name}{{--glyph:url("{svg_data(svg)}")}}')
    rules = "\n".join(icon_rules)
    st.markdown(
        f'<style>{css}\n.st-key-mine_hero{{--plant:url("{artwork}")}}\n{rules}</style>',
        unsafe_allow_html=True,
    )


def brand():
    st.html(f'<div class="ms-brand"><span>{icon("brand")}</span><strong>MineSight</strong></div>')


def eyebrow(label):
    st.html(f'<div class="ms-eyebrow">{escape(label)}</div>')


def section(title, detail=None):
    st.subheader(title)
    if detail:
        st.caption(detail)


def kpis(items):
    cards = []
    for label, value, glyph, hint, fraction in items:
        number = int(value)
        display = f"{number:,}".replace(",", " ")
        cards.append(
            f'<article class="ms-kpi" style="--target:{number};--fraction:{fraction:.2%}">'
            f'<span class="ms-glyph">{icon(glyph)}</span>'
            f'<span class="ms-tooltip" tabindex="0" aria-label="{escape(hint, quote=True)}">?'
            f'<span role="tooltip">{escape(hint)}</span></span>'
            f'<div class="ms-kpi-value"><span class="ms-count" aria-hidden="true">{display}</span>'
            f'<span class="ms-sr">{display}</span></div>'
            f'<span class="ms-kpi-label">{escape(label)}</span><i aria-hidden="true"></i></article>'
        )
    st.html('<div class="ms-kpis">' + ''.join(cards) + '</div>')


def pipeline():
    stages = (
        ("upload", "Datos operativos", "Siete variables de alimentación, dosificación y pulpa. El entrenamiento utilizó promedios por hora."),
        ("scale", "Estandarización", "StandardScaler resta la media histórica y divide por la desviación estándar de cada variable."),
        ("nodes", "Asignación K-Means", "La operación se asigna al centroide más cercano por distancia euclidiana en el espacio estandarizado."),
    )
    st.html('<ol class="ms-pipeline">' + ''.join(
        f'<li><span class="ms-glyph">{icon(glyph)}</span><h3>{title}</h3><p>{detail}</p></li>'
        for glyph, title, detail in stages
    ) + '</ol>')


def result_card(cluster, color, hours):
    st.html(
        f'<div class="ms-result" style="--cluster:{color}"><span class="ms-glyph">{icon("nodes")}</span>'
        f'<div><div class="ms-eyebrow">Cluster asignado</div><strong>Cluster {cluster}</strong></div>'
        f'<span class="ms-count-label">{hours:,} horas históricas en el grupo</span></div>'
    )


def ari_card():
    st.html(
        '<div class="ms-ari"><div><span>ARI medio</span><strong>0.9959</strong></div>'
        '<div class="ms-ari-track" role="img" aria-label="ARI medio 0.9959 en escala de −1 a 1">'
        '<i></i><b></b></div><div class="ms-ari-scale"><span>−1</span><span>0</span><span>1</span></div></div>'
    )
