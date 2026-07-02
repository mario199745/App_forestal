"""Aplicación Streamlit para la evaluación forestal de tara."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Permite ejecutar tanto con ``streamlit run`` como con ``AppTest``.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from database import DB_PATH, query, table


st.set_page_config(
    page_title="Evaluación forestal | SERFOR",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = ["#176B55", "#D89B32", "#8E5A3C", "#4C8FA3", "#843E52", "#7B8E57"]

st.markdown(
    """
    <style>
      :root { --forest:#176B55; --sand:#F3EFE6; --ink:#17352D; }
      .stApp { background: linear-gradient(180deg,#F8FAF7 0,#FFFFFF 22rem); }
      [data-testid="stSidebar"] { background:#123E34; }
      [data-testid="stSidebar"] * { color:#F7F2E8; }
      [data-testid="stMetric"] {
        background:white; border:1px solid #DDE7E1; border-radius:14px;
        padding:1rem 1.1rem; box-shadow:0 4px 18px rgba(23,53,45,.06);
      }
      .hero { padding:1.5rem 1.7rem; border-radius:20px; color:white;
        background:linear-gradient(120deg,#123E34,#24765F); margin-bottom:1.2rem; }
      .hero h1 { margin:0; font-size:2rem; }
      .hero p { margin:.45rem 0 0; color:#E4F0EA; }
      .eyebrow { color:#DDB46A; font-size:.78rem; letter-spacing:.12em;
        text-transform:uppercase; font-weight:700; }
      .note { border-left:4px solid #D89B32; background:#FFF9ED;
        padding:.75rem 1rem; border-radius:0 10px 10px 0; }
      div[data-testid="stPlotlyChart"] { background:white; border-radius:14px; }
      #MainMenu, footer { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not DB_PATH.exists():
    st.error(
        "No se encontró `App_forestal/data/forestal.db`. "
        "Incluya este archivo en el repositorio desplegado."
    )
    st.stop()


@st.cache_data(show_spinner=False)
def filter_catalog() -> pd.DataFrame:
    return query(
        """
        SELECT region, manejo, clase, morfotipo FROM fact_arbol
        UNION SELECT region, manejo, clase, morfotipo FROM fact_morfologia
        UNION SELECT region, manejo, clase, morfotipo FROM fact_tanino_repeticion
        """
    )


def options(frame: pd.DataFrame, column: str) -> list[str]:
    return sorted(frame[column].dropna().astype(str).unique().tolist())


def apply_filters(frame: pd.DataFrame, selected: dict[str, list[str]]) -> pd.DataFrame:
    result = frame.copy()
    for column, values in selected.items():
        if values and column in result:
            result = result[result[column].isin(values)]
    return result


def download_button(frame: pd.DataFrame, filename: str) -> None:
    st.download_button(
        "Descargar datos filtrados",
        data=frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        width="stretch",
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><div class="eyebrow">SERFOR · Evaluación forestal</div>'
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def empty_state() -> None:
    st.warning("No hay observaciones para la combinación de filtros seleccionada.")
    st.stop()


def style_figure(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=55, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", color="#17352D"),
        legend_title_text="",
    )
    fig.update_xaxes(gridcolor="#E8EEE9")
    fig.update_yaxes(gridcolor="#E8EEE9")
    return fig


catalog = filter_catalog()
with st.sidebar:
    st.markdown("## 🌿 Evaluación forestal")
    st.caption("Producción · Morfología · Taninos")
    page = st.radio(
        "Navegación",
        ["Resumen", "Producción", "Morfología", "Taninos", "Comparación", "Metodología"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("#### Filtros globales")
    selected_region = st.multiselect("Región", options(catalog, "region"))
    dependent = catalog[catalog["region"].isin(selected_region)] if selected_region else catalog
    selected_manejo = st.multiselect("Manejo", options(dependent, "manejo"))
    if selected_manejo:
        dependent = dependent[dependent["manejo"].isin(selected_manejo)]
    selected_clase = st.multiselect("Clase", options(dependent, "clase"))
    if selected_clase:
        dependent = dependent[dependent["clase"].isin(selected_clase)]
    selected_morfotipo = st.multiselect("Morfotipo", options(dependent, "morfotipo"))
    st.caption("Los filtros vacíos incluyen todos los valores.")

filters = {
    "region": selected_region,
    "manejo": selected_manejo,
    "clase": selected_clase,
    "morfotipo": selected_morfotipo,
}


def render_summary() -> None:
    hero("Panorama de la evaluación", "Una lectura integrada de árboles, vainas, semillas y taninos.")
    prod = apply_filters(table("fact_arbol"), filters)
    morph = apply_filters(table("fact_morfologia"), filters)
    tannin = apply_filters(table("fact_tanino_repeticion"), filters)
    if prod.empty and morph.empty and tannin.empty:
        empty_state()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Árboles evaluados", f"{len(prod):,}")
    c2.metric("Mediciones morfológicas", f"{len(morph):,}")
    c3.metric("Ensayos de taninos", f"{len(tannin):,}")
    all_regions = pd.concat([prod.get("region"), morph.get("region"), tannin.get("region")]).dropna()
    c4.metric("Regiones representadas", all_regions.nunique())

    left, right = st.columns([1.25, 1])
    with left:
        counts = pd.concat(
            [
                prod.groupby("region").size().rename("Producción"),
                morph.groupby("region").size().rename("Morfología"),
                tannin.groupby("region").size().rename("Taninos"),
            ], axis=1,
        ).fillna(0).reset_index().melt("region", var_name="Dominio", value_name="Observaciones")
        fig = px.bar(counts, x="region", y="Observaciones", color="Dominio", barmode="group",
                     color_discrete_sequence=COLORS, title="Cobertura de observaciones por región")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        coverage = apply_filters(table("vw_cobertura_dominios"), {k: v for k, v in filters.items() if k != "morfotipo"})
        labels = ["Producción", "Morfología", "Taninos"]
        values = [coverage["tiene_produccion"].sum(), coverage["tiene_morfologia"].sum(), coverage["tiene_taninos"].sum()]
        fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=COLORS[:3], text=values, textposition="auto"))
        fig.update_layout(title="Grupos región–manejo–clase con datos")
        st.plotly_chart(style_figure(fig), width="stretch")
    st.markdown('<div class="note">Las cifras corresponden a unidades de observación distintas. No deben sumarse como si fueran individuos equivalentes.</div>', unsafe_allow_html=True)


PROD_METRICS = {
    "alt_total": ("Altura total", "m"), "dap_ms": ("DAP multisección", "cm"),
    "biomasa_alom": ("Biomasa alométrica", "kg"), "peso_cosfin": ("Peso final de cosecha", "kg"),
    "vol_copa": ("Volumen de copa", "m³"), "cober_copa": ("Cobertura de copa", "m²"),
}


def render_production() -> None:
    hero("Producción por árbol", "Estructura, biomasa y cosecha de los individuos evaluados.")
    data = apply_filters(table("fact_arbol"), filters)
    if data.empty: empty_state()
    metric = st.selectbox("Variable de análisis", list(PROD_METRICS), format_func=lambda x: f"{PROD_METRICS[x][0]} ({PROD_METRICS[x][1]})")
    valid = pd.to_numeric(data[metric], errors="coerce").dropna()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Observaciones", f"{len(data):,}")
    c2.metric("Con dato", f"{len(valid):,}")
    c3.metric("Promedio", f"{valid.mean():,.2f}" if len(valid) else "—")
    c4.metric("Mediana", f"{valid.median():,.2f}" if len(valid) else "—")
    left, right = st.columns(2)
    with left:
        fig = px.box(data, x="manejo", y=metric, color="clase", points="outliers",
                     color_discrete_sequence=COLORS, title=f"{PROD_METRICS[metric][0]} por manejo y clase")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        fig = px.scatter(data, x="dap_ms", y="biomasa_alom", color="manejo", symbol="clase",
                         hover_data=["region", "morfotipo", "alt_total"], opacity=.7,
                         color_discrete_sequence=COLORS, title="Relación entre DAP y biomasa")
        st.plotly_chart(style_figure(fig), width="stretch")
    visible = list(dict.fromkeys(c for c in ["region","manejo","clase","morfotipo",metric,"edad","alt_total","dap_ms"] if c in data))
    st.dataframe(data[visible], width="stretch", hide_index=True)
    download_button(data, "produccion_filtrada.csv")


MORPH_METRICS = {
    "long_vaina": ("Longitud de vaina", "mm"), "anch_vaina": ("Ancho de vaina", "mm"),
    "peso_vaina": ("Peso de vaina", "g"), "n_semilla": ("Número de semillas", "n"),
    "long_semilla": ("Longitud de semilla", "mm"), "anch_semilla": ("Ancho de semilla", "mm"),
    "peso_semilla": ("Peso de semilla", "g"),
}


def render_morphology() -> None:
    hero("Morfología de vainas y semillas", "Distribuciones biométricas y diferencias entre morfotipos.")
    data = apply_filters(table("fact_morfologia"), filters)
    if data.empty: empty_state()
    metric = st.selectbox("Variable morfológica", list(MORPH_METRICS), format_func=lambda x: f"{MORPH_METRICS[x][0]} ({MORPH_METRICS[x][1]})")
    valid = pd.to_numeric(data[metric], errors="coerce").dropna()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mediciones", f"{len(data):,}")
    c2.metric("Morfotipos", data["morfotipo"].nunique())
    c3.metric("Promedio", f"{valid.mean():,.2f}")
    c4.metric("Desv. estándar", f"{valid.std():,.2f}")
    left, right = st.columns(2)
    with left:
        fig = px.violin(data, x="morfotipo", y=metric, color="manejo", box=True, points=False,
                        color_discrete_sequence=COLORS, title=f"Distribución de {MORPH_METRICS[metric][0].lower()}")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        fig = px.scatter(data, x="long_vaina", y="peso_vaina", color="morfotipo", facet_col="manejo",
                         hover_data=["region","clase","n_semilla"], opacity=.65,
                         color_discrete_sequence=COLORS, title="Longitud y peso de vaina")
        st.plotly_chart(style_figure(fig), width="stretch")
    visible = list(dict.fromkeys(["region","manejo","clase","morfotipo",metric,"n_semilla"]))
    st.dataframe(data[visible].head(1000), width="stretch", hide_index=True)
    download_button(data, "morfologia_filtrada.csv")


def render_tannins() -> None:
    hero("Taninos en vainas", "Resultados consolidados, repeticiones y control de variabilidad.")
    data = apply_filters(table("fact_tanino_repeticion"), filters)
    if data.empty: empty_state()
    values = pd.to_numeric(data["taninos"], errors="coerce").dropna()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ensayos", f"{len(data):,}")
    c2.metric("Muestras", data["codigo_dei"].nunique())
    c3.metric("Taninos promedio", f"{values.mean():,.2f}")
    c4.metric("Rango", f"{values.min():,.1f} – {values.max():,.1f}")
    left, right = st.columns(2)
    with left:
        fig = px.box(data, x="morfotipo", y="taninos", color="manejo", points="all",
                     color_discrete_sequence=COLORS, title="Distribución de taninos")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        sample = data.groupby(["codigo_dei","repetition"], dropna=False)["taninos"].mean().reset_index()
        fig = px.line(sample, x="codigo_dei", y="taninos", color="repetition", markers=True,
                      color_discrete_sequence=COLORS, title="Consistencia entre repeticiones")
        fig.update_xaxes(showticklabels=False, title="Muestras")
        st.plotly_chart(style_figure(fig), width="stretch")
    st.dataframe(data[["codigo_dei","region","manejo","clase","morfotipo","repetition","taninos","humedad","fecha_result","origen"]], width="stretch", hide_index=True)
    download_button(data, "taninos_filtrados.csv")


def render_comparison() -> None:
    hero("Comparación integrada", "Indicadores agregados; sin unir observaciones individuales incompatibles.")
    prod = apply_filters(query("SELECT * FROM vw_resumen_produccion"), filters).rename(columns={"n": "n_produccion"})
    morph = apply_filters(query("SELECT * FROM vw_resumen_morfologia"), filters).rename(columns={"n": "n_morfologia"})
    tannin = apply_filters(query("SELECT * FROM vw_resumen_taninos"), filters).rename(columns={"n": "n_taninos"})
    keys = ["region","manejo","clase","morfotipo"]
    merged = prod.merge(morph, on=keys, how="outer", suffixes=("_prod","_morph")).merge(tannin, on=keys, how="outer")
    if merged.empty: empty_state()
    x_options = {"biomasa_media":"Biomasa media", "cosecha_media":"Cosecha media", "peso_vaina_medio":"Peso medio de vaina", "longitud_vaina_media":"Longitud media de vaina"}
    x_var = st.selectbox("Indicador del eje X", list(x_options), format_func=x_options.get)
    fig = px.scatter(merged, x=x_var, y="taninos_media",
                     color="manejo", symbol="clase", hover_data=keys,
                     color_discrete_sequence=COLORS, title=f"{x_options[x_var]} y taninos promedio")
    st.plotly_chart(style_figure(fig, 500), width="stretch")
    st.caption("Cada punto representa un agregado de región, manejo, clase y morfotipo; el gráfico no implica causalidad.")
    st.dataframe(merged, width="stretch", hide_index=True)
    download_button(merged, "comparacion_integrada.csv")


def render_methodology() -> None:
    hero("Datos y metodología", "Alcance, trazabilidad y criterios de interpretación.")
    st.markdown("""
    ### Fuentes incluidas

    - Producción por árbol: estructura, copa, biomasa y cosecha.
    - Morfología: dimensiones y peso de vainas y semillas.
    - Taninos: resultados por repetición y reporte consolidado.

    ### Criterios de integración

    Las etiquetas de región, manejo, clase y morfotipo se normalizan para los filtros,
    pero sus valores originales permanecen en la base. Los dominios solo se comparan
    después de agregarlos al mismo nivel; no se unen mediciones individuales.

    ### Calidad y lectura

    El número de observaciones puede variar entre indicadores debido a valores ausentes.
    Los duplicados de origen se conservan y se marcan. Las visualizaciones describen la
    muestra evaluada y no constituyen por sí solas una inferencia causal o poblacional.
    """)
    coverage = table("vw_cobertura_dominios")
    st.dataframe(coverage, width="stretch", hide_index=True)
    download_button(coverage, "cobertura_dominios.csv")


renderers = {
    "Resumen": render_summary, "Producción": render_production,
    "Morfología": render_morphology, "Taninos": render_tannins,
    "Comparación": render_comparison, "Metodología": render_methodology,
}
renderers[page]()

